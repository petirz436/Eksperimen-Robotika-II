/*
 * Arduino Nano Actuator Sub-Controller Firmware
 * ==============================================
 * Board: Arduino Nano (ATmega328P / ATmega328P Old Bootloader)
 *
 * Jalur Komunikasi:
 * - Menerima instruksi via Hardware Serial (RX Pin D0, TX Pin D1) @ 115200 baud
 *   terhubung ke ESP32 Control (TX2 GPIO 22 -> Nano RX D0).
 * - Common GND: Pastikan GND Arduino Nano dan GND ESP32 terhubung bersama!
 *
 * Aktuator yang Dikendalikan:
 * 1. SERVO KAMERA  : Pin D9  (Sudut: 0 - 180°, Default: 90° Netral)
 * 2. SERVO LIFTER  : Pin D10 (Sudut: 0 - 180°, Default: 0° Bawah / Down)
 * 3. SERVO GRIPPER : Pin D11 (Sudut: 0 - 180°, Default: 0° Terbuka / Open)
 *
 * Persiapan Stepper Lifter (Bisa diaktifkan via #define LIFTER_USE_STEPPER 1):
 * - STEP: Pin D5, DIR: Pin D6, ENABLE: Pin D7
 *
 * Format Protokol Serial:
 * "ACT:<cam>,<lift>,<grip>\n"
 * Contoh: "ACT:90,0,0\n"     -> Kamera 90°, Lift Turun 0°, Gripper Buka 0°
 * Contoh: "ACT:90,90,90\n"   -> Kamera 90°, Lift Naik 90°, Gripper Jepit 90°
 * Mendukung juga perintah "PING\n" -> Dibalas "PONG\n"
 */

#include <Arduino.h>
#include <Servo.h>

// ======================================================================
// KONFIGURASI PIN & HARDWARE
// ======================================================================
#define SERVO_CAM_PIN     9   // Pin PWM Servo Kamera
#define SERVO_LIFT_PIN    10  // Pin PWM Servo Lifter
#define SERVO_GRIP_PIN    11  // Pin PWM Servo Gripper
#define LED_INDICATOR_PIN 13  // LED bawaan Nano (indikator penerimaan data)

// Atur ke 1 jika Lifter sudah diganti dari Servo menjadi Motor Stepper
#define LIFTER_USE_STEPPER 0

#if LIFTER_USE_STEPPER
#define STEPPER_STEP_PIN  5
#define STEPPER_DIR_PIN   6
#define STEPPER_EN_PIN    7
const long STEPS_PER_UNIT = 800; // Contoh resolusi langkah
long targetStepperPos = 0;
long currentStepperPos = 0;
#endif

// ======================================================================
// OBJEK SERVO & VARIABEL STATE
// ======================================================================
Servo servoCam;
Servo servoLift;
Servo servoGrip;

int currentCamAngle  = 90; // Default posisi netral tengah
int currentLiftAngle = 0;  // Default posisi bawah
int currentGripAngle = 0;  // Default posisi terbuka

char rxBuffer[64];
uint8_t rxIndex = 0;
unsigned long lastCmdTime = 0;
unsigned long lastLedBlink = 0;

// ======================================================================
// FUNGSI EKSEKUSI AKTUATOR
// ======================================================================
void applyActuators(int cam, int lift, int grip) {
  // Batasi nilai rentang 0 - 180 derajat
  currentCamAngle  = constrain(cam, 0, 180);
  currentLiftAngle = constrain(lift, 0, 180);
  currentGripAngle = constrain(grip, 0, 180);

  // 1. Eksekusi Servo Kamera
  servoCam.write(currentCamAngle);

  // 2. Eksekusi Lifter
#if LIFTER_USE_STEPPER
  // Konversi sudut (0-180) ke langkah stepper target
  targetStepperPos = map(currentLiftAngle, 0, 180, 0, 3200);
#else
  servoLift.write(currentLiftAngle);
#endif

  // 3. Eksekusi Gripper
  servoGrip.write(currentGripAngle);

  // Kedipkan LED indikator tanda perintah aktif dieksekusi
  digitalWrite(LED_INDICATOR_PIN, HIGH);
  lastLedBlink = millis();
}

// ======================================================================
// PARSING PERINTAH SERIAL
// ======================================================================
void parseCommand(char* cmd) {
  // Format: "ACT:<cam>,<lift>,<grip>"
  if (strncmp(cmd, "ACT:", 4) == 0) {
    int cam = currentCamAngle;
    int lift = currentLiftAngle;
    int grip = currentGripAngle;

    if (sscanf(cmd + 4, "%d,%d,%d", &cam, &lift, &grip) >= 1) {
      applyActuators(cam, lift, grip);
      lastCmdTime = millis();
      Serial.println(F("ACK:OK"));
    }
  } else if (strncmp(cmd, "PING", 4) == 0) {
    Serial.println(F("PONG"));
  }
}

// ======================================================================
// SETUP
// ======================================================================
void setup() {
  // Hardware Serial ke ESP32 @ 115200 baud
  Serial.begin(115200);

  pinMode(LED_INDICATOR_PIN, OUTPUT);
  digitalWrite(LED_INDICATOR_PIN, LOW);

  // Pasang Servo Pin
  servoCam.attach(SERVO_CAM_PIN);
#if LIFTER_USE_STEPPER
  pinMode(STEPPER_STEP_PIN, OUTPUT);
  pinMode(STEPPER_DIR_PIN, OUTPUT);
  pinMode(STEPPER_EN_PIN, OUTPUT);
  digitalWrite(STEPPER_EN_PIN, LOW); // Aktifkan driver
#else
  servoLift.attach(SERVO_LIFT_PIN);
#endif
  servoGrip.attach(SERVO_GRIP_PIN);

  // Set Posisi Default Awal
  applyActuators(currentCamAngle, currentLiftAngle, currentGripAngle);

  Serial.println(F("[NANO-ACTUATOR] Siap menerima kontrol dari ESP32 Control!"));
}

// ======================================================================
// LOOP UTAMA
// ======================================================================
void loop() {
  // 1. Baca data Serial secara non-blocking
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (rxIndex > 0) {
        rxBuffer[rxIndex] = '\0';
        parseCommand(rxBuffer);
        rxIndex = 0;
      }
    } else if (rxIndex < sizeof(rxBuffer) - 1) {
      rxBuffer[rxIndex++] = c;
    } else {
      rxIndex = 0; // Buffer overflow, reset
    }
  }

  // 2. Matikan LED kedip setelah 50ms
  if (digitalRead(LED_INDICATOR_PIN) == HIGH && (millis() - lastLedBlink > 50)) {
    digitalWrite(LED_INDICATOR_PIN, LOW);
  }

#if LIFTER_USE_STEPPER
  // Penggerak stepper bertahap (non-blocking)
  if (currentStepperPos < targetStepperPos) {
    digitalWrite(STEPPER_DIR_PIN, HIGH);
    digitalWrite(STEPPER_STEP_PIN, HIGH);
    delayMicroseconds(400);
    digitalWrite(STEPPER_STEP_PIN, LOW);
    delayMicroseconds(400);
    currentStepperPos++;
  } else if (currentStepperPos > targetStepperPos) {
    digitalWrite(STEPPER_DIR_PIN, LOW);
    digitalWrite(STEPPER_STEP_PIN, HIGH);
    delayMicroseconds(400);
    digitalWrite(STEPPER_STEP_PIN, LOW);
    delayMicroseconds(400);
    currentStepperPos--;
  }
#endif
}

