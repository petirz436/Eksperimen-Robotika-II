/*
 * ESP32 Control System Firmware for AutoStack Eksbot2
 * ====================================================
 * Fitur:
 * 1. Menerima instruksi kabel Serial UART dari ESP32-CAM (Format: "CMD:lin,ang,grip,lift\n").
 * 2. Mengendalikan Motor DC Kiri & Kanan (Differential Drive PWM L298N/BTS7960).
 * 3. Mengendalikan Servo Gripper (Jepit/Buka) & Servo Lift (Angkat/Turun).
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

Servo gripperServo;
Servo liftServo;

const float WHEEL_BASE = 0.24; // 24 cm
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

void loop() {
  // Membaca pesan Serial dari ESP32-CAM
  if (Serial2.available()) {
    String inputStr = Serial2.readStringUntil('\n');
    inputStr.trim();

    if (inputStr.startsWith("CMD:")) {
      inputStr.remove(0, 4); // Hapus header "CMD:"

      float lin = 0.0, ang = 0.0;
      int grip = 0, lift = 0;

      // Parsing format CSV: "lin,ang,grip,lift"
      int firstComma  = inputStr.indexOf(',');
      int secondComma = inputStr.indexOf(',', firstComma + 1);
      int thirdComma  = inputStr.indexOf(',', secondComma + 1);

      if (firstComma != -1 && secondComma != -1 && thirdComma != -1) {
        lin  = inputStr.substring(0, firstComma).toFloat();
        ang  = inputStr.substring(firstComma + 1, secondComma).toFloat();
        grip = inputStr.substring(secondComma + 1, thirdComma).toInt();
        lift = inputStr.substring(thirdComma + 1).toInt();

        // Eksekusi Gerakan Motor
        applyMotorControl(lin, ang);

        // Eksekusi Servo
        gripperServo.write(constrain(grip, 0, 180));
        liftServo.write(constrain(lift, 0, 180));

        Serial.printf("[EXECUTE] Lin:%.2f | Ang:%.2f | Grip:%d | Lift:%d\n", lin, ang, grip, lift);
      }
    }
  }
  delay(10);
}
