/*
 * ESP32 Control System Firmware - Direct Wi-Fi Test (Tanpa Kamera)
 * =================================================================
 * Fitur:
 * 1. ESP32 Sistem Kontrol memancarkan Wi-Fi Access Point (SoftAP):
 *    - SSID: "dimas_asoy_geboy" (atau "AutoStack-Control-Test")
 *    - Pass: "12345678"
 *    - IP Default: 192.168.4.1
 * 2. UDP Server pada Port 8888 mendengarkan JSON paket dari Laptop.
 * 3. Mengendalikan Motor DC (L298N/BTS7960) & Servo Gripper/Lift secara langsung.
 */

#include <WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>

// PIN CONFIGURATION MOTOR DRIVER (L298N / BTS7960)
#define ENA_PIN 4  // PWM Speed Left
#define IN1_PIN 16  // Direction 1 Left
#define IN2_PIN 17  // Direction 2 Left

#define ENB_PIN 19  // PWM Speed Right
#define IN3_PIN 21  // Direction 1 Right
#define IN4_PIN 18  // Direction 2 Right

// PIN SERVO
#define SERVO_GRIPPER_PIN 7
#define SERVO_LIFT_PIN    3

// CONFIG WI-FI SOFTAP & UDP
const char* AP_SSID = "dimas_asoy_geboy";
const char* AP_PASS = "12345678";
const int UDP_PORT  = 8888;

WiFiUDP udp;
Servo gripperServo;
Servo liftServo;

const float WHEEL_BASE = 0.26; // 24 cm
const float MAX_SPEED  = 0.50; // 0.5 m/s

void applyMotorControl(float linear_x, float angular_z) {
  // Kinematika Differential Drive
  float v_left  = linear_x - (angular_z * WHEEL_BASE / 2.0);
  float v_right = linear_x + (angular_z * WHEEL_BASE / 2.0);

  // Skala ke PWM (0 - 255)
  int pwm_left  = constrain(abs(v_left) * 255.0 / MAX_SPEED, 0, 255);
  int pwm_right = constrain(abs(v_right) * 255.0 / MAX_SPEED, 0, 255);

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
  IPAddress ip = WiFi.softAPIP();
  Serial.println("\n==================================================");
  Serial.print("[INFO ESP32] Wi-Fi SSID       : "); Serial.println(AP_SSID);
  Serial.print("[INFO ESP32] SoftAP IP Address : "); Serial.println(ip);
  Serial.print("[INFO ESP32] Client Terhubung  : "); Serial.println(WiFi.softAPgetStationNum());
  Serial.printf("[INFO ESP32] UDP Control Port  : %d\n", UDP_PORT);
  Serial.println("==================================================\n");
}

void setup() {
  Serial.begin(115200);

  pinMode(ENA_PIN, OUTPUT);
  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);
  pinMode(ENB_PIN, OUTPUT);
  pinMode(IN3_PIN, OUTPUT);
  pinMode(IN4_PIN, OUTPUT);

  gripperServo.attach(SERVO_GRIPPER_PIN);
  liftServo.attach(SERVO_LIFT_PIN);

  // Default Servo Position
  gripperServo.write(0); // Open
  liftServo.write(0);    // Down

  // Inisialisasi Wi-Fi Access Point
  WiFi.softAP(AP_SSID, AP_PASS);
  
  // Cetak Info IP ESP32
  printESP32IPInfo();

  udp.begin(UDP_PORT);
  Serial.printf("UDP Listener mendengarkan pada Port %d...\n", UDP_PORT);
}

unsigned long lastIPPrintTime = 0;

void loop() {
  // Cetak IP Info secara periodik tiap 5 detik ke Serial Monitor
  if (millis() - lastIPPrintTime > 5000) {
    lastIPPrintTime = millis();
    printESP32IPInfo();
  }

  int packetSize = udp.parsePacket();
  if (packetSize) {
    char packetBuffer[255];
    int len = udp.read(packetBuffer, 255);
    if (len > 0) packetBuffer[len] = 0;

    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, packetBuffer);

    if (!error) {
      float lin  = doc["lin"]  | 0.0;
      float ang  = doc["ang"]  | 0.0;
      int grip   = doc["grip"] | 0;
      int lift   = doc["lift"] | 0;

      // Eksekusi Gerakan Motor
      applyMotorControl(lin, ang);

      // Eksekusi Servo
      gripperServo.write(constrain(grip, 0, 180));
      liftServo.write(constrain(lift, 0, 180));

      Serial.printf("[RECV] Lin: %.2f | Ang: %.2f | Grip: %d | Lift: %d\n", lin, ang, grip, lift);
    }
  }
  delay(5);
}
