#!/usr/bin/env python3
"""
Script Penguji Laptop Vision -> ESP32-CAM TFT LCD (test_vision_laptop.py)
-------------------------------------------------------------------------
Script ini khusus digunakan untuk:
1. Membuka MJPEG stream dari ESP32-CAM (http://192.168.4.1:81/stream atau http://192.168.4.1/stream).
2. Mendeteksi objek warna RGB (Red, Green, Blue).
3. Mengirimkan hasil deteksi (Warna, Error X, Status Locked) via UDP Socket (Port 8888) ke ESP32-CAM.
4. ESP32-CAM menerima sinyal UDP dan secara otomatis memperbarui informasi di layar TFT LCD!
"""

import cv2 as cv
import numpy as np
import urllib.request
import socket
import json
import time

ESP_IP = "192.168.4.1"
ESP_PORT = 8888

# Socket UDP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Preset HSV Warna RGB
COLOR_PRESETS = {
    "RED": (np.array([0, 100, 100]), np.array([10, 255, 255]), (0, 0, 255)),
    "GREEN": (np.array([35, 100, 100]), np.array([85, 255, 255]), (0, 255, 0)),
    "BLUE": (np.array([100, 100, 100]), np.array([130, 255, 255]), (255, 100, 0))
}

class ESPCamStream:
    """
    HTTP MJPEG Stream Reader presisi dengan penanganan marker JPEG SOI (0xFFD8) & EOI (0xFFD9).
    """
    def __init__(self, urls):
        self.urls = urls if isinstance(urls, list) else [urls]
        self.stream = None
        self.bytes = b''
        self.cap_native = None
        self.active_url = None
        self.connect()

    def connect(self):
        for url in self.urls:
            print(f"[CAM] Mencoba menghubungkan ke stream: {url}...")
            # 1. Coba Native OpenCV VideoCapture dulu
            cap = cv.VideoCapture(url)
            if cap.isOpened():
                ret, test_frame = cap.read()
                if ret and test_frame is not None and test_frame.shape[0] > 0:
                    self.cap_native = cap
                    self.active_url = url
                    print(f"[CAM] ✅ OpenCV VideoCapture Berhasil Aktif: {url}")
                    return
                cap.release()

            # 2. Coba HTTP Stream Buffer Reader
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                stream = urllib.request.urlopen(req, timeout=3)
                self.stream = stream
                self.active_url = url
                print(f"[CAM] ✅ HTTP MJPEG Buffer Reader Berhasil Aktif: {url}")
                return
            except Exception as e:
                print(f"[CAM] Gagal di {url}: {e}")

        print("[ERROR] ❌ Semua URL Stream tidak dapat dibuka. Pastikan Wi-Fi terhubung ke Access Point ESP32!")

    def read(self):
        if self.cap_native is not None and self.cap_native.isOpened():
            ret, frame = self.cap_native.read()
            if ret and frame is not None:
                return True, frame

        if self.stream is not None:
            try:
                while True:
                    self.bytes += self.stream.read(2048)
                    a = self.bytes.find(b'\xff\xd8') # SOI Marker
                    if a != -1:
                        b = self.bytes.find(b'\xff\xd9', a) # EOI Marker HARUS dicari setelah SOI (a)
                        if b != -1:
                            jpg = self.bytes[a:b+2]
                            self.bytes = self.bytes[b+2:]
                            frame = cv.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv.IMREAD_COLOR)
                            if frame is not None and frame.shape[0] > 0:
                                return True, frame
            except Exception as e:
                print(f"[CAM] Stream read error: {e}")
                self.stream = None
                return False, None

        return False, None

    def release(self):
        if self.cap_native is not None:
            self.cap_native.release()
        if self.stream is not None:
            try: self.stream.close()
            except: pass

def main():
    stream_urls = [
        f"http://{ESP_IP}:81/stream",
        f"http://{ESP_IP}/stream",
        f"http://{ESP_IP}:80/stream"
    ]
    
    cam = ESPCamStream(stream_urls)
    active_color = "RED"

    window_name = "Laptop Vision Tester -> ESP32-CAM LCD"
    cv.namedWindow(window_name)

    print("\n==================================================")
    print("      LAPTOP VISION TESTER (ESP32 LCD BRIDGE)    ")
    print("==================================================")
    print("[KEYBOARD SHORTCUTS]")
    print(" 1 : Mode Warna RED (Merah)")
    print(" 2 : Mode Warna GREEN (Hijau)")
    print(" 3 : Mode Warna BLUE (Biru)")
    print(" ESC : Keluar\n")

    last_send = time.time()

    while True:
        ret, frame = cam.read()
        if not ret or frame is None:
            time.sleep(0.03)
            continue

        h, w = frame.shape[:2]
        cx_screen = w // 2

        # HSV Masking
        lower, upper, color_bgr = COLOR_PRESETS[active_color]
        hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
        mask = cv.inRange(hsv, lower, upper)

        contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        
        target_found = False
        error_x = 0.0

        for c in contours:
            if cv.contourArea(c) > 400:
                x, y, bw, bh = cv.boundingRect(c)
                target_cx = x + bw // 2
                target_cy = y + bh // 2
                error_x = float(target_cx - cx_screen)
                target_found = True

                cv.rectangle(frame, (x, y), (x + bw, y + bh), color_bgr, 2)
                cv.circle(frame, (target_cx, target_cy), 5, (0, 0, 255), -1)
                cv.putText(frame, f"{active_color} (ErrX: {error_x:.1f}px)", (x, y - 8),
                           cv.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 2)
                break

        # Kirim hasil ke ESP32-CAM via UDP setiap 100ms
        if time.time() - last_send > 0.1:
            payload = {
                "color": active_color if target_found else "SEARCHING",
                "err_x": round(error_x, 1),
                "locked": target_found
            }
            try:
                msg = json.dumps(payload).encode('utf-8')
                sock.sendto(msg, (ESP_IP, ESP_PORT))
            except Exception:
                pass
            last_send = time.time()

        cv.putText(frame, f"TARGET COLOR: {active_color} (1:RED, 2:GREEN, 3:BLUE)", (15, 30),
                   cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv.putText(frame, f"STATUS LCD: {'LOCKED' if target_found else 'SEARCHING'}", (15, 60),
                   cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0) if target_found else (0, 0, 255), 2)

        cv.imshow(window_name, frame)
        key = cv.waitKey(1) & 0xFF
        if key == 27:
            break
        elif key == ord('1'): active_color = "RED"
        elif key == ord('2'): active_color = "GREEN"
        elif key == ord('3'): active_color = "BLUE"

    cam.release()
    cv.destroyAllWindows()

if __name__ == "__main__":
    main()
