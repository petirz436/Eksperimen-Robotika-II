#!/usr/bin/env python3
"""
Eksbot2 Main Control Application (main.py)
------------------------------------------
Aplikasi utama pengendalikan robot Eksbot2.
Fitur Utama:
1. Kontrol Manual Real-time menggunakan keyboard WSAD (W:Maju, S:Mundur, A:Kiri, D:Kanan).
2. Kontrol Servo Manual (J:Jepit, K:Buka, U:Angkat Lift, I:Turunkan Lift).
3. Switch Mode Warna RGB (Key 1: Merah, Key 2: Hijau, Key 3: Biru).
4. Auto Navigasi Vision Tracking berdasarkan error terhitung dari vision.py.
5. Mendukung Jalur Simulasi Gazebo (ROS Topic) maupun Robot Fisik (ESP32-CAM Wi-Fi).
"""

import sys
import time
import cv2 as cv
import numpy as np
import urllib.request

from vision import VisionEngine
from robot_api import RobotAPI

try:
    import rospy
    from sensor_msgs.msg import Image
    from cv_bridge import CvBridge, CvBridgeError
    HAS_ROS = True
except ImportError:
    HAS_ROS = False

# ============================================================
# ROS IMAGE SUBSCRIBER
# ============================================================
class ROSImageSub:
    def __init__(self, topic="/camera/image_raw"):
        self.bridge = CvBridge()
        self.frame = None
        self.sub = rospy.Subscriber(topic, Image, self.callback)

    def callback(self, data):
        try:
            self.frame = self.bridge.imgmsg_to_cv2(data, "bgr8")
        except CvBridgeError:
            pass

    def read(self):
        if self.frame is not None:
            return True, self.frame.copy()
        return False, None

# ============================================================
# HTTP MJPEG STREAM READER FOR ESP32-CAM
# ============================================================
class ESPCamReader:
    def __init__(self, url):
        self.url = url
        self.stream = None
        self.bytes = b''
        self._opened = False
        self.connect()

    def connect(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            self.stream = urllib.request.urlopen(req, timeout=3)
            self._opened = True
            print(f"[CAM_READER] Terhubung ke stream ESP32-CAM: {self.url}")
        except Exception as e:
            print(f"[CAM_READER] Gagal membuka stream ESP32-CAM ({self.url}): {e}")
            self._opened = False

    def read(self):
        if not self._opened or self.stream is None:
            return False, None
        try:
            while True:
                self.bytes += self.stream.read(1024)
                a = self.bytes.find(b'\xff\xd8')
                b = self.bytes.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    jpg = self.bytes[a:b+2]
                    self.bytes = self.bytes[b+2:]
                    frame = cv.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv.IMREAD_COLOR)
                    if frame is not None:
                        return True, frame
        except Exception:
            self._opened = False
            return False, None

    def release(self):
        if self.stream:
            try: self.stream.close()
            except: pass

# ============================================================
# MOUSE CALLBACK FOR TARGET SELECTION
# ============================================================
selected_bbox = None
click_point = None

def mouse_cb(event, x, y, flags, param):
    global click_point
    if event == cv.EVENT_LBUTTONDOWN:
        click_point = (x, y)

# ============================================================
# MAIN APPLICATION LOOP
# ============================================================
def main():
    global click_point

    print("==================================================")
    print("      EKSBOT2 MODULAR CONTROL & VISION SYSTEM     ")
    print("==================================================")
    
    # Inisialisasi ROS jika tersedia
    ros_active = False
    ros_sub = None
    if HAS_ROS:
        try:
            rospy.init_node("eksbot2_main_node", anonymous=True)
            image_topic = rospy.get_param("~image_topic", "/camera/image_raw")
            use_sim = rospy.get_param("~use_sim", True)
            if use_sim:
                ros_sub = ROSImageSub(image_topic)
                ros_active = True
                print(f"[MAIN] Mode ROS Simulasi Aktif! Membaca dari topik: {image_topic}")
        except Exception as e:
            print(f"[MAIN] Memulai tanpa ROS Master Node: {e}")

    # Inisialisasi Camera Capture Source jika ROS tidak aktif
    cap = None
    esp_cam_url = "http://192.168.4.1/stream"
    if not ros_active:
        print(f"[MAIN] Membuka Stream ESP32-CAM: {esp_cam_url}")
        cap = ESPCamReader(esp_cam_url)
        if not cap._opened:
            print("[MAIN] Stream ESP32-CAM tidak ditemukan, fallback ke Webcam Lokal (index 0)...")
            cap = cv.VideoCapture(0)

    # Inisialisasi Modul Vision & Robot API
    vision = VisionEngine()
    robot = RobotAPI(esp_ip="192.168.4.1", esp_port=8888, use_ros=ros_active)

    window_name = "Eksbot2 Control Center (WSAD Manual & Vision RGB)"
    cv.namedWindow(window_name)
    cv.setMouseCallback(window_name, mouse_cb)

    manual_mode = True  # Mode Default: Manual Control WSAD
    speed_linear = 0.30
    speed_angular = 1.2

    target_lin = 0.0
    target_ang = 0.0
    last_move_key_time = 0.0
    auto_align_phase = "ALIGNING"  # "ALIGNING" (Putar di Tempat) atau "DRIVING" (Maju Adaptif)

    print("\n[PETUNJUK KONTROL KEYBOARD RESPANSIF]")
    print(" M        : Switch Mode (MANUAL WSAD <--> AUTO VISION NAVIGASI)")
    print(" W / S    : Maju / Mundur (Manual Mode)")
    print(" A / D    : Belok Kiri / Belok Kanan (Manual Mode)")
    print(" SPACE    : Stop / Rem Robot")
    print(" J / K    : Jepit (Gripper Close) / Buka (Gripper Open)")
    print(" U / I    : Naikkan Lift (Up) / Turunkan Lift (Down)")
    print(" 1 / 2 / 3: Ganti Mode Target Warna (1: MERAH, 2: HIJAU, 3: BIRU)")
    print(" R        : Reset Vision Lock Target")
    print(" ESC      : Keluar dari Program\n")

    last_time = time.time()

    try:
        while True:
            if ros_active:
                if rospy.is_shutdown(): break
                ret, frame = ros_sub.read()
                if not ret:
                    time.sleep(0.01)
                    continue
            else:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.02)
                    continue

            frame_h, frame_w = frame.shape[:2]

            # 1. Olah Frame Gambar dengan Vision Engine
            frame_vis, v_data = vision.process_frame(frame, manual_mode=manual_mode)

            # 2. Tangani Klik Mouse pada Mode Vision Auto
            if not manual_mode and click_point is not None and not v_data.get("tracking", False):
                px, py = click_point
                for target in v_data.get("detected_targets", []):
                    tx, ty, tw, th = target["bbox"]
                    if tx <= px <= tx + tw and ty <= py <= ty + th:
                        vision.lock_target_bbox(frame, target["bbox"])
                        auto_align_phase = "ALIGNING"
                        break
                click_point = None

            # 3. Logika Navigasi Otomatis (Jika Mode Vision Auto Aktif)
            if not manual_mode:
                if v_data.get("tracking", False):
                    norm_x = v_data.get("norm_x", 0.0)
                    target_cy = v_data.get("target_cy", frame_h // 2)
                    target_area = v_data.get("target_area", 0)

                    # Deteksi Guncangan / Target Bergerak Cepat -> Kembalikan ke Koreksi Orientasi
                    if abs(norm_x) > 0.35:
                        auto_align_phase = "ALIGNING"

                    # FASE 1: Rotasi di Tempat (Orientasi Presisi Terlebih Dahulu)
                    if auto_align_phase == "ALIGNING":
                        lin_x = 0.0
                        ang_z = np.clip(-2.5 * norm_x, -1.8, 1.8)
                        if abs(norm_x) <= 0.08:
                            auto_align_phase = "DRIVING"

                    # FASE 2: Maju Adaptif (PWM Berubah Sesuai Error Pixel Angular & Distance)
                    else:
                        # Base speed maju disesuaikan dengan jarak target di layar
                        dist_ratio = max(0.0, float(frame_h - target_cy) / float(frame_h))
                        lin_x = np.clip(0.12 + 0.25 * dist_ratio, 0.12, 0.32)

                        # Perubahan PWM tiap roda diatur oleh offset angular terintegrasi
                        ang_z = -1.2 * norm_x

                        # Auto Grip & Lift saat target berada di jangkauan robot
                        if target_cy > (frame_h - 2) or target_area > 12000:
                            print("[AUTO-GRIP] Target tercapai! Eksekusi jepit dan angkat...")
                            robot.stop()
                            time.sleep(0.2)
                            robot.set_lift("DOWN")
                            time.sleep(0.4)
                            robot.set_gripper("CLOSE")
                            time.sleep(0.6)
                            robot.set_lift("UP")
                            time.sleep(0.5)
                            vision.reset_tracker()
                            auto_align_phase = "ALIGNING"
                            lin_x, ang_z = 0.0, 0.0

                    robot.move(lin_x, ang_z)
                    cv.putText(frame_vis, f"AUTO NAV: {auto_align_phase} | Lin: {lin_x:.2f} Ang: {ang_z:.2f}",
                               (20, frame_h - 20), cv.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
                else:
                    robot.stop()
                    auto_align_phase = "ALIGNING"

            # 4. Tangani Input Keyboard Real-Time (Fast 1ms Sampling)
            key = cv.waitKey(1) & 0xFF

            if key == 27:  # ESC
                break
            elif key == ord('m') or key == ord('M'):
                manual_mode = not manual_mode
                robot.stop()
                target_lin, target_ang = 0.0, 0.0
                auto_align_phase = "ALIGNING"
                print(f"[MODE SWITCH] Mode berganti ke: {'MANUAL WSAD' if manual_mode else 'AUTO VISION NAVIGASI'}")
            elif key == ord('1'):
                vision.set_color_mode("RED")
            elif key == ord('2'):
                vision.set_color_mode("GREEN")
            elif key == ord('3'):
                vision.set_color_mode("BLUE")
            elif key == ord('r') or key == ord('R'):
                vision.reset_tracker()
                auto_align_phase = "ALIGNING"
                if not manual_mode: robot.stop()

            # Kontrol Servo
            elif key == ord('j') or key == ord('J'):
                robot.set_gripper("CLOSE")
            elif key == ord('k') or key == ord('K'):
                robot.set_gripper("OPEN")
            elif key == ord('u') or key == ord('U'):
                robot.set_lift("UP")
            elif key == ord('i') or key == ord('I'):
                robot.set_lift("DOWN")

            # Kontrol Manual
            if manual_mode:
                now_t = time.time()
                if key == ord('w') or key == ord('W'):
                    target_lin, target_ang = speed_linear, 0.0
                    last_move_key_time = now_t
                elif key == ord('s') or key == ord('S'):
                    target_lin, target_ang = -speed_linear, 0.0
                    last_move_key_time = now_t
                elif key == ord('a') or key == ord('A'):
                    target_lin, target_ang = 0.0, speed_angular
                    last_move_key_time = now_t
                elif key == ord('d') or key == ord('D'):
                    target_lin, target_ang = 0.0, -speed_angular
                    last_move_key_time = now_t
                elif key == 32:  # SPACE (Rem Darurat)
                    target_lin, target_ang = 0.0, 0.0
                    last_move_key_time = 0.0
                    robot.stop()

                # Watchdog gerak manual: Tahan pergerakan dengan halus (timeout 0.7 detik)
                if now_t - last_move_key_time < 0.7:
                    robot.move(target_lin, target_ang)
                else:
                    target_lin, target_ang = 0.0, 0.0
                    robot.stop()

            # Tampilkan Overlay FPS & Info tambahan
            now = time.time()
            dt = now - last_time
            last_time = now
            fps = 1.0 / dt if dt > 0 else 0
            cv.putText(frame_vis, f"FPS: {fps:.1f}", (frame_vis.shape[1] - 120, 30),
                       cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            cv.imshow(window_name, frame_vis)

    except KeyboardInterrupt:
        pass
    finally:
        robot.stop()
        if cap is not None:
            if hasattr(cap, 'release'): cap.release()
        cv.destroyAllWindows()
        print("[MAIN] Program selesai dan robot dihentikan.")

if __name__ == "__main__":
    main()
