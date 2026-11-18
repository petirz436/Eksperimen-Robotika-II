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
 * 1. SERVO KAMERA (SG90)      : Pin D2       (Sudut: 0 - 180°, Default: 90° Netral)
 * 2. LIFTER STEPPER (28BYJ-48): Pin D7, D8, D9, D10 -> ULN2003 IN1..IN4
 * 3. SERVO GRIPPER KIRI/KANAN : Pin D11, D12 (Sudut: 0 - 180°, Default: 0° Terbuka / Open)
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
#define SERVO_CAM_PIN     2  // Pin Servo Kamera
#define CAM_RAMP_MS       18 // Jeda (ms) tiap 1 derajat gerak servo kamera agar smooth
#define SERVO_GRIP_L_PIN  3  // Pin Servo Gripper Kiri
#define SERVO_GRIP_R_PIN  4  // Pin Servo Gripper Kanan
#define SERVO_SAPU_PIN    5  // Pin Servo Penyapu
#define GRIP_R_INVERT     1  // 1 = arah kanan dibalik (180 - grip) agar menjepit simetris, 0 = searah

#define STEPPER_IN1_PIN   7
#define STEPPER_IN2_PIN   8
#define STEPPER_IN3_PIN   9
#define STEPPER_IN4_PIN   10
#define STEPPER_MAX_STEPS 4096L       // 4096 half-step = 1 putaran penuh 28BYJ-48 (sesuaikan panjang tali kerek)
#define STEPPER_STEP_US   1100UL      // Interval antar half-step (microseconds, ~900 step/detik)
#define STEPPER_HOLD_COIL 0           // 0 = matikan koil saat diam (dingin & hemat baterai), 1 = tahan posisi

const uint8_t HALF_STEP_SEQ[8][4] = {
  {1, 0, 0, 0},
  {1, 1, 0, 0},
  {0, 1, 0, 0},
  {0, 1, 1, 0},
  {0, 0, 1, 0},
  {0, 0, 1, 1},
  {0, 0, 0, 1},
  {1, 0, 0, 1}
};

long targetStepperPos = 0;
long currentStepperPos = 0;
uint8_t stepPhase = 0;
unsigned long lastStepUs = 0;
bool coilsActive = false;

void setStepperCoils(uint8_t phase) {
  digitalWrite(STEPPER_IN1_PIN, HALF_STEP_SEQ[phase][0]);
  digitalWrite(STEPPER_IN2_PIN, HALF_STEP_SEQ[phase][1]);
  digitalWrite(STEPPER_IN3_PIN, HALF_STEP_SEQ[phase][2]);
  digitalWrite(STEPPER_IN4_PIN, HALF_STEP_SEQ[phase][3]);
  coilsActive = true;
}

void releaseStepperCoils() {
  digitalWrite(STEPPER_IN1_PIN, LOW);
  digitalWrite(STEPPER_IN2_PIN, LOW);
  digitalWrite(STEPPER_IN3_PIN, LOW);
  digitalWrite(STEPPER_IN4_PIN, LOW);
  coilsActive = false;
}

// ======================================================================
// OBJEK SERVO & VARIABEL STATE
// ======================================================================
Servo servoCam;
Servo servoGripL;
Servo servoGripR;

int currentCamAngle  = 90; // Posisi aktual servo kamera
int targetCamAngle   = 90; // Target posisi servo kamera (untuk smooth ramp)
int currentLiftAngle = 0;  // Default posisi bawah
int currentGripAngle = 0;  // Default posisi terbuka

char rxBuffer[64];
uint8_t rxIndex = 0;
unsigned long lastCmdTime = 0;
unsigned long lastCamRampMs = 0;

// ======================================================================
// FUNGSI EKSEKUSI AKTUATOR
// ======================================================================
void applyActuators(int cam, int lift, int grip) {
  // Batasi nilai rentang 0 - 180 derajat
  targetCamAngle   = constrain(cam, 0, 180);
  currentLiftAngle = constrain(lift, 0, 180);
  currentGripAngle = constrain(grip, 0, 180);

  // 1. Servo Kamera digerakkan bertahap (smooth ramp) di loop()

  // 2. Eksekusi Lifter Stepper 28BYJ-48
  targetStepperPos = map(currentLiftAngle, 0, 180, 0, STEPPER_MAX_STEPS);

  // 3. Eksekusi Gripper Kiri & Kanan (gerak menjepit simetris)
  int gripL = currentGripAngle;
  int gripR = GRIP_R_INVERT ? (180 - currentGripAngle) : currentGripAngle;
  servoGripL.write(gripL);
  servoGripR.write(gripR);
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

  // Pasang Servo & Pin Stepper
  servoCam.attach(SERVO_CAM_PIN);
  pinMode(STEPPER_IN1_PIN, OUTPUT);
  pinMode(STEPPER_IN2_PIN, OUTPUT);
  pinMode(STEPPER_IN3_PIN, OUTPUT);
  pinMode(STEPPER_IN4_PIN, OUTPUT);
  releaseStepperCoils();
  servoGripL.attach(SERVO_GRIP_L_PIN);
  servoGripR.attach(SERVO_GRIP_R_PIN);

  // Set Posisi Default Awal
  servoCam.write(currentCamAngle);
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

  // 2. Smooth ramp Servo Kamera (geser 1 derajat tiap CAM_RAMP_MS agar halus)
  if (currentCamAngle != targetCamAngle) {
    unsigned long nowMs = millis();
    if (nowMs - lastCamRampMs >= CAM_RAMP_MS) {
      lastCamRampMs = nowMs;
      currentCamAngle += (currentCamAngle < targetCamAngle) ? 1 : -1;
      servoCam.write(currentCamAngle);
    }
  }

  // 3. Penggerak stepper 28BYJ-48 (half-step non-blocking berbasis micros())
  if (currentStepperPos != targetStepperPos) {
    unsigned long nowUs = micros();
    if (nowUs - lastStepUs >= STEPPER_STEP_US) {
      lastStepUs = nowUs;
      if (currentStepperPos < targetStepperPos) {
        stepPhase = (stepPhase + 1) & 0x07;
        currentStepperPos++;
      } else {
        stepPhase = (stepPhase + 7) & 0x07;
        currentStepperPos--;
      }
      setStepperCoils(stepPhase);
    }
  } else if (!STEPPER_HOLD_COIL && coilsActive) {
    releaseStepperCoils();
  }
}

