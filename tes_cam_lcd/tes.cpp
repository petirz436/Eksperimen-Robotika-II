/**
 * 🧪 Test Sketch 01B: ESP32-WROVER + OV3660 Wi-Fi Visualizer
 * 
 * Program pengujian visualisasi Kamera OV3660 / OV2640 pada ESP32-WROVER (4MB/8MB PSRAM)
 * SEBELUM ESP32 dihubungkan ke layar LCD fisik (ST7789 / ILI9341).
 * 
 * 🛠️ DUKUNGAN HARDWARE:
 * - Microcontroller: ESP32-WROVER / ESP32-WROVER-DEV / AI-Thinker WROVER
 * - Sensor Kamera  : OV3660 3MP (Auto-detected) & OV2640 2MP
 * - PSRAM          : 4MB / 8MB External SPI RAM (ESP32-WROVER)
 * 
 * 🛠️ METODE VISUALISASI:
 * 1. 🌐 Wi-Fi Web Live Stream:
 *    - Connect HP/Laptop ke Wi-Fi AP: "PocketCam-Visualizer" (Pass: "password123")
 *    - Buka browser (Chrome/Safari) ke URL: http://192.168.4.1
 *    - Menampilkan video live stream MJPEG real-time, kontrol Flash LED, & stats sensor OV3660.
 */

#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"
#include <Arduino.h>

// --- PILIH MODEL BOARD SESUAI BOARD ESP32 ANDA (Aktifkan salah satu) ---
#define CAMERA_MODEL_WROVER_KIT   // Board ESP32-WROVER-DEV / WROVER Kit Default (Coba ini pertama!)
// #define CAMERA_MODEL_AI_THINKER // Board ESP32-CAM AI-Thinker
//#define CAMERA_MODEL_ESP_EYE    // Board ESP-EYE WROVER

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
  #define FLASH_LED_PIN    2
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
  #define FLASH_LED_PIN     4
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
  #define FLASH_LED_PIN    -1
#endif

// --- WI-FI ACCESS POINT CONFIG ---
const char* ap_ssid = "PocketCam-Visualizer";
const char* ap_password = "password123";

// Global Variables & HTTP Server Handler
httpd_handle_t stream_httpd = NULL;
httpd_handle_t camera_httpd = NULL;
bool flashState = false;
unsigned long frameCount = 0;
float fps = 0.0;
unsigned long lastFpsTime = 0;
String sensorModelName = "OV2640";


#define PART_BOUNDARY "123456789000000000000987654321"
static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* _STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

// HTML Page PROGMEM dengan Info OV3660
const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>📸 Pocket-Cam OV3660 Visualizer</title>
  <style>
    :root {
      --bg: #0f172a;
      --card: #1e293b;
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --text: #f8fafc;
      --text-muted: #94a3b8;
    }
    body {
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
    }
    .container {
      max-width: 640px;
      width: 100%;
      background: var(--card);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5);
      border: 1px solid rgba(255,255,255,0.1);
    }
    .header {
      text-align: center;
      margin-bottom: 20px;
    }
    .header h1 {
      margin: 0;
      font-size: 1.6rem;
      color: var(--accent);
    }
    .header p {
      margin: 5px 0 0;
      color: var(--text-muted);
      font-size: 0.9rem;
    }
    .viewfinder {
      position: relative;
      width: 100%;
      background: #000;
      border-radius: 12px;
      overflow: hidden;
      aspect-ratio: 4/3;
      display: flex;
      justify-content: center;
      align-items: center;
      border: 2px solid var(--accent);
    }
    .viewfinder img {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
    .controls {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 20px;
    }
    .btn {
      background: #334155;
      color: var(--text);
      border: none;
      padding: 12px;
      font-size: 1rem;
      font-weight: 600;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }
    .btn:hover { background: #475569; }
    .btn-primary { background: var(--accent); color: #0f172a; }
    .btn-primary:hover { background: var(--accent-hover); }
    .status-panel {
      margin-top: 20px;
      background: rgba(0,0,0,0.3);
      padding: 12px;
      border-radius: 8px;
      display: flex;
      justify-content: space-between;
      font-size: 0.85rem;
      color: var(--text-muted);
    }
    .badge {
      background: #22c55e;
      color: #052e16;
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: bold;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>📷 ESP32-WROVER Camera Visualizer</h1>
      <p>Pengujian Real-Time Sensor Kamera (Tanpa Layar LCD)</p>
    </div>

    <div class="viewfinder">
      <img src="" id="stream" alt="Live Stream Kamera">
    </div>

    <div class="controls">
      <button class="btn btn-primary" onclick="toggleFlash()">
        💡 Flash LED: <span id="flash-status">OFF</span>
      </button>
      <button class="btn" onclick="captureStill()">
        📸 Tangkap Foto
      </button>
    </div>

    <div class="status-panel">
      <div>Status: <span class="badge">ONLINE</span></div>
      <div>MCU: <b>ESP32-WROVER (PSRAM)</b></div>
      <div>Sensor: <b id="sensor-name">OV3660 / OV2640</b></div>
    </div>
  </div>

  <script>
    window.addEventListener('DOMContentLoaded', () => {
      const streamImg = document.getElementById('stream');
      if (streamImg) {
        streamImg.src = location.protocol + '//' + location.hostname + ':81/stream';
      }
    });
    function toggleFlash() {
      fetch('/flash')
        .then(res => res.text())
        .then(state => {
          const statusElem = document.getElementById('flash-status');
          if (statusElem) {
            statusElem.innerText = state.trim() === '1' ? 'ON' : 'OFF';
          }
        })
        .catch(err => console.error('Flash error:', err));
    }
    function captureStill() {
      window.open('/capture', '_blank');
    }
  </script>
</body>
</html>
)rawliteral";

// Handler Halaman Utama Index
static esp_err_t index_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, index_html, strlen(index_html));
}

// Handler MJPEG Video Stream
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t * _jpg_buf = NULL;
  char part_buf[64];

  res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
  if (res != ESP_OK) return res;

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("❌ Camera Frame Capture Failed");
      res = ESP_FAIL;
    } else {
      if (fb->format != PIXFORMAT_JPEG) {
        bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
        esp_camera_fb_return(fb);
        fb = NULL;
        if (!jpeg_converted) {
          Serial.println("❌ JPEG Compression Failed");
          res = ESP_FAIL;
        }
      } else {
        _jpg_buf_len = fb->len;
        _jpg_buf = fb->buf;
      }
    }

    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
    }
    if (res == ESP_OK) {
      size_t hlen = snprintf(part_buf, 64, _STREAM_PART, _jpg_buf_len);
      res = httpd_resp_send_chunk(req, part_buf, hlen);
    }
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    }

    if (fb) {
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if (_jpg_buf) {
      free(_jpg_buf);
      _jpg_buf = NULL;
    }

    if (res != ESP_OK) break;

    frameCount++;
    if (millis() - lastFpsTime >= 1000) {
      fps = frameCount;
      frameCount = 0;
      lastFpsTime = millis();
    }
  }
  return res;
}

// Handler Flash LED
static esp_err_t flash_handler(httpd_req_t *req) {
  flashState = !flashState;
  if (FLASH_LED_PIN >= 0) {
    digitalWrite(FLASH_LED_PIN, flashState ? HIGH : LOW);
  }
  httpd_resp_set_type(req, "text/plain");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, flashState ? "1" : "0", 1);
}

// Handler Capture Still Image (JPEG)
static esp_err_t capture_handler(httpd_req_t *req) {
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }
  
  uint8_t * jpg_buf = NULL;
  size_t jpg_len = 0;
  bool is_converted = false;
  
  if (fb->format != PIXFORMAT_JPEG) {
    is_converted = frame2jpg(fb, 80, &jpg_buf, &jpg_len);
    esp_camera_fb_return(fb);
    fb = NULL;
    if (!is_converted) {
      httpd_resp_send_500(req);
      return ESP_FAIL;
    }
  } else {
    jpg_buf = fb->buf;
    jpg_len = fb->len;
  }

  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture_ov3660.jpg");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  esp_err_t res = httpd_resp_send(req, (const char *)jpg_buf, jpg_len);

  if (is_converted && jpg_buf) {
    free(jpg_buf);
  } else if (fb) {
    esp_camera_fb_return(fb);
  }
  return res;
}

void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;

  httpd_config_t stream_config = HTTPD_DEFAULT_CONFIG();
  stream_config.server_port = 81;
  stream_config.ctrl_port = 32769;

  httpd_uri_t index_uri = {
    .uri       = "/",
    .method    = HTTP_GET,
    .handler   = index_handler,
    .user_ctx  = NULL
  };

  httpd_uri_t flash_uri = {
    .uri       = "/flash",
    .method    = HTTP_GET,
    .handler   = flash_handler,
    .user_ctx  = NULL
  };

  httpd_uri_t capture_uri = {
    .uri       = "/capture",
    .method    = HTTP_GET,
    .handler   = capture_handler,
    .user_ctx  = NULL
  };

  httpd_uri_t stream_uri = {
    .uri       = "/stream",
    .method    = HTTP_GET,
    .handler   = stream_handler,
    .user_ctx  = NULL
  };

  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &flash_uri);
    httpd_register_uri_handler(camera_httpd, &capture_uri);
  }

  if (httpd_start(&stream_httpd, &stream_config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
  }
}


void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=======================================================");
  Serial.println("  📸 POCKET-CAM: ESP32-WROVER + OV3660 VISUALIZER TEST ");
  Serial.println("=======================================================");

  pinMode(FLASH_LED_PIN, OUTPUT);
  digitalWrite(FLASH_LED_PIN, LOW);

  // 1. Cek Ketersediaan External PSRAM (ESP32-WROVER 4MB/8MB)
  if (psramFound()) {
    Serial.printf("✅ PSRAM WROVER Ditemukan! Ukuran: %d KB (%d MB)\n", 
                  ESP.getPsramSize() / 1024, ESP.getPsramSize() / (1024 * 1024));
  } else {
    Serial.println("⚠️ PSRAM Tidak Ditemukan! Periksa opsi PSRAM (Enabled) di Arduino IDE.");
  }

  // 2. Konfigurasi Kamera
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
  config.xclk_freq_hz = 10000000; // 10MHz untuk keandalan probe I2C SCCB pada OV3660
  config.pixel_format = PIXFORMAT_JPEG; // Native Hardware JPEG untuk Web MJPEG Stream

  if (psramFound()) {
    config.frame_size = FRAMESIZE_QVGA; // 320x240
    config.jpeg_quality = 10;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    config.frame_size = FRAMESIZE_HQVGA; // 240x176
    config.jpeg_quality = 12;
    config.fb_count = 1;
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  }

  // Inisialisasi Driver Kamera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("❌ Gagal inisialisasi Kamera! Error code: 0x%x\n", err);
    Serial.println("💡 SOLUSI ERROR 0x106 (ESP_ERR_NOT_SUPPORTED):");
    Serial.println("1. Jika menggunakan Board ESP32-WROVER-DEV, pastikan #define CAMERA_MODEL_WROVER_KIT aktif.");
    Serial.println("2. Jika menggunakan Board AI-Thinker WROVER, aktifkan #define CAMERA_MODEL_AI_THINKER di bagian atas sketch.");
    Serial.println("3. Tekan/kencangkan kabel pita fleksibel (ribbon cable) sensor OV3660 pada socket FPC ESP32.");
    return;
  }

  // 3. Deteksi & Optimasi Sensor OV3660 / OV2640
  sensor_t * s = esp_camera_sensor_get();
  if (s != NULL) {
    if (s->id.PID == OV3660_PID) {
      sensorModelName = "OV3660 (3 Megapixel)";
      Serial.println("🔍 SENSOR DETECTED: OV3660 (3MP Sensor)");
      
      // Auto-tuning khas sensor OV3660 untuk meningkatkan kualitas gambar
      s->set_vflip(s, 1);        // Flip vertikal jika gambar terbalik
      s->set_hmirror(s, 0);      // Horizontal mirror
      s->set_brightness(s, 1);   // -2 to 2
      s->set_contrast(s, 0);     // -2 to 2
      s->set_saturation(s, 1);   // -2 to 2
      s->set_whitebal(s, 1);     // Auto White Balance
    } else if (s->id.PID == OV2640_PID) {
      sensorModelName = "OV2640 (2 Megapixel)";
      Serial.println("🔍 SENSOR DETECTED: OV2640 (2MP Sensor)");
    } else {
      Serial.printf("🔍 SENSOR DETECTED PID: 0x%x\n", s->id.PID);
    }
  }

  Serial.println("✅ Sensor Kamera Berhasil Diinisialisasi!");

  // 4. Konfigurasi Wi-Fi Access Point (SoftAP Mode)
  Serial.println("🌐 Memulai Wi-Fi Access Point...");
  WiFi.softAP(ap_ssid, ap_password);
  IPAddress apIP = WiFi.softAPIP();

  Serial.println("=======================================================");
  Serial.printf("📶 SSID Wi-Fi  : %s\n", ap_ssid);
  Serial.printf("🔑 Password    : %s\n", ap_password);
  Serial.printf("🌐 Web Panel   : http://%s/\n", apIP.toString().c_str());
  Serial.printf("📹 Video Stream: http://%s:81/stream\n", apIP.toString().c_str());
  Serial.println("=======================================================");

  // 5. Start Web Server
  startCameraServer();
  Serial.println("🚀 Web Server Live Stream Berhasil Aktif!");
  Serial.println("📱 Hubungkan HP/Laptop ke Wi-Fi di atas dan buka browser.");
}

void loop() {
  // Web server berjalan di background task
  delay(1000);
}