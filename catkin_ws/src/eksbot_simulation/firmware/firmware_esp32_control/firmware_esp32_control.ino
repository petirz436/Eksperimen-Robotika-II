/*
 * ESP32 Control System Firmware for AutoStack Eksbot2
 * ====================================================
 * Disesuaikan dengan konfigurasi pin dan Wi-Fi dari folder program_dimas.
 * Mendukung komunikasi nirkabel (Wireless Wi-Fi UDP) antar ESP & fallback kabel Serial2,
 * serta dilengkapi HTTP Web Server Port 80 untuk OTA Firmware Update Nirkabel.
 *
 * Fitur:
 * 1. Nirkabel (Wi-Fi Station UDP Port 8888):
 *    - Konek ke SoftAP ESP32-CAM "dimas_asoy_geboy" (password "12345678") dengan Static IP 192.168.4.10.
 *    - Auto-reconnect di loop() jika ESP32-CAM telat menyala (tanpa membuat AP kembar).
 *    - Menerima kontrol JSON {"lin", "ang", "grip", "lift", "cam"} langsung dari Laptop / ESP32-CAM.
 * 2. Web Server & OTA Update (Port 80):
 *    - Halaman OTA Update di http://192.168.4.10/update untuk flash biner firmware (.bin).
 *    - Mendukung navigasi pemilihan target flash (ESP32-Control 192.168.4.10 vs ESP32-CAM 192.168.4.1).
 * 3. Kabel Serial UART2 ke Arduino Nano (GPIO22 TX2 -> D0, GPIO23 RX2 <- D1):
 *    - Mengirim perintah aktuator ("ACT:cam,lift,grip\n") ke Arduino Nano.
 *    - Tetap mendukung fallback perintah Serial ("CMD:lin,ang,grip,lift,cam\n").
 * 4. Mengendalikan Motor DC Kiri & Kanan (Differential Drive PWM L298N/BTS7960) sesuai pin program_dimas:
 *    - ENA: 4, IN1: 16, IN2: 17, ENB: 21, IN3: 19, IN4: 18
 * 5. Failsafe: motor berhenti otomatis bila tidak ada perintah valid selama 500 ms.
 * 6. Telemetri Baterai: membaca ADC GPIO34 dan mengirim status langsung ke Laptop, ESP32-CAM (192.168.4.1) & broadcast.
 */

#include <WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>
#include "esp_http_server.h"
#include <Update.h>

// PIN CONFIGURATION MOTOR DRIVER (L298N / BTS7960) - Sesuai program_dimas
#define ENA_PIN 4   // PWM Speed Left
#define IN1_PIN 16  // Direction 1 Left
#define IN2_PIN 17  // Direction 2 Left

#define ENB_PIN 21  // PWM Speed Right
#define IN3_PIN 19  // Direction 1 Right
#define IN4_PIN 18  // Direction 2 Right

// PIN HARDWARE SERIAL UART2 KE ARDUINO NANO (AKTUATOR SUB-CONTROLLER)
#define RX2_PIN 23  // RX2 ESP32 <- TX Nano (D1)
#define TX2_PIN 22  // TX2 ESP32 -> RX Nano (D0)

// PIN SENSOR BATERAI (ADC Input-Only GPIO34)
#define PIN_BATTERY_ADC 34
#define BATT_DIVIDER_RATIO 4.0f // Rasio pembagi tegangan (misal 30k:10k) untuk LiPo 3S (11.1V - 12.6V)

// KONFIGURASI WI-FI & UDP
const char* STA_SSID = "dimas-cam";      // Konek ke SoftAP ESP32-CAM (192.168.4.10)
const char* STA_PASS = "12345678";
const char* AP_SSID  = "dimas-control";  // SoftAP mandiri Control (192.168.5.1) untuk OTA/akses darurat
const char* AP_PASS  = "12345678";
const int UDP_PORT   = 8888;

// Kinematika Differential Drive - Sesuai program_dimas
const float WHEEL_BASE = 0.26; // 26 cm
const float MAX_SPEED  = 0.50; // 0.5 m/s
const unsigned long FAILSAFE_MS = 500;

WiFiUDP udp;
httpd_handle_t control_httpd = NULL;


unsigned long lastCmdMs = 0;
bool motorsStopped = true;
char lineBuf[64];
uint8_t lineLen = 0;
unsigned long lastIPPrintTime = 0;
float currentLinear = 0.0f;
float currentAngular = 0.0f;
int currentGrip = 0;
int currentLift = 0;
int currentCam = 90; // Default posisi tengah kamera (0 - 180 derajat)
float batteryVoltage = 12.0f;

// ------------------------------------------------------------
// OTA Web Update Handler untuk ESP32 Control (Port 80)
// ------------------------------------------------------------
static const char OTA_CONTROL_HTML[] =
  "<!DOCTYPE html><html lang='id'><head><meta charset='utf-8'>"
  "<meta name='viewport' content='width=device-width,initial-scale=1'>"
  "<title>ESP32-Control OTA Firmware Update</title>"
  "<style>"
  "body{font-family:system-ui,-apple-system,sans-serif;background:#0c0d10;color:#ededf0;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;padding:16px;box-sizing:border-box}"
  ".card{background:#18191e;border:1px solid #282a32;border-radius:14px;padding:24px;width:min(420px,100%);text-align:center;box-shadow:0 8px 32px rgba(0,0,0,0.6)}"
  ".badge{display:inline-block;padding:4px 10px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:0.5px;background:#10b98122;color:#34d399;border:1px solid #10b98155;margin-bottom:12px}"
  "h1{font-size:19px;margin:0 0 6px;font-weight:700}p{font-size:13px;color:#9a9aa3;margin:0 0 16px;line-height:1.4}"
  ".selector-title{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#6b7280;margin-bottom:8px;text-align:left;font-weight:600}"
  ".target-switch{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:18px}"
  ".target-btn{padding:10px 8px;border-radius:8px;font-size:12px;font-weight:600;text-decoration:none;border:1px solid #282a32;color:#9ca3af;background:#111216;display:flex;flex-direction:column;align-items:center;gap:3px;transition:all .15s}"
  ".target-btn span{font-size:10px;opacity:0.75}"
  ".target-btn.active{border-color:#10b981;color:#fff;background:#064e3b44;box-shadow:0 0 0 1px #10b981 inset}"
  "input[type=file]{width:100%;padding:10px;border:1px dashed #3f4250;border-radius:8px;margin-bottom:14px;background:#101115;color:#ededf0;box-sizing:border-box;font-size:12px}"
  "button{background:#10b981;color:#052e16;border:none;border-radius:8px;padding:11px 16px;font-weight:700;width:100%;cursor:pointer;font-size:14px;transition:background .15s}"
  "button:hover:not(:disabled){background:#34d399}"
  "button:disabled{opacity:0.5;cursor:not-allowed}"
  "#status{margin-top:14px;font-size:13px;font-weight:600;min-height:20px}"
  ".nav-bar{margin-top:18px;padding-top:14px;border-top:1px solid #282a32;display:flex;justify-content:space-between;font-size:12px}"
  ".nav-bar a{color:#60a5fa;text-decoration:none;font-weight:500}"
  ".nav-bar a:hover{text-decoration:underline}"
  "</style></head><body><div class='card'>"
  "<div class='badge'>SISTEM KONTROL MOTOR &amp; NANO (STATION)</div>"
  "<h1>ESP32-Control OTA Update</h1>"
  "<p>Upload binary (.bin) untuk firmware ESP32 Sistem Kontrol (IP: 192.168.4.10:80).</p>"
  "<div class='selector-title'>Pilih Target Board ESP:</div>"
  "<div class='target-switch'>"
  "<a class='target-btn active' href='#'><b>ESP-Control</b><span>192.168.4.10 (Saat Ini)</span></a>"
  "<a class='target-btn' href='http://192.168.4.1/update'><b>ESP-CAM</b><span>192.168.4.1 ↗</span></a>"
  "</div>"
  "<input type='file' id='fw' accept='.bin'>"
  "<button id='btn' onclick='startUpdate()'>Flash ESP32-Control (.bin)</button>"
  "<div id='status'></div>"
  "<div class='nav-bar'>"
  "<a href='/'>← Status Motor/Servo</a>"
  "<a href='http://192.168.4.1/stream' target='_blank'>Stream Kamera (192.168.4.1) ↗</a>"
  "</div></div><script>"
  "async function startUpdate(){"
  "const f=document.getElementById('fw').files[0];"
  "if(!f)return alert('Pilih file .bin firmware kontrol!');"
  "const btn=document.getElementById('btn');const st=document.getElementById('status');"
  "btn.disabled=true;st.style.color='#38bdf8';st.textContent='Mengunggah & Flash... jangan matikan robot!';"
  "try{const res=await fetch('/update',{method:'POST',body:f});"
  "if(res.ok){st.style.color='#4ade80';st.textContent='SUKSES! ESP32-Control sedang reboot...';"
  "setTimeout(()=>location.reload(),7000);}"
  "else{st.style.color='#f87171';st.textContent='Gagal flash: HTTP '+res.status;btn.disabled=false;}}"
  "catch(e){st.style.color='#f87171';st.textContent='Error koneksi: '+e;btn.disabled=false;}}"
  "</script></body></html>";

static const char ROOT_CONTROL_HTML[] =
  "<!DOCTYPE html><html lang='id'><head><meta charset='utf-8'>"
  "<meta name='viewport' content='width=device-width,initial-scale=1'>"
  "<title>ESP32-Control Status Dashboard</title>"
  "<style>"
  "body{font-family:system-ui,sans-serif;background:#0c0d10;color:#ededf0;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;padding:16px;box-sizing:border-box}"
  ".card{background:#18191e;border:1px solid #282a32;border-radius:14px;padding:24px;width:min(440px,100%);box-shadow:0 8px 32px rgba(0,0,0,0.6)}"
  "h1{font-size:18px;margin:0 0 14px;color:#34d399}table{width:100%;border-collapse:collapse;font-size:13px;margin:12px 0}"
  "td{padding:8px 6px;border-bottom:1px solid #282a32}td:first-child{color:#9ca3af;width:40%}"
  "a.btn{display:inline-block;width:100%;text-align:center;background:#10b981;color:#052e16;padding:10px;border-radius:8px;font-weight:700;text-decoration:none;box-sizing:border-box;margin-top:12px}"
  "a.btn-cam{background:#2563eb;color:#fff;margin-top:8px}"
  "</style></head><body><div class='card'>"
  "<h1>ESP32-Control Status</h1>"
  "<table>"
  "<tr><td>Board</td><td>ESP32 Sistem Kontrol (Motor + Nano Aktuator)</td></tr>"
  "<tr><td>Wi-Fi Mode</td><td>Station -&gt; ESP32-CAM (dimas_asoy_geboy)</td></tr>"
  "<tr><td>IP Address</td><td>192.168.4.10 (OTA Port 80 &amp; UDP 8888)</td></tr>"
  "<tr><td>Target ESP-CAM</td><td>192.168.4.1 (AP Utama &amp; Kamera Stream)</td></tr>"
  "<tr><td>Failsafe</td><td>500 ms Auto-STOP Aktif</td></tr>"
  "</table>"
  "<a class='btn' href='/update'>Buka OTA Flash ESP32-Control ↗</a>"
  "<a class='btn btn-cam' href='http://192.168.4.1/update'>Buka OTA Flash ESP32-CAM (192.168.4.1) ↗</a>"
  "</div></body></html>";

static void set_cors_headers(httpd_req_t *req) {
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Headers", "Content-Type");
}

static esp_err_t ota_options_handler(httpd_req_t *req) {
  set_cors_headers(req);
  httpd_resp_set_status(req, "204 No Content");
  return httpd_resp_send(req, NULL, 0);
}

static esp_err_t ota_get_handler(httpd_req_t *req) {
  set_cors_headers(req);
  httpd_resp_set_type(req, "text/html; charset=utf-8");
  return httpd_resp_sendstr(req, OTA_CONTROL_HTML);
}

static esp_err_t root_get_handler(httpd_req_t *req) {
  set_cors_headers(req);
  httpd_resp_set_type(req, "text/html; charset=utf-8");
  return httpd_resp_sendstr(req, ROOT_CONTROL_HTML);
}

static esp_err_t ota_post_handler(httpd_req_t *req) {
  set_cors_headers(req);
  size_t total = req->content_len;
  if (!Update.begin(total > 0 ? total : UPDATE_SIZE_UNKNOWN)) {
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }
  char buf[1024];
  size_t remaining = total;
  while (remaining > 0) {
    int to_read = remaining < sizeof(buf) ? remaining : sizeof(buf);
    int received = httpd_req_recv(req, buf, to_read);
    if (received <= 0) {
      if (received == HTTPD_SOCK_ERR_TIMEOUT) continue;
      Update.abort();
      httpd_resp_send_500(req);
      return ESP_FAIL;
    }
    if (Update.write((uint8_t*)buf, received) != (size_t)received) {
      Update.abort();
      httpd_resp_send_500(req);
      return ESP_FAIL;
    }
    remaining -= received;
  }
  if (!Update.end(true)) {
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }
  httpd_resp_sendstr(req, "OK");
  delay(500);
  esp_restart();
  return ESP_OK;
}

void startControlServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.lru_purge_enable = true;
  config.max_open_sockets = 4;
  config.recv_wait_timeout = 3;
  config.send_wait_timeout = 3;

  httpd_uri_t ota_get_uri = {
    .uri       = "/update",
    .method    = HTTP_GET,
    .handler   = ota_get_handler,
    .user_ctx  = NULL
  };
  httpd_uri_t ota_post_uri = {
    .uri       = "/update",
    .method    = HTTP_POST,
    .handler   = ota_post_handler,
    .user_ctx  = NULL
  };
  httpd_uri_t ota_opt_uri = {
    .uri       = "/update",
    .method    = HTTP_OPTIONS,
    .handler   = ota_options_handler,
    .user_ctx  = NULL
  };
  httpd_uri_t root_uri = {
    .uri       = "/",
    .method    = HTTP_GET,
    .handler   = root_get_handler,
    .user_ctx  = NULL
  };

  if (httpd_start(&control_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(control_httpd, &ota_get_uri);
    httpd_register_uri_handler(control_httpd, &ota_post_uri);
    httpd_register_uri_handler(control_httpd, &ota_opt_uri);
    httpd_register_uri_handler(control_httpd, &root_uri);
    Serial.println("[ESP32-CONTROL] HTTP Web Server & OTA aktif di port 80 (http://192.168.4.10/update)");
  } else {
    Serial.println("[ESP32-CONTROL ERROR] Gagal memulai HTTP Web Server!");
  }
}

void applyMotorControl(float linear_x, float angular_z) {
  currentLinear = linear_x;
  currentAngular = angular_z;

  // Kinematika Differential Drive
  float v_left  = linear_x - (angular_z * WHEEL_BASE / 2.0f);
  float v_right = linear_x + (angular_z * WHEEL_BASE / 2.0f);

  // Skala ke PWM Dasar (0 - 255)
  int raw_pwm_left  = constrain((int)(abs(v_left) * 255.0f / MAX_SPEED), 0, 255);
  int raw_pwm_right = constrain((int)(abs(v_right) * 255.0f / MAX_SPEED), 0, 255);

  // Kompensasi Deadzone: Menembus gesekan statis motor DC gearbox agar tidak ngeden/stuck
  const int MIN_PWM = 60;
  int pwm_left  = (raw_pwm_left > 0) ? (MIN_PWM + (int)((raw_pwm_left * (255 - MIN_PWM)) / 255)) : 0;
  int pwm_right = (raw_pwm_right > 0) ? (MIN_PWM + (int)((raw_pwm_right * (255 - MIN_PWM)) / 255)) : 0;

  // Motor Kiri
  digitalWrite(IN1_PIN, v_left >= 0 ? HIGH : LOW);
  digitalWrite(IN2_PIN, v_left >= 0 ? LOW : HIGH);
  analogWrite(ENA_PIN, pwm_left);

  // Motor Kanan
  digitalWrite(IN3_PIN, v_right >= 0 ? HIGH : LOW);
  digitalWrite(IN4_PIN, v_right >= 0 ? LOW : HIGH);
  analogWrite(ENB_PIN, pwm_right);
}

void printESP32IPInfo() {
  IPAddress staIp = WiFi.localIP();
  Serial.println("\n==================================================");
  Serial.printf("[INFO ESP32-CONTROL] STA Target SSID  : %s (%s)\n", STA_SSID,
                WiFi.status() == WL_CONNECTED ? "TERHUBUNG" : "MENUNGGU AP CAM...");
  Serial.print("[INFO ESP32-CONTROL] STA IP Address   : "); Serial.println(staIp);
  Serial.printf("[INFO ESP32-CONTROL] HTTP & OTA Port  : 80 (http://%s/update)\n", staIp.toString().c_str());
  Serial.printf("[INFO ESP32-CONTROL] UDP Control Port : %d\n", UDP_PORT);
  Serial.println("==================================================\n");
}

void setup() {
  Serial.begin(115200);                                     // Debug Serial USB
  Serial2.begin(115200, SERIAL_8N1, RX2_PIN, TX2_PIN);     // Hardware Serial UART2 ke Arduino Nano Aktuator

  pinMode(ENA_PIN, OUTPUT);
  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);
  pinMode(ENB_PIN, OUTPUT);
  pinMode(IN3_PIN, OUTPUT);
  pinMode(IN4_PIN, OUTPUT);

  // Kirim posisi awal aktuator ke Arduino Nano
  delay(100);
  Serial2.printf("ACT:%d,%d,%d\n", currentCam, currentLift, currentGrip);

  // Inisialisasi Wi-Fi Station murni ke ESP32-CAM ("dimas-cam") dengan Static IP 192.168.4.10
  // (Lebih hemat daya & stabil daripada AP_STA; auto-reconnect di loop())
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);

  IPAddress local_IP(192, 168, 4, 10);
  IPAddress gateway(192, 168, 4, 1);
  IPAddress subnet(255, 255, 255, 0);
  WiFi.config(local_IP, gateway, subnet);
  WiFi.begin(STA_SSID, STA_PASS);
  WiFi.setSleep(false);

  Serial.printf("\n[ESP32-CONTROL] Menyambungkan ke AP '%s'...\n", STA_SSID);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 5000) {
    delay(200);
    Serial.print(".");
  }
  Serial.println();
  printESP32IPInfo();

  // Memulai HTTP Server Port 80 untuk OTA & status dashboard
  startControlServer();

  udp.begin(UDP_PORT);
  Serial.printf("[ESP32-CONTROL] UDP Listener nirkabel mendengarkan pada Port %d (IP: %s)...\n",
                UDP_PORT, WiFi.localIP().toString().c_str());
}

void handleCommand(float lin, float ang, int grip, int lift, int cam = -1) {
  applyMotorControl(lin, ang);
  currentGrip = constrain(grip, 0, 180);
  currentLift = constrain(lift, 0, 180);
  if (cam >= 0) {
    currentCam = constrain(cam, 0, 180);
  }

  // Teruskan instruksi aktuator (Kamera, Lift, Gripper) ke Arduino Nano via Serial2
  Serial2.printf("ACT:%d,%d,%d\n", currentCam, currentLift, currentGrip);

  lastCmdMs = millis();
  motorsStopped = (lin == 0.0f && ang == 0.0f);
}

void handleLine(char *line) {
  if (strncmp(line, "ACK:", 4) == 0) {
    // Respon ACK dari Arduino Nano aktuator
    return;
  }
  if (strncmp(line, "CMD:", 4) == 0) {
    float lin = 0.0f, ang = 0.0f;
    int grip = 0, lift = 0, cam = -1;
    int parsed = sscanf(line + 4, "%f,%f,%d,%d,%d", &lin, &ang, &grip, &lift, &cam);
    if (parsed >= 4) {
      handleCommand(lin, ang, grip, lift, cam >= 0 ? cam : currentCam);
    }

    static unsigned long lastPrint = 0;
    if (millis() - lastPrint > 300) {
      lastPrint = millis();
      Serial.printf("[RECV CMD] Lin:%.2f | Ang:%.2f | Cam:%d | Grip:%d | Lift:%d\n", lin, ang, currentCam, grip, lift);
    }
  }
}

void loop() {
  // Cetak info IP secara periodik tiap 5 detik
  if (millis() - lastIPPrintTime > 5000) {
    lastIPPrintTime = millis();
    printESP32IPInfo();
  }

  // 0. Auto-reconnect Wi-Fi Station jika terputus / ESP32-CAM baru menyala belakangan
  static unsigned long lastReconnectAttempt = 0;
  if (WiFi.status() != WL_CONNECTED && millis() - lastReconnectAttempt > 5000) {
    lastReconnectAttempt = millis();
    Serial.println("[ESP32-CONTROL] Wi-Fi terputus, mencoba menyambung ulang ke AP...");
    WiFi.disconnect(false);
    WiFi.begin(STA_SSID, STA_PASS);
  }

  // 1. Terima paket nirkabel UDP langsung dari Laptop / ESP32-CAM
  static IPAddress lastClientIP;
  static uint16_t lastClientPort = 0;
  int packetSize = udp.parsePacket();
  if (packetSize > 0) {
    IPAddress remote = udp.remoteIP();
    uint16_t rport = udp.remotePort();
    char packetBuffer[256];
    int len = udp.read(packetBuffer, sizeof(packetBuffer) - 1);
    if (len > 0) {
      packetBuffer[len] = 0;

      StaticJsonDocument<256> doc;
      DeserializationError error = deserializeJson(doc, packetBuffer);
      if (!error && (doc.containsKey("lin") || doc.containsKey("ang"))) {
        if (remote != IPAddress(192, 168, 4, 1)) {
          lastClientIP = remote;
          lastClientPort = rport;
        }
        float lin = doc["lin"] | 0.0f;
        float ang = doc["ang"] | 0.0f;
        int grip  = doc["grip"] | 0;
        int lift  = doc["lift"] | 0;
        int cam   = doc.containsKey("cam") ? (int)doc["cam"] : currentCam;

        handleCommand(lin, ang, grip, lift, cam);

        static unsigned long lastUdpPrint = 0;
        if (millis() - lastUdpPrint > 300) {
          lastUdpPrint = millis();
          Serial.printf("[RECV UDP NIRKABEL] Lin:%.2f | Ang:%.2f | Cam:%d | Grip:%d | Lift:%d\n", lin, ang, currentCam, grip, lift);
        }
      }
    }
  }

  // 2. Terima data kabel Serial2 (sebagai fallback/backup)
  while (Serial2.available()) {
    char c = (char)Serial2.read();
    if (c == '\n' || c == '\r') {
      if (lineLen > 0) {
        lineBuf[lineLen] = 0;
        handleLine(lineBuf);
        lineLen = 0;
      }
    } else if (lineLen < sizeof(lineBuf) - 1) {
      lineBuf[lineLen++] = c;
    } else {
      lineLen = 0;
    }
  }

  // 3. Failsafe: jika tidak ada perintah valid > 500 ms -> motor berhenti
  if (!motorsStopped && millis() - lastCmdMs > FAILSAFE_MS) {
    applyMotorControl(0.0f, 0.0f);
    motorsStopped = true;
    Serial.println("[FAILSAFE] Tidak ada perintah > 500 ms -> motor STOP");
  }

  // 4. Kirim pembacaan tegangan baterai nirkabel (UDP) & kabel (Serial2) tiap 1 detik
  static unsigned long lastBattMs = 0;
  if (millis() - lastBattMs > 1000) {
    lastBattMs = millis();
    int raw = analogRead(PIN_BATTERY_ADC);
    float v = (raw / 4095.0f) * 3.3f * BATT_DIVIDER_RATIO;
    if (v < 3.0f) v = 12.0f; // Default nilai aman jika resistor divider belum terpasang
    batteryVoltage = v;
    int pct = (v >= 9.0f) ? constrain((int)((v - 9.9f) / (12.6f - 9.9f) * 100), 0, 100) : 95;

    // Kirim via kabel Serial2
    Serial2.printf("BATT:%.2f\n", v);

    // Kirim nirkabel via UDP langsung ke Laptop, ESP32-CAM (192.168.4.1), dan broadcast (192.168.4.255)
    if (WiFi.status() == WL_CONNECTED) {
      char battBuf[64];
      int blen = snprintf(battBuf, sizeof(battBuf), "{\"batt\":%.2f,\"pct\":%d}\n", v, pct);

      if (lastClientPort > 0) {
        udp.beginPacket(lastClientIP, lastClientPort);
        udp.write((const uint8_t*)battBuf, blen);
        udp.endPacket();
      }

      udp.beginPacket(IPAddress(192, 168, 4, 1), UDP_PORT);
      udp.write((const uint8_t*)battBuf, blen);
      udp.endPacket();

      udp.beginPacket(IPAddress(192, 168, 4, 255), UDP_PORT);
      udp.write((const uint8_t*)battBuf, blen);
      udp.endPacket();
    }
  }

  delay(2);
}
