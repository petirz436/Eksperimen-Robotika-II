#!/usr/bin/env python3
"""
Test Manual Control Robot via Direct Wi-Fi UDP (Tanpa Kamera)
==============================================================
Script ini dijalankan di laptop untuk menguji pergerakan robot (WSAD + Servo)
langsung terhubung ke Wi-Fi Access Point ESP32 Sistem Kontrol.

Petunjuk Keyboard:
  W / S    : Maju / Mundur
  A / D    : Belok Kiri / Belok Kanan
  SPACE    : Stop (Rem Darurat)
  J / K    : Jepit (Gripper Close 90°) / Buka (Gripper Open 0°)
  U / I    : Angkat Lift (Lift UP 90°) / Turunkan Lift (Lift DOWN 0°)
  ESC      : Keluar dari Program
"""

import socket
import json
import time
import cv2 as cv
import numpy as np

ESP_IP = "192.168.4.1"
ESP_PORT = 8888

def send_udp(sock, payload_dict):
    try:
        msg_bytes = json.dumps(payload_dict).encode('utf-8')
        sock.sendto(msg_bytes, (ESP_IP, ESP_PORT))
    except Exception as e:
        print(f"[ERROR SEND UDP]: {e}")

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    speed_linear = 0.30
    speed_angular = 1.2

    curr_lin = 0.0
    curr_ang = 0.0
    curr_grip = 0   # 0: OPEN, 90: CLOSE
    curr_lift = 0   # 0: DOWN, 90: UP

    last_key_time = 0.0

    print("==================================================")
    print("   TEST DIRECT WI-FI MANUAL CONTROL (NO CAMERA)   ")
    print("==================================================")
    print(f"Target ESP32 IP: {ESP_IP}:{ESP_PORT}")
    print("\n[PETUNJUK KONTROL]")
    print(" W / S    : Maju / Mundur")
    print(" A / D    : Belok Kiri / Kanan")
    print(" SPACE    : Stop")
    print(" J / K    : Grip CLOSE / OPEN")
    print(" U / I    : Lift UP / DOWN")
    print(" ESC      : Keluar\n")

    # Buat GUI Window Sederhana untuk Menangkap Keyboard
    canvas = np.zeros((350, 600, 3), dtype=np.uint8)
    cv.namedWindow("Robot Control Test Panel", cv.WINDOW_NORMAL)

    try:
        while True:
            canvas.fill(25)  # Background Gelap Modern

            # Header Text
            cv.putText(canvas, "ROBOT MANUAL CONTROL TEST (NO CAM)", (30, 45),
                       cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv.putText(canvas, f"Connected IP: {ESP_IP}:{ESP_PORT}", (30, 75),
                       cv.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            # Telemetri Status Kecepatan & Servo
            cv.putText(canvas, f"Linear Velocity  : {curr_lin:+.2f} m/s", (30, 130),
                       cv.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0) if curr_lin != 0 else (255, 255, 255), 2)
            cv.putText(canvas, f"Angular Velocity : {curr_ang:+.2f} rad/s", (30, 170),
                       cv.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0) if curr_ang != 0 else (255, 255, 255), 2)
            cv.putText(canvas, f"Gripper Status   : {'CLOSED (90 deg)' if curr_grip > 45 else 'OPEN (0 deg)'}", (30, 210),
                       cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
            cv.putText(canvas, f"Lift Status      : {'UP (90 deg)' if curr_lift > 45 else 'DOWN (0 deg)'}", (30, 250),
                       cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

            # Info Key Controls
            cv.putText(canvas, "Tekan WSAD, J/K, U/I di jendela ini | ESC untuk keluar", (30, 310),
                       cv.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)

            cv.imshow("Robot Control Test Panel", canvas)

            key = cv.waitKey(20) & 0xFF
            now = time.time()

            if key == 27:  # ESC
                break
            elif key == ord('w') or key == ord('W'):
                curr_lin, curr_ang = speed_linear, 0.0
                last_key_time = now
            elif key == ord('s') or key == ord('S'):
                curr_lin, curr_ang = -speed_linear, 0.0
                last_key_time = now
            elif key == ord('a') or key == ord('A'):
                curr_lin, curr_ang = 0.0, speed_angular
                last_key_time = now
            elif key == ord('d') or key == ord('D'):
                curr_lin, curr_ang = 0.0, -speed_angular
                last_key_time = now
            elif key == 32:  # SPACE
                curr_lin, curr_ang = 0.0, 0.0
                last_key_time = 0.0
            elif key == ord('j') or key == ord('J'):
                curr_grip = 90  # CLOSE
            elif key == ord('k') or key == ord('K'):
                curr_grip = 0   # OPEN
            elif key == ord('u') or key == ord('U'):
                curr_lift = 90  # UP
            elif key == ord('i') or key == ord('I'):
                curr_lift = 0   # DOWN

            # Watchdog Timeout: Jika tombol WSAD dilepas selama > 0.5s, hentikan robot
            if now - last_key_time > 0.5:
                curr_lin, curr_ang = 0.0, 0.0

            # Kirim Paket UDP ke ESP32
            payload = {
                "cmd": "move",
                "lin": round(curr_lin, 2),
                "ang": round(curr_ang, 2),
                "grip": curr_grip,
                "lift": curr_lift
            }
            send_udp(sock, payload)

    except KeyboardInterrupt:
        pass
    finally:
        # Kirim sinyal stop akhir
        send_udp(sock, {"cmd": "move", "lin": 0.0, "ang": 0.0, "grip": curr_grip, "lift": curr_lift})
        sock.close()
        cv.destroyAllWindows()
        print("\n[INFO] Program dihentikan.")

if __name__ == "__main__":
    main()
