#!/usr/bin/env python3
import sys
import os
import cv2 as cv
import numpy as np
import time
import urllib.request

# ROS Integration (Import optional jika dijalankan tanpa ROS)
try:
    import rospy
    from sensor_msgs.msg import Image
    from geometry_msgs.msg import Twist, Point
    from std_msgs.msg import String
    from cv_bridge import CvBridge, CvBridgeError
    HAS_ROS = True
except ImportError:
    HAS_ROS = False

# ============================================================
# CONFIGURATION
# ============================================================
USE_ESP_CAM = False                             # Set True untuk stream ESP32-CAM, False untuk Webcam/ROS Topic
ESP_CAM_URL = "http://172.20.10.3/stream" # URL stream ESP32-CAM fisik
CAMERA_INDEX = 0                               # Index webcam lokal jika USE_ESP_CAM = False & ROS = False
DEFAULT_ROI_W = 100
DEFAULT_ROI_H = 100
ALPHA = 0.35            # Factor smoothing EMA
DEADZONE = 20           # Pixel deadzone error
MIN_CONTOUR_AREA = 500  # Filter kontur minimal untuk deteksi target

# HSV Color Mask (Default: Merah / Red Cube)
HSV_LOWER = np.array([0, 100, 100])
HSV_UPPER = np.array([10, 255, 255])
# Untuk Merah rentang kedua (wrap 180)
HSV_LOWER2 = np.array([170, 100, 100])
HSV_UPPER2 = np.array([180, 255, 255])


# ============================================================
# ROS IMAGE SUBSCRIBER & ROS BRIDGE
# ============================================================
class ROSImageSubscriber:
    def __init__(self, topic="/camera/image_raw"):
        self.bridge = CvBridge()
        self.current_frame = None
        self.sub = rospy.Subscriber(topic, Image, self.callback)

    def callback(self, data):
        try:
            self.current_frame = self.bridge.imgmsg_to_cv2(data, "bgr8")
        except CvBridgeError as e:
            rospy.logerr(f"CvBridge Error: {e}")

    def read(self):
        if self.current_frame is not None:
            return True, self.current_frame.copy()
        return False, None


# ============================================================
# ESP32-CAM STREAM HANDLER
# ============================================================
class ESPCamStream:
    """
    Class pembaca stream MJPEG HTTP dari ESP32-CAM.
    Kompatibel dengan antarmuka cv.VideoCapture (.read(), .isOpened(), .release()).
    """
    def __init__(self, url):
        self.url = url
        self.stream = None
        self.bytes = b''
        self._is_opened = False
        self.connect()

    def connect(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            self.stream = urllib.request.urlopen(req, timeout=5)
            self._is_opened = True
            print(f"[ESP-CAM] Berhasil terhubung ke stream: {self.url}")
        except Exception as e:
            print(f"[ERROR] Gagal terhubung ke ESP32-CAM ({self.url}): {e}")
            self._is_opened = False

    def isOpened(self):
        return self._is_opened

    def read(self):
        if not self._is_opened or self.stream is None:
            return False, None

        try:
            while True:
                self.bytes += self.stream.read(1024)
                a = self.bytes.find(b'\xff\xd8')  # JPEG SOI
                b = self.bytes.find(b'\xff\xd9')  # JPEG EOI
                if a != -1 and b != -1:
                    jpg = self.bytes[a:b+2]
                    self.bytes = self.bytes[b+2:]
                    frame = cv.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv.IMREAD_COLOR)
                    if frame is not None:
                        return True, frame
        except Exception as e:
            print(f"[ESP-CAM] Stream error / frame dropped: {e}")
            self._is_opened = False
            return False, None

    def release(self):
        if self.stream:
            try:
                self.stream.close()
            except Exception:
                pass
        self._is_opened = False


def get_camera_capture(source):
    if isinstance(source, str) and (source.startswith("http://") or source.startswith("https://") or source.startswith("rtsp://")):
        print(f"[INFO] Membuka stream ESP32-CAM: {source}")
        cap = cv.VideoCapture(source)
        if cap.isOpened():
            cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
            return cap
        else:
            print("[INFO] Fallback ke custom HTTP MJPEG Stream Reader...")
            return ESPCamStream(source)
    else:
        print(f"[INFO] Membuka webcam lokal index: {source}")
        return cv.VideoCapture(source)


# ============================================================
# TRACKER FACTORY
# ============================================================
def create_csrt_tracker():
    """Membuat CSRT Tracker compatible dengan berbagai versi OpenCV."""
    if hasattr(cv, "TrackerCSRT_create"):
        return cv.TrackerCSRT_create()
    if hasattr(cv, "legacy") and hasattr(cv.legacy, "TrackerCSRT_create"):
        return cv.legacy.TrackerCSRT_create()
    raise RuntimeError("CSRT tidak tersedia. Install opencv-contrib-python.")


# ============================================================
# GLOBAL STATE & MOUSE CALLBACK
# ============================================================
selecting = False
start_x, start_y = 0, 0
current_x, current_y = 0, 0
selected_bbox = None
click_point = None


def mouse_callback(event, x, y, flags, param):
    global selecting, start_x, start_y, current_x, current_y, selected_bbox, click_point

    if event == cv.EVENT_LBUTTONDOWN:
        selecting = True
        start_x, start_y = x, y
        current_x, current_y = x, y
        click_point = (x, y)

    elif event == cv.EVENT_MOUSEMOVE:
        if selecting:
            current_x, current_y = x, y

    elif event == cv.EVENT_LBUTTONUP:
        if not selecting:
            return
        selecting = False

        x1 = min(start_x, x)
        y1 = min(start_y, y)
        x2 = max(start_x, x)
        y2 = max(start_y, y)

        w = x2 - x1
        h = y2 - y1

        if w >= 10 and h >= 10:
            selected_bbox = (x1, y1, w, h)
            click_point = None


def clamp_bbox(bbox, frame_width, frame_height):
    x, y, w, h = bbox
    x = max(0, min(x, frame_width - 1))
    y = max(0, min(y, frame_height - 1))
    w = max(10, min(w, frame_width - x))
    h = max(10, min(h, frame_height - y))
    return (x, y, w, h)


def apply_deadzone(value, deadzone):
    if abs(value) < deadzone:
        return 0.0
    return value


# ============================================================
# MAIN APPLICATION
# ============================================================
def main():
    global selected_bbox, click_point

    ros_node_active = False
    cmd_pub = None
    telemetry_pub = None
    ros_sub = None

    # Check ROS node initialization
    if HAS_ROS:
        try:
            rospy.init_node("vision_target_node", anonymous=True)
            cmd_pub = rospy.Publisher("/cmd_vel", Twist, queue_size=1)
            telemetry_pub = rospy.Publisher("/target_telemetry", Point, queue_size=1)
            image_topic = rospy.get_param("~image_topic", "/camera/image_raw")
            use_esp = rospy.get_param("~use_esp_cam", USE_ESP_CAM)
            
            if not use_esp:
                ros_sub = ROSImageSubscriber(image_topic)
                ros_node_active = True
                print(f"[ROS] Node Vision Aktif! Membaca dari topik: {image_topic}")
        except Exception as e:
            print(f"[ROS] Tidak menggunakan ROS Node: {e}")

    cap = None
    if not ros_node_active:
        source = ESP_CAM_URL if USE_ESP_CAM else CAMERA_INDEX
        cap = get_camera_capture(source)
        if not cap.isOpened():
            print(f"[ERROR] Kamera / Stream ({source}) tidak dapat dibuka.")
            return

    window_name = "Multi-Target Vision Lock System (AutoStack ROS)"
    cv.namedWindow(window_name)
    cv.setMouseCallback(window_name, mouse_callback)

    tracker = None
    tracking = False
    smooth_cx, smooth_cy = None, None
    last_time = time.time()

    print("\n==============================================")
    print(" MULTI-TARGET LOCK & VISION ROS SYSTEM")
    print("==============================================")
    print(f"[MODE]: {'ROS Image Topic' if ros_node_active else ('ESP32-CAM' if USE_ESP_CAM else 'Webcam')}")
    print("[KONTROL KEYBOARD]")
    print(" R   : Reset lock / kembali ke deteksi multi-target")
    print(" ESC : Keluar")
    print("==============================================\n")

    rate = rospy.Rate(30) if ros_node_active else None

    while True:
        if ros_node_active:
            if rospy.is_shutdown():
                break
            ret, frame = ros_sub.read()
            if not ret:
                time.sleep(0.03)
                continue
        else:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Gagal membaca frame kamera.")
                break

        frame_h, frame_w = frame.shape[:2]
        frame_cx, frame_cy = frame_w // 2, frame_h // 2

        # Crosshair kamera utama
        cv.drawMarker(frame, (frame_cx, frame_cy), (255, 255, 255), cv.MARKER_CROSS, 20, 2)

        # 1. MULTI-TARGET DETECTION (HSV Mask)
        hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
        mask1 = cv.inRange(hsv, HSV_LOWER, HSV_UPPER)
        mask2 = cv.inRange(hsv, HSV_LOWER2, HSV_UPPER2)
        mask = cv.bitwise_or(mask1, mask2)

        contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        detected_targets = []
        target_id_count = 1

        for c in contours:
            area = cv.contourArea(c)
            if area >= MIN_CONTOUR_AREA:
                x, y, w, h = cv.boundingRect(c)
                M = cv.moments(c)
                if M["m00"] != 0:
                    cx_t = int(M["m10"] / M["m00"])
                    cy_t = int(M["m01"] / M["m00"])
                else:
                    cx_t, cy_t = x + w // 2, y + h // 2

                detected_targets.append({
                    "id": target_id_count,
                    "bbox": (x, y, w, h),
                    "center": (cx_t, cy_t),
                    "area": area,
                })
                target_id_count += 1

        # 2. SELEKSI TARGET VIA MOUSE
        if click_point is not None and not tracking:
            px, py = click_point
            clicked_on_target = False

            for t in detected_targets:
                tx, ty, tw, th = t["bbox"]
                if tx <= px <= tx + tw and ty <= py <= ty + th:
                    selected_bbox = t["bbox"]
                    clicked_on_target = True
                    print(f"[LOCK] Target #{t['id']} dipilih via Klik Mouse!")
                    break

            if not clicked_on_target:
                x1 = max(0, px - DEFAULT_ROI_W // 2)
                y1 = max(0, py - DEFAULT_ROI_H // 2)
                selected_bbox = (x1, y1, DEFAULT_ROI_W, DEFAULT_ROI_H)
                print(f"[LOCK] Custom ROI dibuat di ({px}, {py})")

            click_point = None

        # 3. INITIALIZE TRACKER
        if selected_bbox is not None:
            bbox = clamp_bbox(selected_bbox, frame_w, frame_h)
            try:
                tracker = create_csrt_tracker()
                tracker.init(frame, bbox)
                tracking = True
                bx, by, bw, bh = bbox
                smooth_cx = bx + bw / 2.0
                smooth_cy = by + bh / 2.0
                print(f"[TRACKER] Lock Target Initialized: {bbox}")
            except Exception as e:
                print(f"[ERROR] Gagal initialize tracker: {e}")
                tracking = False

            selected_bbox = None

        # 4. TRACKING & ROS VELOCITY COMMAND PUBLISHING
        twist_msg = Twist()

        if tracking and tracker is not None:
            success, bbox = tracker.update(frame)

            if success:
                x, y, w, h = [int(v) for v in bbox]
                valid = (w > 5 and h > 5 and x + w > 0 and y + h > 0 and x < frame_w and y < frame_h)

                if valid:
                    target_cx = x + w / 2.0
                    target_cy = y + h / 2.0

                    if smooth_cx is None: smooth_cx = target_cx
                    if smooth_cy is None: smooth_cy = target_cy

                    smooth_cx = ALPHA * target_cx + (1.0 - ALPHA) * smooth_cx
                    smooth_cy = ALPHA * target_cy + (1.0 - ALPHA) * smooth_cy

                    error_x = smooth_cx - frame_cx
                    error_y = smooth_cy - frame_cy
                    error_x_control = apply_deadzone(error_x, DEADZONE)

                    # Normalize Error (-1.0 to 1.0)
                    norm_x = np.clip(error_x / (frame_w / 2.0), -1.0, 1.0)

                    # PROPORTIONAL ROS VELOCITY CONTROL FOR ESP32 / DIFFERENTIAL DRIVE
                    if cmd_pub is not None:
                        # Angular velocity (Steering): -Kp * norm_x
                        twist_msg.angular.z = -1.2 * norm_x
                        # Forward velocity (Speed up when centered)
                        if abs(norm_x) < 0.3:
                            twist_msg.linear.x = 0.15
                        else:
                            twist_msg.linear.x = 0.05
                        cmd_pub.publish(twist_msg)

                    if telemetry_pub is not None:
                        telemetry_pub.publish(Point(x=smooth_cx, y=smooth_cy, z=0.0))

                    # Visuals
                    cv.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv.circle(frame, (int(smooth_cx), int(smooth_cy)), 6, (0, 0, 255), -1)
                    cv.line(frame, (frame_cx, frame_cy), (int(smooth_cx), int(smooth_cy)), (0, 255, 0), 2)

                    cv.putText(frame, "STATUS: LOCKED (ROS ACTIVE)", (20, 35), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv.putText(frame, f"CMD_VEL -> LinX: {twist_msg.linear.x:.2f} AngZ: {twist_msg.angular.z:.2f}", (20, 65), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                else:
                    tracking = False
            else:
                cv.putText(frame, "TARGET LOST (Tekan 'R' untuk reset)", (20, 35), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                if cmd_pub is not None:
                    cmd_pub.publish(Twist()) # Stop robot
        else:
            # Unlocked state, show detected targets
            for t in detected_targets:
                tx, ty, tw, th = t["bbox"]
                tid = t["id"]
                tcx, tcy = t["center"]

                cv.rectangle(frame, (tx, ty), (tx + tw, ty + th), (255, 255, 0), 2)
                cv.circle(frame, (tcx, tcy), 4, (0, 255, 255), -1)
                cv.putText(frame, f"Target #{tid}", (tx, max(20, ty - 8)), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

            cv.putText(frame, f"DETEKSI TARGET ({len(detected_targets)}) - Klik target untuk LOCK", (20, 35), cv.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

        # Draw mouse selection box
        if selecting:
            x1, y1 = min(start_x, current_x), min(start_y, current_y)
            x2, y2 = max(start_x, current_x), max(start_y, current_y)
            cv.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 2)

        # FPS
        now = time.time()
        dt = now - last_time
        last_time = now
        fps = 1.0 / dt if dt > 0 else 0
        cv.putText(frame, f"FPS: {fps:.1f}", (frame_w - 130, 35), cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv.imshow(window_name, frame)

        key = cv.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break
        elif key == ord("r") or key == ord("R"):
            print("\n[RESET] Unlock target, kembali ke mode deteksi multi-target.")
            tracker = None
            tracking = False
            smooth_cx, smooth_cy = None, None
            if cmd_pub is not None: cmd_pub.publish(Twist())
        elif ord("1") <= key <= ord("9") and not tracking:
            target_idx = key - ord("1")
            if target_idx < len(detected_targets):
                selected_target = detected_targets[target_idx]
                selected_bbox = selected_target["bbox"]

    if cap is not None:
        cap.release()
    cv.destroyAllWindows()


if __name__ == "__main__":
    main()
