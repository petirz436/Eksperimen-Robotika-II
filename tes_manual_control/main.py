#!/usr/bin/env python3
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

    print(f"Target ESP32 IP: {ESP_IP}:{ESP_PORT}")
    print("\n[PETUNJUK KONTROL]")
    print(" W / S    : Maju / Mundur")
    print(" A / D    : Belok Kiri / Kanan")
    print(" SPACE    : Stop")
    print(" ESC      : Keluar\n")

    # Buat GUI Window Sederhana untuk Menangkap Keyboard
    canvas = np.zeros((350, 600, 3), dtype=np.uint8)
    cv.namedWindow("Robot Control Test Panel", cv.WINDOW_NORMAL)

    try:
        while True:
            canvas.fill(25)  # Background Gelap Modern

            # Header Text
            cv.putText(canvas, f"Connected IP: {ESP_IP}:{ESP_PORT}", (30, 75),
                       cv.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            # Telemetri Status Kecepatan & Servo
            cv.putText(canvas, f"Linear Velocity  : {curr_lin:+.2f} m/s", (30, 130),
                       cv.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0) if curr_lin != 0 else (255, 255, 255), 2)
            cv.putText(canvas, f"Angular Velocity : {curr_ang:+.2f} rad/s", (30, 170),
                       cv.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0) if curr_ang != 0 else (255, 255, 255), 2)

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
