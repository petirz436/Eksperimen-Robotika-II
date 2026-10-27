/*
 * ESP32 Control System Firmware for AutoStack Eksbot2
 * ====================================================
 * Fitur:
 * 1. Menerima instruksi kabel Serial UART dari ESP32-CAM (Format: "CMD:lin,ang,grip,lift\n").
 * 2. Mengendalikan Motor DC Kiri & Kanan (Differential Drive PWM L298N/BTS7960).
 * 3. Mengendalikan Servo Gripper (Jepit/Buka) & Servo Lift (Angkat/Turun).
 * 4. Failsafe: motor berhenti bila tidak ada perintah valid selama 500 ms.
 *
 * PENTING (cek wiring robot Anda): pin di bawah BERBEDA dengan tes_manual_control/robot.ino
 * (robot.ino: ENA 4, IN1 16, IN2 17, ENB 19, IN3 21, IN4 18). Jika robot dirakit mengikuti
 * robot.ino, GPIO16/17 dipakai motor sehingga UART dari CAM harus dipindah ke pin lain.
 */

#include <ESP32Servo.h>

// PIN CONFIGURATION MOTOR DRIVER (L298N / BTS7960)
#define ENA_PIN 12  // PWM Speed Left
#define IN1_PIN 14  // Direction 1 Left
#define IN2_PIN 27  // Direction 2 Left

#define ENB_PIN 13  // PWM Speed Right
#define IN3_PIN 26  // Direction 1 Right
#define IN4_PIN 25  // Direction 2 Right

// PIN SERVO
#define SERVO_GRIPPER_PIN 18
#define SERVO_LIFT_PIN    19

// PIN HARDWARE SERIAL UART2 RECEIVER DARI ESP32-CAM
#define RX2_PIN 16
#define TX2_PIN 17

// PIN SENSOR BATERAI (ADC Input-Only GPIO34)
#define PIN_BATTERY_ADC 34
#define BATT_DIVIDER_RATIO 4.0f // Rasio pembagi tegangan (misal 30k:10k) untuk LiPo 3S (11.1V - 12.6V)

Servo gripperServo;
Servo liftServo;

const float WHEEL_BASE = 0.24; // 24 cm
const float MAX_SPEED  = 0.50; // 0.5 m/s
const unsigned long FAILSAFE_MS = 500;

unsigned long lastCmdMs = 0;
bool motorsStopped = true;
char lineBuf[64];
uint8_t lineLen = 0;

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

void setup() {
  Serial.begin(115200);                                     // Debug Serial USB
  Serial2.begin(115200, SERIAL_8N1, RX2_PIN, TX2_PIN);     // Hardware Serial UART2 Kabel dari ESP32-CAM

  pinMode(ENA_PIN, OUTPUT);
  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);
  pinMode(ENB_PIN, OUTPUT);
  pinMode(IN3_PIN, OUTPUT);
  pinMode(IN4_PIN, OUTPUT);

  gripperServo.attach(SERVO_GRIPPER_PIN);
  liftServo.attach(SERVO_LIFT_PIN);

  // Default Position
  gripperServo.write(0); // Open
  liftServo.write(0);    // Down

  Serial.println("[ESP32-CONTROL] Sistem Kontrol Siap Menerima Data Serial Cable!");
}

void handleLine(char *line) {
  if (strncmp(line, "CMD:", 4) != 0) return;
  float lin = 0.0, ang = 0.0;
  int grip = 0, lift = 0;
  // Parsing format CSV: "lin,ang,grip,lift"
  if (sscanf(line + 4, "%f,%f,%d,%d", &lin, &ang, &grip, &lift) != 4) return;

  applyMotorControl(lin, ang);
  gripperServo.write(constrain(grip, 0, 180));
  liftServo.write(constrain(lift, 0, 180));
  lastCmdMs = millis();
  motorsStopped = (lin == 0.0 && ang == 0.0);

  static unsigned long lastPrint = 0;
  if (millis() - lastPrint > 300) {   // Batasi print agar loop tidak melambat
    lastPrint = millis();
    Serial.printf("[EXECUTE] Lin:%.2f | Ang:%.2f | Grip:%d | Lift:%d\n", lin, ang, grip, lift);
  }
}

void loop() {
  // Baca semua byte yang tersedia tanpa memblokir (readStringUntil bisa menunggu 1 detik)
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
      lineLen = 0;   // Baris terlalu panjang/korup -> buang
    }
  }

  // Failsafe: kabel lepas / CAM reboot / laptop freeze -> motor berhenti
  if (!motorsStopped && millis() - lastCmdMs > FAILSAFE_MS) {
    applyMotorControl(0.0, 0.0);
    motorsStopped = true;
    Serial.println("[FAILSAFE] Tidak ada perintah > 500 ms -> motor STOP");
  }

  // Kirim pembacaan tegangan baterai ke ESP32-CAM tiap 1 detik
  static unsigned long lastBattMs = 0;
  if (millis() - lastBattMs > 1000) {
    lastBattMs = millis();
    int raw = analogRead(PIN_BATTERY_ADC);
    float v = (raw / 4095.0f) * 3.3f * BATT_DIVIDER_RATIO;
    if (v < 3.0f) v = 12.0f; // Default nilai aman jika resistor divider belum terpasang
    Serial2.printf("BATT:%.2f\n", v);
  }

  delay(2);
}
