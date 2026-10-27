/*
 * ESP32-CAM / ESP32-WROVER Firmware untuk AutoStack Eksbot2
 * =========================================================
 * Konfigurasi kamera DIAMBIL dari tes_cam_lcd/tescamesp.cpp (yang terbukti bisa connect
 * & tidak freeze di board WROVER yang sama), lalu ditambah bridge kontrol robot.
 *
 * Fitur:
 * 1. Wi-Fi SoftAP: SSID "dimas_asoy_geboy", Password "12345678" (IP: 192.168.4.1).
 * 2. HTTP MJPEG stream di http://192.168.4.1/stream (port 80, dipakai main.py).
 * 3. UDP listener port 8888: menerima JSON {"lin","ang","grip","lift"} dari Laptop.
 * 4. Meneruskan data kontrol ke ESP32 Sistem Kontrol lewat kabel UART (Serial2).
 * 5. Failsafe: jika Laptop berhenti mengirim data > 500 ms, robot dikirimi perintah STOP.
 *
 * WIRING UART (WROVER Kit):
 *   CAM GPIO33 (TX) -> CONTROL GPIO16 (RX2)
 *   CAM GPIO32 (RX) <- CONTROL GPIO17 (TX2)
 *   GND CAM <-> GND CONTROL
 *   PENTING: GPIO16/17 pada WROVER dipakai PSRAM, JANGAN dipakai untuk Serial2 di sisi CAM.
 *
 * Library: hanya library bawaan ESP32 core (tanpa ArduinoJson).
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiUdp.h>
#include "esp_http_server.h"
#include <Update.h>
#include <stdlib.h>

// --- PILIH MODEL BOARD SESUAI BOARD ESP32 ANDA ---
#define CAMERA_MODEL_WROVER_KIT   // Board ESP32-WROVER-DEV / WROVER Kit (sama dengan tescamesp.cpp)
// #define CAMERA_MODEL_AI_THINKER // Board ESP32-CAM AI-Thinker
// #define CAMERA_MODEL_ESP_EYE    // Board ESP-EYE WROVER

#if defined(CAMERA_MODEL_WROVER_KIT)
  #define PWDN_GPIO_NUM    -1
  #define RESET_GPIO_NUM   -1
  #define XCLK_GPIO_NUM    21
  #define SIOD_GPIO_NUM    26
  #define SIOC_GPIO_NUM    27
  #define Y9_GPIO_NUM      35
  #define Y8_GPIO_NUM      34
  #define Y7_GPIO_NUM      39
  #define Y6_GPIO_NUM      36
  #define Y5_GPIO_NUM      19
  #define Y4_GPIO_NUM      18
  #define Y3_GPIO_NUM       5
  #define Y2_GPIO_NUM       4
  #define VSYNC_GPIO_NUM   25
  #define HREF_GPIO_NUM    23
  #define PCLK_GPIO_NUM    22
  #define UART2_TX_PIN     33   // Bebas dari kamera & PSRAM
  #define UART2_RX_PIN     32
#elif defined(CAMERA_MODEL_AI_THINKER)
  #define PWDN_GPIO_NUM    32
  #define RESET_GPIO_NUM   -1
  #define XCLK_GPIO_NUM     0
  #define SIOD_GPIO_NUM    26
  #define SIOC_GPIO_NUM    27
  #define Y9_GPIO_NUM      35
  #define Y8_GPIO_NUM      34
  #define Y7_GPIO_NUM      39
  #define Y6_GPIO_NUM      36
  #define Y5_GPIO_NUM      21
  #define Y4_GPIO_NUM      19
  #define Y3_GPIO_NUM      18
  #define Y2_GPIO_NUM       5
  #define VSYNC_GPIO_NUM   25
  #define HREF_GPIO_NUM    23
  #define PCLK_GPIO_NUM    22
  #define UART2_TX_PIN     14   // GPIO16 = PSRAM CS pada AI-Thinker, jadi pakai 14/15
  #define UART2_RX_PIN     15
#elif defined(CAMERA_MODEL_ESP_EYE)
  #define PWDN_GPIO_NUM    -1
  #define RESET_GPIO_NUM   -1
  #define XCLK_GPIO_NUM     4
  #define SIOD_GPIO_NUM    18
  #define SIOC_GPIO_NUM    23
  #define Y9_GPIO_NUM      36
  #define Y8_GPIO_NUM      37
  #define Y7_GPIO_NUM      38
  #define Y6_GPIO_NUM      39
  #define Y5_GPIO_NUM      35
  #define Y4_GPIO_NUM      14
  #define Y3_GPIO_NUM      13
  #define Y2_GPIO_NUM      34
  #define VSYNC_GPIO_NUM    5
  #define HREF_GPIO_NUM    27
  #define PCLK_GPIO_NUM    25
  #define UART2_TX_PIN     33
  #define UART2_RX_PIN     32
#endif

// Orientasi sensor OV3660 (sama dengan tescamesp.cpp). Ubah 0/1 jika gambar terbalik.
#define CAM_VFLIP_OV3660    1
#define CAM_HMIRROR_OV3660  0

// CONFIG WI-FI SOFTAP & UDP
const char* AP_SSID = "dimas_asoy_geboy";
const char* AP_PASS = "12345678";
const int UDP_PORT = 8888;

// Failsafe: kirim STOP jika tidak ada paket kontrol selama (ms)
const unsigned long FAILSAFE_MS = 500;

WiFiUDP udp;
httpd_handle_t stream_httpd = NULL;
volatile bool camera_ready = false;
unsigned long lastCameraTry = 0;

// State perintah terakhir (untuk failsafe & debug)
int lastGrip = 0, lastLift = 0;
unsigned long lastCmdMs = 0;
bool failsafeSent = true;
unsigned long lastDebugMs = 0;

#define PART_BOUNDARY "123456789000000000000987654321"
static const char* STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* STREAM_PART = "\r\n--" PART_BOUNDARY "\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

// ------------------------------------------------------------
// HTTP Handler untuk Stream MJPEG Kamera
// ------------------------------------------------------------
static esp_err_t stream_handler(httpd_req_t *req) {
  if (!camera_ready) {
    httpd_resp_set_status(req, "503 Service Unavailable");
    return httpd_resp_sendstr(req, "Camera is not ready");
  }

  esp_err_t res = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
  if (res != ESP_OK) return res;
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  char part_buf[96];
  int failCount = 0;

  while (true) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
      // Gagal ambil frame: coba lagi sebentar, jika terus gagal tutup koneksi agar client reconnect.
      if (++failCount > 20) { res = ESP_FAIL; break; }
      delay(10);
      continue;
    }
    failCount = 0;

    if (fb->format != PIXFORMAT_JPEG) {   // Tidak diharapkan: kamera dikonfigurasi JPEG
      esp_camera_fb_return(fb);
      res = ESP_FAIL;
      break;
    }

    // Boundary + header digabung jadi 1 chunk (2 kali kirim per frame, bukan 3) -> latensi lebih kecil
    size_t hlen = snprintf(part_buf, sizeof(part_buf), STREAM_PART, (unsigned)fb->len);
    res = httpd_resp_send_chunk(req, part_buf, hlen);
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    }
    esp_camera_fb_return(fb);   // Selalu kembalikan frame buffer secepatnya

    if (res != ESP_OK) break;   // Client putus -> keluar, jangan menahan server
    delay(1);                   // Beri kesempatan task Wi-Fi/IDLE (cegah watchdog & starvasi)
  }
  return res;
}

// ------------------------------------------------------------
// OTA Web Update Handler (Wireless Firmware Flash via Wi-Fi)
// ------------------------------------------------------------
static const char OTA_HTML[] =
  "<!DOCTYPE html><html lang='id'><head><meta charset='utf-8'>"
  "<meta name='viewport' content='width=device-width,initial-scale=1'>"
  "<title>Eksbot2 OTA Firmware Update</title>"
  "<style>"
  "body{font-family:system-ui,sans-serif;background:#0c0d10;color:#ededf0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}"
  ".card{background:#18191e;border:1px solid #282a32;border-radius:12px;padding:24px;width:min(380px,92vw);text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.5)}"
  "h1{font-size:18px;margin:0 0 10px;font-weight:650}p{font-size:13px;color:#9a9aa3;margin:0 0 18px}"
  "input[type=file]{width:100%;padding:8px;border:1px dashed #3f4250;border-radius:8px;margin-bottom:14px;background:#101115;color:#ededf0;box-sizing:border-box}"
  "button{background:#3b82f6;color:#fff;border:none;border-radius:8px;padding:10px 16px;font-weight:600;width:100%;cursor:pointer}"
  "button:disabled{opacity:0.5;cursor:not-allowed}#status{margin-top:14px;font-size:13px;font-weight:600;min-height:20px}"
  ".back{display:inline-block;margin-top:14px;font-size:12px;color:#3b82f6;text-decoration:none}"
  "</style></head><body><div class='card'>"
  "<h1>Eksbot2 OTA Update</h1><p>Pilih file binary firmware (.bin) hasil kompilasi untuk update wireless.</p>"
  "<input type='file' id='fw' accept='.bin'>"
  "<button id='btn' onclick='startUpdate()'>Flash Firmware (.bin)</button>"
  "<div id='status'></div>"
  "<a class='back' href='http://192.168.4.1/stream'>← Cek Stream Kamera</a>"
  "</div><script>"
  "async function startUpdate(){"
  "const f=document.getElementById('fw').files[0];"
  "if(!f)return alert('Pilih file .bin!');"
  "const btn=document.getElementById('btn');const st=document.getElementById('status');"
  "btn.disabled=true;st.style.color='#38bdf8';st.textContent='Mengunggah & Flash... jangan matikan robot!';"
  "try{const res=await fetch('/update',{method:'POST',body:f});"
  "if(res.ok){st.style.color='#4ade80';st.textContent='SUKSES! ESP32-CAM sedang reboot...';"
  "setTimeout(()=>location.reload(),7000);}"
  "else{st.style.color='#f87171';st.textContent='Gagal flash: HTTP '+res.status;btn.disabled=false;}}"
  "catch(e){st.style.color='#f87171';st.textContent='Error koneksi: '+e;btn.disabled=false;}}"
  "</script></body></html>";

static esp_err_t ota_get_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/html; charset=utf-8");
  return httpd_resp_sendstr(req, OTA_HTML);
}

static esp_err_t ota_post_handler(httpd_req_t *req) {
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

void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.lru_purge_enable = true;
  config.max_open_sockets = 4;
  config.recv_wait_timeout = 3;
  config.send_wait_timeout = 3;

  httpd_uri_t stream_uri = {
    .uri       = "/stream",
    .method    = HTTP_GET,
    .handler   = stream_handler,
    .user_ctx  = NULL
  };
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

  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
    httpd_register_uri_handler(stream_httpd, &ota_get_uri);
    httpd_register_uri_handler(stream_httpd, &ota_post_uri);
    Serial.println("MJPEG stream aktif di http://192.168.4.1/stream");
    Serial.println("OTA Update Web Page aktif di http://192.168.4.1/update");
  } else {
    Serial.println("Gagal memulai HTTP stream pada port 80.");
  }
}

// ------------------------------------------------------------
// Inisialisasi Kamera (konfigurasi identik dengan tescamesp.cpp)
// ------------------------------------------------------------
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 10000000;   // 10 MHz: stabil dengan kabel/jumper (20 MHz sering bermasalah)
  config.pixel_format = PIXFORMAT_JPEG;

  if (psramFound()) {
    config.frame_size = FRAMESIZE_QVGA;          // 320x240: sesuai ambang vision.py & ringan di SoftAP
    config.jpeg_quality = 10;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;       // Selalu kirim frame TERBARU (bukan antrean basi)
  } else {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Kamera Error: 0x%x (cek model board/pin kamera)\n", err);
    esp_camera_deinit();
    return false;
  }

  sensor_t *s = esp_camera_sensor_get();
  if (s != NULL) {
    if (s->id.PID == OV3660_PID) {
      s->set_vflip(s, CAM_VFLIP_OV3660);
      s->set_hmirror(s, CAM_HMIRROR_OV3660);
      s->set_brightness(s, 1);
      Serial.println("Sensor: OV3660");
    } else if (s->id.PID == OV2640_PID) {
      Serial.println("Sensor: OV2640");
    }
  }
  return true;
}

// ------------------------------------------------------------
// Parser angka JSON sederhana (tahan terhadap spasi dari json.dumps Python: "lin": 0.3)
// ------------------------------------------------------------
static bool jsonNumber(const char *buf, const char *key, float *out) {
  char pat[16];
  snprintf(pat, sizeof(pat), "\"%s\"", key);
  const char *p = strstr(buf, pat);
  if (!p) return false;
  p += strlen(pat);
  while (*p == ' ' || *p == ':') p++;
  char *end = NULL;
  float v = strtof(p, &end);
  if (end == p) return false;
  *out = v;
  return true;
}

static void forwardToControl(float lin, float ang, int grip, int lift) {
  // Format yang dipahami firmware_esp32_control.ino
  Serial2.printf("CMD:%.2f,%.2f,%d,%d\n", lin, ang, grip, lift);
  if (millis() - lastDebugMs > 300) {   // Batasi debug print agar loop tidak melambat
    lastDebugMs = millis();
    Serial.printf("[BRIDGE -> SERIAL2] CMD:%.2f,%.2f,%d,%d\n", lin, ang, grip, lift);
  }
}

void setup() {
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, UART2_RX_PIN, UART2_TX_PIN);   // Kabel ke ESP32 Kontroler
  delay(500);
  Serial.println("\n=== ESP32 CAM + UDP BRIDGE (AutoStack Eksbot2) ===");

  // 1. Kamera dulu (urutan sama dengan tescamesp.cpp). Jika gagal, AP TETAP dinyalakan
  //    supaya board tetap bisa dikoneksikan & didiagnosis, kamera dicoba ulang di loop().
  camera_ready = initCamera();
  lastCameraTry = millis();

  // 2. Wi-Fi Access Point
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);
  WiFi.setSleep(false);   // Matikan power-save Wi-Fi: mengurangi jitter/latensi
  Serial.print("ESP32-CAM Access Point Aktif. SSID: ");
  Serial.print(AP_SSID);
  Serial.print(" | IP: ");
  Serial.println(WiFi.softAPIP());

  // 3. Server stream + UDP
  startCameraServer();
  udp.begin(UDP_PORT);
  Serial.printf("UDP Server mendengarkan pada port %d\n", UDP_PORT);
  Serial.println(camera_ready ? "Kamera siap." : "Kamera BELUM siap (akan dicoba ulang tiap 5 detik).");
}

void loop() {
  // 1. Baca data telemetri baterai dari ESP32-Control via Serial2
  static float lastBattV = 12.0f;
  static int lastBattPct = 95;
  static char s2Buf[32];
  static uint8_t s2Len = 0;
  while (Serial2.available()) {
    char c = (char)Serial2.read();
    if (c == '\n' || c == '\r') {
      if (s2Len > 0) {
        s2Buf[s2Len] = 0;
        if (strncmp(s2Buf, "BATT:", 5) == 0) {
          lastBattV = strtof(s2Buf + 5, NULL);
          if (lastBattV >= 9.0f) {
            lastBattPct = constrain((int)((lastBattV - 9.9f) / (12.6f - 9.9f) * 100), 0, 100);
          } else if (lastBattV >= 6.0f) {
            lastBattPct = constrain((int)((lastBattV - 6.6f) / (8.4f - 6.6f) * 100), 0, 100);
          }
        }
        s2Len = 0;
      }
    } else if (s2Len < sizeof(s2Buf) - 1) {
      s2Buf[s2Len++] = c;
    } else {
      s2Len = 0;
    }
  }

  // 2. Kuras paket UDP kontrol dari Laptop
  bool got = false;
  float lin = 0.0f, ang = 0.0f;
  char packetBuffer[256];
  static IPAddress lastLaptopIP;
  static uint16_t lastLaptopPort = 0;
  static unsigned long lastBattUdpMs = 0;

  while (udp.parsePacket() > 0) {
    lastLaptopIP = udp.remoteIP();
    lastLaptopPort = udp.remotePort();
    int len = udp.read(packetBuffer, sizeof(packetBuffer) - 1);
    if (len <= 0) continue;
    packetBuffer[len] = 0;

    float tLin, tAng, tGrip, tLift;
    if (jsonNumber(packetBuffer, "lin", &tLin) && jsonNumber(packetBuffer, "ang", &tAng)) {
      lin = tLin;
      ang = tAng;
      if (jsonNumber(packetBuffer, "grip", &tGrip)) lastGrip = (int)tGrip;
      if (jsonNumber(packetBuffer, "lift", &tLift)) lastLift = (int)tLift;
      got = true;
    }
  }

  // Kirim balasan status baterai ke Laptop tiap 1 detik
  if (lastLaptopPort > 0 && millis() - lastBattUdpMs > 1000) {
    lastBattUdpMs = millis();
    udp.beginPacket(lastLaptopIP, lastLaptopPort);
    udp.printf("{\"batt\":%.2f,\"pct\":%d}\n", lastBattV, lastBattPct);
    udp.endPacket();
  }

  if (got) {
    forwardToControl(lin, ang, lastGrip, lastLift);
    lastCmdMs = millis();
    failsafeSent = false;
  } else if (!failsafeSent && millis() - lastCmdMs > FAILSAFE_MS) {
    forwardToControl(0.0f, 0.0f, lastGrip, lastLift);   // Laptop diam/freeze -> robot berhenti
    Serial.println("[FAILSAFE] Tidak ada data kontrol -> STOP");
    failsafeSent = true;
  }

  // Kamera gagal saat boot (kabel longgar/salah pin)? Coba lagi tanpa reboot.
  if (!camera_ready && millis() - lastCameraTry > 5000) {
    lastCameraTry = millis();
    camera_ready = initCamera();
    if (camera_ready) Serial.println("Kamera siap (retry berhasil).");
  }

  delay(2);
}
