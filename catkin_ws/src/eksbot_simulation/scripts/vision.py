#!/usr/bin/env python3
"""
Eksbot2 Vision Engine Module (vision.py)
----------------------------------------
Modul pengolahan citra OpenCV modular untuk deteksi dan tracking kubus RGB (Red, Green, Blue).
Mendukung perpindahan mode warna dinamis, CSRT Target Tracker, dan kalkulasi galat posisi (error X, error Y).
"""

import cv2 as cv
import numpy as np
import time

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
            }
        }

        self.active_color = "RED"
        self.tracker = None
        self.tracking = False
        self.smooth_cx = None
        self.smooth_cy = None

    def set_color_mode(self, color_name):
        """Mengganti mode target warna aktif ('RED', 'GREEN', 'BLUE')."""
        color_name = color_name.upper()
        if color_name in self.color_presets:
            self.active_color = color_name
            self.reset_tracker()
            print(f"[VISION] Mode warna diubah ke: {self.active_color}")
            return True
        return False

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

    def lock_target_bbox(self, frame, bbox):
        """Lock target berdasarkan Bounding Box (x, y, w, h)."""
        h_f, w_f = frame.shape[:2]
        x, y, w, h = bbox
        x = max(0, min(x, w_f - 1))
        y = max(0, min(y, h_f - 1))
        w = max(10, min(w, w_f - x))
        h = max(10, min(h, h_f - y))

        try:
            self.tracker = self.create_tracker()
            self.tracker.init(frame, (x, y, w, h))
            self.tracking = True
            self.smooth_cx = x + w / 2.0
            self.smooth_cy = y + h / 2.0
            print(f"[VISION] Target Bounding Box Locked: {(x, y, w, h)}")
            return True
        except Exception as e:
            print(f"[ERROR] Gagal menginisialisasi tracker: {e}")
            self.tracking = False
            return False

    def process_frame(self, frame, manual_mode=False):
        """
        Memproses frame gambar.
        Returns:
            processed_frame: frame dengan overlay GUI
            result_data: dict berisi error_x, error_y, norm_x, tracking status, dll.
        """
        if frame is None:
            return None, {}

        frame_h, frame_w = frame.shape[:2]
        frame_cx, frame_cy = frame_w // 2, frame_h // 2

        # Marker pusat kamera
        cv.drawMarker(frame, (frame_cx, frame_cy), (255, 255, 255), cv.MARKER_CROSS, 20, 1)

        result_data = {
            "tracking": False,
            "error_x": 0.0,
            "error_y": 0.0,
            "norm_x": 0.0,
            "target_cx": frame_cx,
            "target_cy": frame_cy,
            "active_color": self.active_color,
            "detected_targets": []
        }

        # Pemrosesan HSV Mask untuk Warna Aktif
        preset = self.color_presets[self.active_color]
        hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
        mask = cv.inRange(hsv, preset["lower1"], preset["upper1"])
        if preset["lower2"] is not None and preset["upper2"] is not None:
            mask2 = cv.inRange(hsv, preset["lower2"], preset["upper2"])
            mask = cv.bitwise_or(mask, mask2)

        # Morphological Operations untuk membersihkan noise
        kernel = np.ones((5, 5), np.uint8)
        mask = cv.morphologyEx(mask, cv.MORPH_OPEN, kernel)

        # 1. TRACKING MODE (CSRT ACTIVE)
        if self.tracking and self.tracker is not None:
            success, bbox = self.tracker.update(frame)
            if success:
                x, y, w, h = [int(v) for v in bbox]
                # Validasi tetap True meskipun kubus berada sangat dekat di tepi layar
                valid = (w > 5 and h > 5 and (x + w) > 5 and (y + h) > 5)

                if valid:
                    raw_cx = max(0, min(x + w / 2.0, float(frame_w)))
                    raw_cy = max(0, min(y + h / 2.0, float(frame_h)))

                    if self.smooth_cx is None: self.smooth_cx = raw_cx
                    if self.smooth_cy is None: self.smooth_cy = raw_cy

                    # Exponential Moving Average (EMA) Smoothing
                    self.smooth_cx = self.alpha * raw_cx + (1.0 - self.alpha) * self.smooth_cx
                    self.smooth_cy = self.alpha * raw_cy + (1.0 - self.alpha) * self.smooth_cy

                    error_x = self.smooth_cx - frame_cx
                    error_y = self.smooth_cy - frame_cy

                    # Deadzone Application
                    if abs(error_x) < self.deadzone:
                        error_x_ctrl = 0.0
                    else:
                        error_x_ctrl = error_x

                    norm_x = np.clip(error_x_ctrl / (frame_w / 2.0), -1.0, 1.0)

                    result_data.update({
                        "tracking": True,
                        "error_x": error_x_ctrl,
                        "error_y": error_y,
                        "norm_x": norm_x,
                        "target_cx": self.smooth_cx,
                        "target_cy": self.smooth_cy,
                        "target_area": w * h,
                        "bbox": (x, y, w, h)
                    })

                    # GUI Visual Overlays
                    color = preset["color_bgr"]
                    cv.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    cv.circle(frame, (int(self.smooth_cx), int(self.smooth_cy)), 6, (0, 0, 255), -1)
                    cv.line(frame, (frame_cx, frame_cy), (int(self.smooth_cx), int(self.smooth_cy)), (0, 255, 0), 2)

                    cv.putText(frame, f"MODE: VISION AUTO NAV ({self.active_color})", (20, 35),
                               cv.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
                    cv.putText(frame, f"ErrX: {error_x_ctrl:.1f} | NormX: {norm_x:.2f}", (20, 65),
                               cv.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
                else:
                    self.reset_tracker()
            else:
                cv.putText(frame, "TARGET LOST! (Tekan 'R' untuk Reset)", (20, 35),
                           cv.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)
                self.reset_tracker()

        # 2. DETEKSI KONTOUR (UNLOCKED)
        else:
            contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
            detected_targets = []
            target_id = 1

            for c in contours:
                area = cv.contourArea(c)
                if area >= self.min_area:
                    x, y, w, h = cv.boundingRect(c)
                    M = cv.moments(c)
                    cx_t = int(M["m10"] / M["m00"]) if M["m00"] != 0 else x + w // 2
                    cy_t = int(M["m01"] / M["m00"]) if M["m00"] != 0 else y + h // 2

                    target_info = {
                        "id": target_id,
                        "bbox": (x, y, w, h),
                        "center": (cx_t, cy_t),
                        "area": area
                    }
                    detected_targets.append(target_info)

                    # Draw Bounding Box & Label
                    color = preset["color_bgr"]
                    cv.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    cv.circle(frame, (cx_t, cy_t), 4, (0, 255, 255), -1)
                    cv.putText(frame, f"Kubus #{target_id} [{self.active_color}]", (x, max(20, y - 8)),
                               cv.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    target_id += 1

            result_data["detected_targets"] = detected_targets

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
