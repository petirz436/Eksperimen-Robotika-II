#!/usr/bin/env python3
"""
Eksbot2 Robot Interface API Module (robot_api.py)
------------------------------------------------
Modul antarmuka pengiriman instruksi gerak (velocity) dan kontrol servo (gripper/lift).
Mendukung pengiriman lewat ROS Topic (/cmd_vel) untuk Simulasi Gazebo 
SERTA pengiriman langsung via Socket UDP/HTTP Wi-Fi ke ESP32-CAM fisik.
"""

import time
import socket
import json
import urllib.request

try:
    import rospy
    from geometry_msgs.msg import Twist
    from std_msgs.msg import Int32, Bool
    HAS_ROS = True
except ImportError:
    HAS_ROS = False

class RobotAPI:
    def __init__(self, esp_ip="192.168.4.1", esp_port=8888, use_ros=True):
        self.esp_ip = esp_ip
        self.esp_port = esp_port
        self.use_ros = use_ros and HAS_ROS
        
        # ROS Publishers
        self.cmd_pub = None
        self.servo_pub = None
        self.lift_pub = None
        self.vacuum_pub = None

        # UDP Socket untuk pengiriman Wi-Fi langsung ke ESP32-CAM
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # State Kecepatan & Servo Terakhir
        self.current_linear_x = 0.0
        self.current_angular_z = 0.0
        self.current_gripper = 0   # 0: OPEN, 90: CLOSED
        self.current_lift = 0      # 0: DOWN, 90: UP

        if self.use_ros:
            self._init_ros()

    def _init_ros(self):
        """Menginisialisasi ROS node & publisher jika belum diinisialisasi."""
        try:
            if not rospy.get_node_uri():
                rospy.init_node("eksbot_modular_api_node", anonymous=True)
            self.cmd_pub = rospy.Publisher("/cmd_vel", Twist, queue_size=1)
            self.servo_pub = rospy.Publisher("/esp32/servo", Int32, queue_size=1)
            self.lift_pub = rospy.Publisher("/esp32/lift", Int32, queue_size=1)
            self.vacuum_pub = rospy.Publisher("/dummy_robot/gripper_switch", Bool, queue_size=1)
            print("[ROBOT_API] ROS Publishers terinisialisasi aktif! (/cmd_vel, /esp32/servo, /esp32/lift, /dummy_robot/gripper_switch)")
        except Exception as e:
            print(f"[ROBOT_API] ROS tidak aktif, fallback ke Wi-Fi UDP Socket: {e}")
            self.use_ros = False

    def move(self, linear_x, angular_z):
        """Mengirimkan instruksi kecepatan maju/mundur (linear_x) dan belok (angular_z)."""
        self.current_linear_x = float(linear_x)
        self.current_angular_z = float(angular_z)

        # 1. Kirim via ROS
        if self.use_ros and self.cmd_pub is not None:
            twist = Twist()
            twist.linear.x = self.current_linear_x
            twist.angular.z = self.current_angular_z
            self.cmd_pub.publish(twist)

        # 2. Kirim via Wi-Fi UDP Socket ke ESP32-CAM
        payload = {
            "cmd": "move",
            "lin": round(self.current_linear_x, 2),
            "ang": round(self.current_angular_z, 2),
            "grip": self.current_gripper,
            "lift": self.current_lift
        }
        self._send_udp_esp(payload)

    def set_gripper(self, angle_or_state):
        """
        Mengatur posisi servo gripper (Jepit/Buka).
        Param: angle (int) 0 - 180 ATAU string 'OPEN' (0) / 'CLOSE' (90).
        """
        if isinstance(angle_or_state, str):
            angle = 90 if angle_or_state.upper() in ["CLOSE", "GRAB", "JEPIT"] else 0
        else:
            angle = int(angle_or_state)

        self.current_gripper = max(0, min(angle, 180))

        if self.use_ros and self.servo_pub is not None:
            self.servo_pub.publish(Int32(data=self.current_gripper))
            if self.vacuum_pub is not None:
                is_closed = self.current_gripper > 45
                self.vacuum_pub.publish(Bool(data=is_closed))

        self.move(self.current_linear_x, self.current_angular_z)
        print(f"[ROBOT_API] Gripper Servo Set: {self.current_gripper}° ({'CLOSE/GRAB' if self.current_gripper > 45 else 'OPEN/RELEASE'})")

    def set_lift(self, angle_or_state):
        """
        Mengatur posisi servo lift (Naik/Turun).
        Param: angle (int) 0 - 180 ATAU string 'UP' (90) / 'DOWN' (0).
        """
        if isinstance(angle_or_state, str):
            angle = 90 if angle_or_state.upper() in ["UP", "NAIK"] else 0
        else:
            angle = int(angle_or_state)

        self.current_lift = max(0, min(angle, 180))

        if self.use_ros and self.lift_pub is not None:
            self.lift_pub.publish(Int32(data=self.current_lift))

        self.move(self.current_linear_x, self.current_angular_z)
        print(f"[ROBOT_API] Lift Servo Set: {self.current_lift}°")

    def stop(self):
        """Mengehentikan semua gerakan robot."""
        self.move(0.0, 0.0)

    def _send_udp_esp(self, payload_dict):
        """Mengirimkan JSON string payload via UDP ke ESP32-CAM."""
        try:
            msg_bytes = json.dumps(payload_dict).encode('utf-8')
            self.sock.sendto(msg_bytes, (self.esp_ip, self.esp_port))
        except Exception:
            pass # Silent send error jika Wi-Fi fisik belum terhubung saat simulasi
