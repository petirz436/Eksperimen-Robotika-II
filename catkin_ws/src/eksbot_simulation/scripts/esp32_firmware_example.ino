/*
 * ESP32 ROS Control Bridge for AutoStack Robot
 * 
 * Hardware:
 *  - ESP32 WROOM-32 / ESP32-CAM
 *  - L298N / BTS7960 / DRV8833 Motor Driver
 *  - Servos (Gripper & Lift)
 *
 * ROS Topics:
 *  - Subscribe: /cmd_vel (geometry_msgs/Twist) -> Driver motor DC kiri & kanan
 *  - Subscribe: /esp32/servo (std_msgs/Int32)  -> Posisi servo gripper
 */


 //buatkan separate program untuk eksbot2 lalu buatkan fitur agar vision dapat deteksi R G dan B untuk yg deteksi coklat apus aja soalnya itu uji coba. lalu berikan tombol untuk switch mode warna
#include <WiFi.h>
#include <ros.h>
#include <geometry_msgs/Twist.h>
#include <std_msgs/Int32.h>
#include <ESP32Servo.h>

// PIN CONFIGURATION
#define ENA_PIN 12  # PWM Motor Left
#define IN1_PIN 14  # Dir 1 Left
#define IN2_PIN 27  # Dir 2 Left

#define ENB_PIN 13  # PWM Motor Right
#define IN3_PIN 26  # Dir 1 Right
#define IN4_PIN 25  # Dir 2 Right

#define SERVO_GRIPPER_PIN 18
#define SERVO_LIFT_PIN 19

Servo gripperServo;
Servo liftServo;

// ROS Node Handle
ros::NodeHandle nh;

// Differential Drive Parameters
const float WHEEL_BASE = 0.24; // 24 cm
const float WHEEL_RADIUS = 0.04; // 4 cm

void cmdVelCallback(const geometry_msgs::Twist& msg) {
  float linear_x = msg.linear.x;
  float angular_z = msg.angular.z;

  // Differential Drive Kinematics
  float v_left  = linear_x - (angular_z * WHEEL_BASE / 2.0);
  float v_right = linear_x + (angular_z * WHEEL_BASE / 2.0);

  // Map to PWM (0 - 255)
  int pwm_left  = constrain(abs(v_left) * 255.0 / 0.5, 0, 255);
  int pwm_right = constrain(abs(v_right) * 255.0 / 0.5, 0, 255);

  // Left Motor Direction
  digitalWrite(IN1_PIN, v_left >= 0 ? HIGH : LOW);
  digitalWrite(IN2_PIN, v_left >= 0 ? LOW : HIGH);
  analogWrite(ENA_PIN, pwm_left);

  // Right Motor Direction
  digitalWrite(IN3_PIN, v_right >= 0 ? HIGH : LOW);
  digitalWrite(IN4_PIN, v_right >= 0 ? LOW : HIGH);
  analogWrite(ENB_PIN, pwm_right);
}

void servoCallback(const std_msgs::Int32& msg) {
  int angle = constrain(msg.data, 0, 180);
  gripperServo.write(angle);
}

ros::Subscriber<geometry_msgs::Twist> subCmdVel("/cmd_vel", &cmdVelCallback);
ros::Subscriber<std_msgs::Int32> subServo("/esp32/servo", &servoCallback);

void setup() {
  pinMode(ENA_PIN, OUTPUT);
  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);
  pinMode(ENB_PIN, OUTPUT);
  pinMode(IN3_PIN, OUTPUT);
  pinMode(IN4_PIN, OUTPUT);

  gripperServo.attach(SERVO_GRIPPER_PIN);
  liftServo.attach(SERVO_LIFT_PIN);

  // ROS Serial / Wi-Fi Initialization
  nh.initNode();
  nh.subscribe(subCmdVel);
  nh.subscribe(subServo);
}

void loop() {
  nh.spinOnce();
  delay(10);
}
