#!/usr/bin/env python3
"""
Eksbot2 Vision Engine Module (vision.py)
----------------------------------------
Modul pengolahan citra OpenCV modular untuk deteksi dan tracking kubus RGB (Red, Green, Blue).

Alur (mirip "lock-on" rudal/drone):
  1. FILTER WARNA : HSV mask + morphology + contour -> kandidat target.
  2. LOCK         : operator memilih kandidat (klik) -> CSRT Tracker diinisialisasi pada bbox.
  3. TRACK        : CSRT memperbarui bbox tiap frame (tahan terhadap perubahan warna/cahaya
                    ringan karena memakai fitur tampilan, bukan hanya mask warna).
  4. ERROR        : galat posisi target terhadap TITIK BIDIK (aim point / crosshair), bukan
                    sekadar tengah frame. Titik bidik bisa digeser (boresight kamera).

process_frame(draw=False) tidak menggambar apa pun pada frame sehingga HUD dapat dirender
oleh antarmuka web; draw=True mempertahankan overlay OpenCV lama untuk mode jendela (--gui).
"""

import time
import threading
import urllib.request

import cv2 as cv
import numpy as np

try:
    import rospy
    from sensor_msgs.msg import Image
    from cv_bridge import CvBridge, CvBridgeError
    HAS_ROS = True
except ImportError:
    HAS_ROS = False


# ======================================================================
# Sumber Kamera (Kamera ESP32-CAM, ROS Gazebo, atau Webcam)
# ======================================================================
class ROSImageSub:
    name = "ROS /camera/image_raw"

    def __init__(self, topic="/camera/image_raw"):
        self.name = f"ROS {topic}"
        self.bridge = CvBridge()
        self.frame = None
        self._seq = 0
        self._last_seq = 0
        self._stamp = 0.0
        self._lock = threading.Lock()
        self.sub = rospy.Subscriber(topic, Image, self._callback, queue_size=1)

    def _callback(self, data):
        try:
            frame = self.bridge.imgmsg_to_cv2(data, "bgr8")
        except CvBridgeError:
            return
        with self._lock:
            self.frame = frame
            self._seq += 1
            self._stamp = time.time()

    @property
    def connected(self):
        return self.frame is not None and (time.time() - self._stamp) < 2.0

    def read(self):
        with self._lock:
            if self.frame is None or self._seq == self._last_seq:
                return False, None
            self._last_seq = self._seq
            return True, self.frame.copy()

    def release(self):
        try:
            self.sub.unregister()
        except Exception:
            pass


class WebcamSource:
    def __init__(self, index=0):
        self.name = f"Webcam {index}"
        self.cap = cv.VideoCapture(index)
        self._ok_time = 0.0

    @property
    def connected(self):
        return self.cap.isOpened() and (time.time() - self._ok_time) < 2.0

    def read(self):
        ok, frame = self.cap.read()
        if ok:
            self._ok_time = time.time()
            return True, frame
        return False, None

    def release(self):
        self.cap.release()


class ESPCamReader:
    """
    Pembaca stream MJPEG ESP32-CAM berbasis thread latar belakang.
    - Thread terus menguras socket dan HANYA menyimpan frame terbaru (tidak ada antrean basi).
    - Reconnect otomatis jika stream putus/timeout.
    - read() tidak memblokir: (False, None) bila belum ada frame baru.
    """

    def __init__(self, url, timeout=3.0, retry_delay=1.5):
        self.url = url
        self.name = f"ESP32-CAM {url}"
        self.timeout = timeout
        self.retry_delay = retry_delay
        self.stream = None
        self._opened = False
        self._running = True
        self._lock = threading.Lock()
        self._latest_jpg = None
        self._seq = 0
        self._last_seq = 0
        self._stamp = 0.0
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    @property
    def connected(self):
        return self._opened and (time.time() - self._stamp) < 2.0

    def _connect(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            self.stream = urllib.request.urlopen(req, timeout=self.timeout)
            self._opened = True
            print(f"[CAM_READER] Terhubung ke stream ESP32-CAM: {self.url}")
        except Exception as e:
            print(f"[CAM_READER] Gagal membuka stream ({self.url}): {e}")
            self.stream = None
            self._opened = False

    def _close_stream(self):
        if self.stream is not None:
            try:
                self.stream.close()
            except Exception:
                pass
        self.stream = None
        self._opened = False

    def _reader_loop(self):
        buf = bytearray()
        while self._running:
            if self.stream is None:
                self._connect()
                buf = bytearray()
                if self.stream is None:
                    time.sleep(self.retry_delay)
                continue
            try:
                chunk = self.stream.read1(4096) if hasattr(self.stream, 'read1') else self.stream.read(1024)
                if not chunk:
                    raise EOFError("Stream ditutup oleh ESP32-CAM")
                buf += chunk
                end = buf.rfind(b'\xff\xd9')
                if end != -1:
                    start = buf.rfind(b'\xff\xd8', 0, end)
                    if start != -1:
                        with self._lock:
                            self._latest_jpg = bytes(buf[start:end + 2])
                            self._seq += 1
                            self._stamp = time.time()
                    del buf[:end + 2]
                if len(buf) > 512 * 1024:
                    buf = bytearray()
            except Exception as e:
                if self._running:
                    print(f"[CAM_READER] Stream terputus ({e}), mencoba reconnect...")
                self._close_stream()

    def read(self):
        with self._lock:
            if self._latest_jpg is None or self._seq == self._last_seq:
                return False, None
            jpg = self._latest_jpg
            self._last_seq = self._seq
        frame = cv.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv.IMREAD_COLOR)
        if frame is None:
            return False, None
        return True, frame

    def release(self):
        self._running = False
        self._close_stream()


def open_source(kind, esp_ip="192.168.4.10", esp_url=None, ros_topic="/camera/image_raw", webcam_index=0):
    """Factory pembuat objek sumber kamera: kind in {'esp', 'sim', 'webcam'}."""
    if kind == "esp":
        return ESPCamReader(esp_url or f"http://{esp_ip}/stream")
    if kind == "sim":
        if not HAS_ROS:
            raise RuntimeError("Mode sim membutuhkan ROS (rospy/cv_bridge) tetapi tidak ditemukan.")
        return ROSImageSub(ros_topic)
    if kind == "webcam":
        return WebcamSource(webcam_index)
    raise ValueError(f"Sumber kamera tidak dikenal: {kind}")


# ======================================================================
# Vision Engine (Filter Warna HSV + Kontur + CSRT Tracker)
# ======================================================================
class VisionEngine:
    def __init__(self, deadzone=15, alpha=0.35, min_area=150):
        self.deadzone = deadzone
        self.alpha = alpha
        self.min_area = min_area

        # Preset HSV Color Ranges (R, G, B) - Toleran terhadap bayangan & pencahayaan arena
        self.color_presets = {
            "RED": {
                "lower1": np.array([0, 50, 50]),
                "upper1": np.array([10, 255, 255]),
                "lower2": np.array([165, 50, 50]),
                "upper2": np.array([180, 255, 255]),
                "color_bgr": (0, 0, 255)
            },
            "GREEN": {
                "lower1": np.array([35, 45, 45]),
                "upper1": np.array([85, 255, 255]),
                "lower2": None,
                "upper2": None,
                "color_bgr": (0, 255, 0)
            },
            "BLUE": {
                "lower1": np.array([95, 50, 50]),
                "upper1": np.array([130, 255, 255]),
                "lower2": None,
                "upper2": None,
                "color_bgr": (255, 100, 0)
            },
            "YELLOW": {
                "lower1": np.array([20, 70, 70]),
                "upper1": np.array([35, 255, 255]),
                "lower2": None,
                "upper2": None,
                "color_bgr": (0, 230, 255)
            }
        }

        self.default_presets = {k: {
            "lower1": v["lower1"].copy() if v["lower1"] is not None else None,
            "upper1": v["upper1"].copy() if v["upper1"] is not None else None,
            "lower2": v["lower2"].copy() if v["lower2"] is not None else None,
            "upper2": v["upper2"].copy() if v["upper2"] is not None else None,
            "color_bgr": v["color_bgr"]
        } for k, v in self.color_presets.items()}

        self.active_color = "RED"
        self.tracker = None
        self.tracking = False
        self.smooth_cx = None
        self.smooth_cy = None
        self.last_targets = []     # Kandidat kontur frame terakhir (untuk lock via klik)
        self._kernel = np.ones((5, 5), np.uint8)

        # ------------------------------------------------------------------
        # Estimasi Kecepatan & Arah Gerak Objek (Velocity & Trajectory Prediction)
        # ------------------------------------------------------------------
        self.last_cx = None
        self.last_cy = None
        self.last_t = None
        self.vel_x = 0.0          # pixel / second (kecepatan horizontal)
        self.vel_y = 0.0          # pixel / second (kecepatan vertikal)
        self.speed = 0.0          # total pixel / second
        self.pred_cx = None       # prediksi posisi X (misal 0.5 detik ke depan)
        self.pred_cy = None       # prediksi posisi Y (misal 0.5 detik ke depan)
        self.heading_deg = 0.0    # arah vektor gerak objek (derajat: 0=kanan, 90=bawah, 180=kiri, -90=atas)
        self.move_dir = "STILL"   # "LEFT", "RIGHT", "TOWARDS", "AWAY", "STILL"

    # ------------------------------------------------------------------
    # Konfigurasi
    # ------------------------------------------------------------------
    def set_color_mode(self, color_name):
        """Mengganti mode target warna aktif ('RED', 'GREEN', 'BLUE', 'YELLOW')."""
        color_name = color_name.upper()
        if color_name in self.color_presets:
            self.active_color = color_name
            self.reset_tracker()
            self.last_targets = []
            print(f"[VISION] Mode warna diubah ke: {self.active_color}")
            return True
        return False

    def get_hsv_ranges(self):
        """Mengembalikan dictionary range HSV seluruh preset (untuk Web HMI tuner)."""
        res = {}
        for c, p in self.color_presets.items():
            l1, u1 = p["lower1"], p["upper1"]
            res[c] = {
                "h_min": int(l1[0]), "s_min": int(l1[1]), "v_min": int(l1[2]),
                "h_max": int(u1[0]), "s_max": int(u1[1]), "v_max": int(u1[2])
            }
        return {"active": self.active_color, "ranges": res}

    def set_hsv_range(self, color_name, h_min, h_max, s_min, s_max, v_min, v_max):
        """Mengatur batas HSV warna aktif secara dinamis."""
        color_name = color_name.upper()
        if color_name not in self.color_presets:
            return False
        h_min = max(0, min(179, int(h_min)))
        h_max = max(0, min(179, int(h_max)))
        s_min = max(0, min(255, int(s_min)))
        s_max = max(0, min(255, int(s_max)))
        v_min = max(0, min(255, int(v_min)))
        v_max = max(0, min(255, int(v_max)))

        p = self.color_presets[color_name]
        p["lower1"] = np.array([h_min, s_min, v_min])
        p["upper1"] = np.array([h_max, s_max, v_max])
        return True

    def reset_hsv_presets(self):
        """Mereset seluruh preset warna kembali ke standar."""
        for k, v in self.default_presets.items():
            self.color_presets[k] = {
                "lower1": v["lower1"].copy() if v["lower1"] is not None else None,
                "upper1": v["upper1"].copy() if v["upper1"] is not None else None,
                "lower2": v["lower2"].copy() if v["lower2"] is not None else None,
                "upper2": v["upper2"].copy() if v["upper2"] is not None else None,
                "color_bgr": v["color_bgr"]
            }
        return True

    def create_tracker(self):
        """Membuat instance CSRT Tracker."""
        if hasattr(cv, "TrackerCSRT_create"):
            return cv.TrackerCSRT_create()
        if hasattr(cv, "legacy") and hasattr(cv.legacy, "TrackerCSRT_create"):
            return cv.legacy.TrackerCSRT_create()
        raise RuntimeError("CSRT Tracker tidak tersedia pada instalasi OpenCV ini.")

    def reset_tracker(self):
        """Mereset tracker kembali ke deteksi multi-target kontur."""
        self.tracker = None
        self.tracking = False
        self.smooth_cx = None
        self.smooth_cy = None
        self.last_cx = None
        self.last_cy = None
        self.last_t = None
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.speed = 0.0
        self.pred_cx = None
        self.pred_cy = None
        self.heading_deg = 0.0
        self.move_dir = "STILL"

    # ------------------------------------------------------------------
    # Lock target
    # ------------------------------------------------------------------
    def lock_target_bbox(self, frame, bbox):
        """Lock target berdasarkan Bounding Box (x, y, w, h)."""
        h_f, w_f = frame.shape[:2]
        x, y, w, h = [int(v) for v in bbox]
        x = max(0, min(x, w_f - 1))
        y = max(0, min(y, h_f - 1))
        w = max(10, min(w, w_f - x))
        h = max(10, min(h, h_f - y))

        try:
            self.tracker = self.create_tracker()
            self.tracker.init(frame, (x, y, w, h))
            self.tracking = True
            cx = x + w / 2.0
            cy = y + h / 2.0
            self.smooth_cx = cx
            self.smooth_cy = cy
            self.last_cx = cx
            self.last_cy = cy
            self.last_t = time.time()
            self.vel_x = 0.0
            self.vel_y = 0.0
            self.speed = 0.0
            self.pred_cx = cx
            self.pred_cy = cy
            self.move_dir = "STILL"
            print(f"[VISION] Target Bounding Box Locked: {(x, y, w, h)}")
            return True
        except Exception as e:
            print(f"[ERROR] Gagal menginisialisasi tracker: {e}")
            self.reset_tracker()
            return False

    def lock_at_point(self, frame, px, py, roi=50):
        """
        Lock target pada titik (px, py) piksel.
        1. Snap ke kontur warna yang mencakup klik (toleransi 15px).
        2. Jika klik sedikit meleset, snap ke kontur terdekat dalam radius 45px.
        3. Jika tidak ada kontur warna sama sekali, buat ROI ukuran kubus proporsional (50x50).
        """
        # 1. Hit test langsung dengan toleransi 15px
        for t in self.last_targets:
            x, y, w, h = t["bbox"]
            if (x - 15) <= px <= (x + w + 15) and (y - 15) <= py <= (y + h + 15):
                print(f"[VISION] Lock snap ke kontur Kubus #{t['id']} {t['bbox']}")
                return self.lock_target_bbox(frame, t["bbox"])

        # 2. Cari kontur terdekat dalam radius 45px
        best_t = None
        best_dist = 45.0
        for t in self.last_targets:
            cx, cy = t["center"]
            dist = float(np.hypot(px - cx, py - cy))
            if dist < best_dist:
                best_dist = dist
                best_t = t

        if best_t is not None:
            print(f"[VISION] Lock snap radius ke Kubus #{best_t['id']} {best_t['bbox']}")
            return self.lock_target_bbox(frame, best_t["bbox"])

        # 3. Fallback jika tidak ada kontur: buat ROI ukuran kubus (50x50 bukan 100x100)
        h_f, w_f = frame.shape[:2]
        roi_w = min(roi, w_f // 4)
        roi_h = min(roi, h_f // 4)
        return self.lock_target_bbox(frame, (px - roi_w // 2, py - roi_h // 2, roi_w, roi_h))

    # ------------------------------------------------------------------
    # Pemrosesan frame & Fusi Simultan
    # ------------------------------------------------------------------
    def _color_mask(self, frame):
        """
        Fusi Simultan Matriks:
        1. Mask warna HSV (lower1, upper1, lower2, upper2)
        2. Deteksi tepi fisik (Canny) di-invert untuk memotong celah antar 2 balok yang menempel
        3. Bitwise AND langsung antar layer mask dan not-edges
        4. Pembersihan noise dengan morphology open
        """
        preset = self.color_presets[self.active_color]
        hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
        mask = cv.inRange(hsv, preset["lower1"], preset["upper1"])
        if preset["lower2"] is not None and preset["upper2"] is not None:
            mask = cv.bitwise_or(mask, cv.inRange(hsv, preset["lower2"], preset["upper2"]))

        # 2. Deteksi celah / tepi fisik HANYA di area warna (Masked Canny)
        # Ini mencegah garis tepi arena/lantai memotong objek dan jauh lebih hemat CPU
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        masked_gray = cv.bitwise_and(gray, gray, mask=mask)
        blurred_gray = cv.GaussianBlur(masked_gray, (3, 3), 0)
        edges = cv.Canny(blurred_gray, 40, 120)

        # Tebalkan sedikit garis pemotong celah
        edge_kernel = np.ones((3, 3), np.uint8)
        edges_dilated = cv.dilate(edges, edge_kernel, iterations=1)

        # 3. Operasi Bitwise Simultan: Potong garis celah fisik dari mask warna
        split_mask = cv.bitwise_and(mask, cv.bitwise_not(edges_dilated))

        # 4. Morphology open untuk membuang noise kecil dan memisahkan jembatan tipis
        cleaned_mask = cv.morphologyEx(split_mask, cv.MORPH_OPEN, self._kernel)
        return cleaned_mask

    def process_frame(self, frame, manual_mode=False, aim=None, draw=True):
        """
        Memproses frame gambar.
        Param:
            aim  : (x, y) titik bidik dalam piksel; default tengah frame.
            draw : True -> gambar overlay OpenCV pada frame; False -> frame tidak diubah.
        Returns:
            frame (beranotasi bila draw=True), result_data (dict telemetri vision)
        """
        if frame is None:
            return None, {}

        frame_h, frame_w = frame.shape[:2]
        aim_x, aim_y = (frame_w // 2, frame_h // 2) if aim is None else (int(aim[0]), int(aim[1]))
        preset = self.color_presets[self.active_color]
        color_bgr = preset["color_bgr"]

        result_data = {
            "tracking": False,
            "lost": False,
            "error_x": 0.0,
            "error_y": 0.0,
            "norm_x": 0.0,
            "target_cx": aim_x,
            "target_cy": aim_y,
            "target_area": 0,
            "bbox": None,
            "active_color": self.active_color,
            "frame_w": frame_w,
            "frame_h": frame_h,
            "aim": (aim_x, aim_y),
            "detected_targets": []
        }

        if draw:
            cv.drawMarker(frame, (aim_x, aim_y), (255, 255, 255), cv.MARKER_CROSS, 20, 1)

        # 1. TRACKING MODE (CSRT ACTIVE) - mask warna tidak diperlukan, dilewati agar hemat CPU
        if self.tracking and self.tracker is not None:
            success, bbox = self.tracker.update(frame)
            if success:
                x, y, w, h = [int(v) for v in bbox]
                valid = (w > 5 and h > 5 and (x + w) > 5 and (y + h) > 5)

                if valid:
                    raw_cx = max(0, min(x + w / 2.0, float(frame_w)))
                    raw_cy = max(0, min(y + h / 2.0, float(frame_h)))

                    if self.smooth_cx is None:
                        self.smooth_cx = raw_cx
                    if self.smooth_cy is None:
                        self.smooth_cy = raw_cy

                    # Exponential Moving Average (EMA) Smoothing
                    self.smooth_cx = self.alpha * raw_cx + (1.0 - self.alpha) * self.smooth_cx
                    self.smooth_cy = self.alpha * raw_cy + (1.0 - self.alpha) * self.smooth_cy

                    # --- ESTIMASI KECEPATAN & ARAH GERAK OBJEK (VELOCITY & TRAJECTORY) ---
                    now = time.time()
                    if self.last_cx is not None and self.last_t is not None:
                        dt = max(1e-3, now - self.last_t)
                        # Instantaneous velocity (px/sec)
                        inst_vx = (self.smooth_cx - self.last_cx) / dt
                        inst_vy = (self.smooth_cy - self.last_cy) / dt
                        # Filter dengan EMA agar stabil terhadap jitter kamera
                        self.vel_x = 0.3 * inst_vx + 0.7 * self.vel_x
                        self.vel_y = 0.3 * inst_vy + 0.7 * self.vel_y
                    else:
                        self.vel_x = 0.0
                        self.vel_y = 0.0

                    self.last_cx = self.smooth_cx
                    self.last_cy = self.smooth_cy
                    self.last_t = now
                    self.speed = float(np.hypot(self.vel_x, self.vel_y))

                    # Prediksi posisi objek 0.4 detik ke depan
                    lookahead = 0.4
                    self.pred_cx = float(np.clip(self.smooth_cx + self.vel_x * lookahead, 0, frame_w))
                    self.pred_cy = float(np.clip(self.smooth_cy + self.vel_y * lookahead, 0, frame_h))

                    # Tentukan arah gerak utama (move_dir) & sudut hadap vektor (heading_deg)
                    if self.speed > 18.0: # threshold gerak nyata (> 18 px/s)
                        self.heading_deg = float(np.degrees(np.arctan2(self.vel_y, self.vel_x)))
                        if abs(self.vel_x) > abs(self.vel_y) * 1.2:
                            self.move_dir = "RIGHT" if self.vel_x > 0 else "LEFT"
                        elif abs(self.vel_y) > abs(self.vel_x) * 1.2:
                            self.move_dir = "TOWARDS" if self.vel_y > 0 else "AWAY"
                        else:
                            horiz = "RIGHT" if self.vel_x > 0 else "LEFT"
                            vert = "TOWARDS" if self.vel_y > 0 else "AWAY"
                            self.move_dir = f"{vert}-{horiz}"
                    else:
                        self.move_dir = "STILL"

                    error_x = self.smooth_cx - aim_x
                    error_y = self.smooth_cy - aim_y
                    error_x_ctrl = 0.0 if abs(error_x) < self.deadzone else error_x
                    norm_x = float(np.clip(error_x_ctrl / (frame_w / 2.0), -1.0, 1.0))

                    result_data.update({
                        "tracking": True,
                        "error_x": error_x_ctrl,
                        "error_y": error_y,
                        "norm_x": norm_x,
                        "target_cx": self.smooth_cx,
                        "target_cy": self.smooth_cy,
                        "target_area": w * h,
                        "bbox": (x, y, w, h),
                        "vel_x": round(self.vel_x, 1),
                        "vel_y": round(self.vel_y, 1),
                        "speed": round(self.speed, 1),
                        "heading_deg": round(self.heading_deg, 1),
                        "move_dir": self.move_dir,
                        "pred_target": [round(self.pred_cx, 1), round(self.pred_cy, 1)],
                    })

                    if draw:
                        cv.rectangle(frame, (x, y), (x + w, y + h), color_bgr, 2)
                        cv.circle(frame, (int(self.smooth_cx), int(self.smooth_cy)), 6, (0, 0, 255), -1)
                        cv.line(frame, (aim_x, aim_y), (int(self.smooth_cx), int(self.smooth_cy)), (0, 255, 0), 2)
                        # Gambar garis vektor prediksi arah gerak objek (kuning)
                        if self.speed > 18.0:
                            cv.arrowedLine(frame, (int(self.smooth_cx), int(self.smooth_cy)),
                                           (int(self.pred_cx), int(self.pred_cy)), (0, 255, 255), 2, tipLength=0.25)
                        cv.putText(frame, f"MODE: VISION AUTO NAV ({self.active_color})", (20, 35),
                                   cv.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
                        cv.putText(frame, f"ErrX: {error_x_ctrl:.1f} | Speed: {self.speed:.0f}px/s | Dir: {self.move_dir}", (20, 65),
                                   cv.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
                else:
                    self.reset_tracker()
                    result_data["lost"] = True
            else:
                result_data["lost"] = True
                if draw:
                    cv.putText(frame, "TARGET LOST! (Tekan 'R' untuk Reset)", (20, 35),
                               cv.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)
                self.reset_tracker()

        # 2. DETEKSI KONTOUR (UNLOCKED)
        else:
            mask = self._color_mask(frame)
            contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
            detected_targets = []

            for c in contours:
                area = cv.contourArea(c)
                if area < self.min_area:
                    continue
                x, y, w, h = cv.boundingRect(c)
                M = cv.moments(c)
                cx_t = int(M["m10"] / M["m00"]) if M["m00"] != 0 else x + w // 2
                cy_t = int(M["m01"] / M["m00"]) if M["m00"] != 0 else y + h // 2
                detected_targets.append({
                    "id": len(detected_targets) + 1,
                    "bbox": (x, y, w, h),
                    "center": (cx_t, cy_t),
                    "area": area
                })

            # Urutkan: Balok paling dekat (posisi vertikal / dasar kotak paling bawah di POV)
            # didahulukan. Jika jarak mirip, pilih area terbesar.
            detected_targets.sort(key=lambda t: (t["bbox"][1] + t["bbox"][3], t["area"]), reverse=True)
            detected_targets = detected_targets[:8]
            for i, t in enumerate(detected_targets):
                t["id"] = i + 1

            self.last_targets = detected_targets
            result_data["detected_targets"] = detected_targets

            if draw:
                for t in detected_targets:
                    x, y, w, h = t["bbox"]
                    cx_t, cy_t = t["center"]
                    cv.rectangle(frame, (x, y), (x + w, y + h), color_bgr, 2)
                    cv.circle(frame, (cx_t, cy_t), 4, (0, 255, 255), -1)
                    cv.putText(frame, f"Kubus #{t['id']} [{self.active_color}]", (x, max(20, y - 8)),
                               cv.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 2)
                if manual_mode:
                    cv.putText(frame, f"MODE: MANUAL - Found ({len(detected_targets)})", (20, 35),
                               cv.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
                    cv.putText(frame, f"WARNA TERPILIH: {self.active_color} (Tekan 1:Red, 2:Green, 3:Blue, 'M':Auto)", (20, 65),
                               cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                else:
                    cv.putText(frame, f"MODE: AUDIT VISION [{self.active_color}] - Found ({len(detected_targets)})", (20, 35),
                               cv.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 0), 2)
                    cv.putText(frame, "Klik Target atau Tekan '1':Red '2':Green '3':Blue 'M':Manual", (20, 65),
                               cv.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        return frame, result_data
