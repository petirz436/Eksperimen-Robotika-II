/*
 * ESP32-CAM Firmware for AutoStack Eksbot2
 * ========================================
 * Fitur:
 * 1. Menjadi Wi-Fi Access Point (SoftAP): SSID "AutoStack-ESP-CAM", Password "12345678" (IP: 192.168.4.1).
 * 2. HTTP MJPEG Camera Streaming Server pada port 80 (/stream).
 * 3. UDP Socket Listener pada port 8888 menerima instruksi kontrol dari Laptop.
 * 4. Meneruskan data kontrol ke ESP32 Sistem Kontrol via Hardware Serial UART2 (TX2: Pin 17, RX2: Pin 16).
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiUdp.h>
#include "esp_http_server.h"
#include <ArduinoJson.h>

// PIN CONFIGURATION UNTUK ESP32-CAM (AI-THINKER MODEL)
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// SERIAL UART2 KE ESP32 KONTROLER
#define UART2_TX_PIN      17
#define UART2_RX_PIN      16

// CONFIG WI-FI SOFTAP
const char* AP_SSID = "AutoStack-ESP-CAM";
const char* AP_PASS = "12345678";
const int UDP_PORT = 8888;

WiFiUDP udp;
httpd_handle_t stream_httpd = NULL;

// HTTP Handler untuk Stream MJPEG Kamera
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t * _jpg_buf = NULL;
  char * part_buf[64];

  res = httpd_resp_set_type(req, "multipart/x-mixed-replace; boundary=123456789000000000000987654321");
  if(res != ESP_OK) return res;

  while(true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      delay(10);
      continue;
    }
    if(fb->format != PIXFORMAT_JPEG){
      bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
      esp_camera_fb_return(fb);
      fb = NULL;
      if(!jpeg_converted) res = ESP_FAIL;
    } else {
      _jpg_buf_len = fb->len;
      _jpg_buf = fb->buf;
    }

    if(res == ESP_OK){
      size_t hlen = snprintf((char *)part_buf, 64, "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", _jpg_buf_len);
      res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
    }
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    }
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, "\r\n--123456789000000000000987654321\r\n", 37);
    }
    if(fb){
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if(_jpg_buf){
      free(_jpg_buf);
      _jpg_buf = NULL;
    }
    if(res != ESP_OK) break;
  }
  return res;
}

void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;

  httpd_uri_t stream_uri = {
    .uri       = "/stream",
    .method    = HTTP_GET,
    .handler   = stream_handler,
    .user_ctx  = NULL
  };

  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
  }
}

void setup() {
  Serial.begin(115200); // Debug Serial
  Serial2.begin(115200, SERIAL_8N1, UART2_RX_PIN, UART2_TX_PIN); // Hardware Serial2 Kabel ke ESP32 Kontroler

  // Inisialisasi Konfigurasi Kamera
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
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  if(psramFound()){
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 12;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 15;
    config.fb_count = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Kamera Error: 0x%x", err);
    return;
  }

  // Inisialisasi Wi-Fi Access Point (SoftAP)
  WiFi.softAP(AP_SSID, AP_PASS);
  IPAddress IP = WiFi.softAPIP();
  Serial.print("ESP32-CAM Access Point Aktif. IP: ");
  Serial.println(IP);

  startCameraServer();
  udp.begin(UDP_PORT);
  Serial.printf("UDP Server mendengarkan pada port %d\n", UDP_PORT);
}

void loop() {
  // Mendengarkan Paket UDP Wi-Fi dari Laptop
  int packetSize = udp.parsePacket();
  if (packetSize) {
    char packetBuffer[255];
    int len = udp.read(packetBuffer, 255);
    if (len > 0) packetBuffer[len] = 0;

    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, packetBuffer);

    if (!error) {
      float lin = doc["lin"] | 0.0;
      float ang = doc["ang"] | 0.0;
      int grip = doc["grip"] | 0;
      int lift = doc["lift"] | 0;

      // Teruskan paket data ke ESP32 Kontroler via Kabel Serial UART2
      char serialMsg[64];
      snprintf(serialMsg, sizeof(serialMsg), "CMD:%.2f,%.2f,%d,%d\n", lin, ang, grip, lift);
      Serial2.print(serialMsg);
      Serial.print("[BRIDGE -> SERIAL2]: ");
      Serial.print(serialMsg);
    }
  }
  delay(5);
}
