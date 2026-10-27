#!/usr/bin/env python3
"""
Eksbot2 Robot API & Controller Module (robot_api.py)
----------------------------------------------------
Modul penggabungan kendali perangkat keras (RobotAPI) dan logika state machine (Controller).

Komponen:
  - RobotAPI   : Antarmuka pengiriman instruksi gerak kecepatan (linear/angular) dan posisi servo
                 (gripper/lift) ke ROS Topic (/cmd_vel) atau langsung via Wi-Fi UDP ke ESP32 fisik.
                 Juga menangani pembacaan telemetri baterai ADC non-blocking dari ESP32.
  - Controller : Otak navigasi & autopilot (MANUAL/AUTO, ALIGNING -> DRIVING -> PICKUP),
                 pemetaan kontrol keyboard (WSAD, E-STOP), manajemen crosshair dan titik bidik,
                 serta kompilasi data telemetri lengkap untuk HUD antarmuka pilot.
"""

import json
import os
import socket
import threading
import time
import urllib.request

import numpy as np

try:
    import rospy
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry
    from std_msgs.msg import Int32, Bool
    HAS_ROS = True
except ImportError:
    HAS_ROS = False


# ======================================================================
# Konstanta Kontrol & Autopilot
# ======================================================================
MOVE_KEYS = {
    "KeyW": "fwd", "ArrowUp": "fwd",
    "KeyS": "back", "ArrowDown": "back",
    "KeyA": "left", "ArrowLeft": "left",
    "KeyD": "right", "ArrowRight": "right",
}

KEY_TIMEOUT = 0.8         # detik: tombol "ditahan" dianggap lepas jika heartbeat berhenti
MAX_LINEAR = 0.50         # m/s, sama dengan MAX_SPEED di firmware kontrol
BASE_LINEAR = 0.30
BASE_ANGULAR = 1.2
REF_AREA = 320 * 240      # resolusi acuan ambang area (QVGA)
GRIP_AREA_REF = 12000     # luas bbox (QVGA) saat target dianggap sudah dalam jangkauan gripper

PICKUP_STEPS = [          # (aksi, jeda setelah aksi dalam detik)
    ("stop", 0.2),
    ("lift_down", 0.4),
    ("grip_close", 0.6),
    ("lift_up", 0.5),
]

CROSSHAIR_DEFAULT = {
    "visible": True,
    "style": "cross",      # cross | gapcross | dot | circle
    "size": 24,            # panjang lengan / radius (px frame)
    "gap": 6,              # celah tengah (px frame)
    "thickness": 2,
    "color": "lime",       # lime | red | cyan | yellow | white | black
    "dx": 0,               # offset titik bidik terhadap tengah frame (px frame)
    "dy": 0,
}
CROSSHAIR_STYLES = ("cross", "gapcross", "dot", "circle")
CROSSHAIR_COLORS = ("lime", "red", "cyan", "yellow", "white", "black")

SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".config", "eksbot2", "hmi_settings.json")


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ======================================================================
# 1. RobotAPI: Antarmuka Komunikasi Hardware (UDP / ROS)
# ======================================================================
class RobotAPI:
    def __init__(self, esp_ip="192.168.4.1", esp_port=8888, use_ros=False):
        self.esp_ip = esp_ip
        self.esp_port = esp_port
        self.use_ros = use_ros and HAS_ROS

        # ROS Publishers & Subscribers
        self.cmd_pub = None
        self.servo_pub = None
        self.lift_pub = None
        self.vacuum_pub = None
        self.odom_sub = None

        # UDP Socket untuk pengiriman Wi-Fi langsung ke ESP32-CAM
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.setblocking(False)
        except Exception:
            pass

        # State Kecepatan, Servo & Baterai Terakhir
        self.current_linear_x = 0.0
        self.current_angular_z = 0.0
        self.current_gripper = 0   # 0: OPEN, 90: CLOSED
        self.current_lift = 0      # 0: DOWN, 90: UP
        self.battery_v = 12.0
        self.battery_pct = 95

        # ------------------------------------------------------------------
        # State Odometri Robot (Posisi 2D: X, Y dalam meter, Yaw dalam radian)
        # ------------------------------------------------------------------
        self.pose_x = 0.0
        self.pose_y = 0.0
        self.pose_yaw = 0.0
        self.wheel_radius = 0.033        # meter (~66mm diameter)
        self.wheel_base = 0.160          # meter (jarak antar roda kiri-kanan)
        self.ticks_per_rev = 360.0       # resolusi encoder
        self._last_enc_l = None
        self._last_enc_r = None
        self._last_odom_ts = time.time()

        if self.use_ros:
            self._init_ros()

    def _init_ros(self):
        """Menginisialisasi ROS node, publisher, & odometry subscriber."""
        try:
            if not rospy.core.is_initialized():
                return
            self.cmd_pub = rospy.Publisher("/cmd_vel", Twist, queue_size=1)
            self.servo_pub = rospy.Publisher("/esp32/servo", Int32, queue_size=1)
            self.lift_pub = rospy.Publisher("/esp32/lift", Int32, queue_size=1)
            self.vacuum_pub = rospy.Publisher("/dummy_robot/gripper_switch", Bool, queue_size=1)
            self.odom_sub = rospy.Subscriber("/odom", Odometry, self._ros_odom_callback, queue_size=1)
            print("[ROBOT_API] ROS Publishers & Subscriber /odom aktif")
        except Exception as e:
            print(f"[ROBOT_API] ROS tidak aktif, fallback ke Wi-Fi UDP Socket: {e}")
            self.use_ros = False

    def _ros_odom_callback(self, msg):
        """Callback penerimaan odometri resmi dari ROS simulasi / node odometry."""
        pos = msg.pose.pose.position
        ori = msg.pose.pose.orientation
        self.pose_x = float(pos.x)
        self.pose_y = float(pos.y)

        # Hitung yaw dari quaternion (z, w)
        siny_cosp = 2.0 * (ori.w * ori.z + ori.x * ori.y)
        cosy_cosp = 1.0 - 2.0 * (ori.y * ori.y + ori.z * ori.z)
        self.pose_yaw = float(np.arctan2(siny_cosp, cosy_cosp))

    def update_encoder_ticks(self, enc_l, enc_r):
        """
        Hitung integrasi dead reckoning dari akumulasi tick encoder (roda kiri & kanan).
        Sangat ringan dan tahan fluktuasi Wi-Fi karena berbasis total tick count.
        """
        if self._last_enc_l is None or self._last_enc_r is None:
            self._last_enc_l = enc_l
            self._last_enc_r = enc_r
            self._last_odom_ts = time.time()
            return

        d_ticks_l = enc_l - self._last_enc_l
        d_ticks_r = enc_r - self._last_enc_r
        self._last_enc_l = enc_l
        self._last_enc_r = enc_r

        # Jarak tempuh masing-masing roda dalam meter
        dist_per_tick = (2.0 * np.pi * self.wheel_radius) / self.ticks_per_rev
        dl = d_ticks_l * dist_per_tick
        dr = d_ticks_r * dist_per_tick

        # Integrasi pergerakan diferensial
        ds = (dr + dl) / 2.0
        dtheta = (dr - dl) / self.wheel_base

        # Update pose
        mid_theta = self.pose_yaw + (dtheta / 2.0)
        self.pose_x += ds * np.cos(mid_theta)
        self.pose_y += ds * np.sin(mid_theta)
        self.pose_yaw = (self.pose_yaw + dtheta + np.pi) % (2.0 * np.pi) - np.pi
        self._last_odom_ts = time.time()

    def reset_odometry(self, x=0.0, y=0.0, yaw=0.0):
        """Reset pose odometri ke titik awal / home."""
        self.pose_x = float(x)
        self.pose_y = float(y)
        self.pose_yaw = float(yaw)

    def move(self, linear_x, angular_z):
        """Mengirimkan instruksi kecepatan maju/mundur (linear_x) dan belok (angular_z)."""
        self.current_linear_x = float(linear_x)
        self.current_angular_z = float(angular_z)

        # 1. Kirim via ROS jika aktif
        if self.use_ros and self.cmd_pub is not None:
            twist = Twist()
            twist.linear.x = self.current_linear_x
            twist.angular.z = self.current_angular_z
            self.cmd_pub.publish(twist)

        # 2. Kirim via Wi-Fi UDP Socket ke ESP32 fisik
        payload = {
            "cmd": "move",
            "lin": round(self.current_linear_x, 2),
            "ang": round(self.current_angular_z, 2),
            "grip": self.current_gripper,
            "lift": self.current_lift
        }
        self._send_udp_esp(payload)

    def set_gripper(self, angle_or_state):
        """Mengatur posisi servo gripper (Jepit/Buka)."""
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

    def set_lift(self, angle_or_state):
        """Mengatur posisi servo lift (Naik/Turun)."""
        if isinstance(angle_or_state, str):
            angle = 90 if angle_or_state.upper() in ["UP", "NAIK"] else 0
        else:
            angle = int(angle_or_state)

        self.current_lift = max(0, min(angle, 180))

        if self.use_ros and self.lift_pub is not None:
            self.lift_pub.publish(Int32(data=self.current_lift))

        self.move(self.current_linear_x, self.current_angular_z)

    def stop(self):
        """Menghentikan semua gerakan robot."""
        self.move(0.0, 0.0)

    def _send_udp_esp(self, payload_dict):
        """Mengirimkan JSON string payload via UDP ke ESP32-CAM dan membaca telemetri jika ada."""
        try:
            msg_bytes = json.dumps(payload_dict).encode('utf-8')
            self.sock.sendto(msg_bytes, (self.esp_ip, self.esp_port))
            # Baca paket balasan telemetri dari ESP32 (non-blocking)
            try:
                data, _ = self.sock.recvfrom(256)
                if data:
                    res = json.loads(data.decode('utf-8', errors='ignore'))
                    if "batt" in res:
                        self.battery_v = float(res["batt"])
                    if "pct" in res:
                        self.battery_pct = int(res["pct"])
                    # Telemetri encoder dari ESP32 fisik
                    if "enc_l" in res and "enc_r" in res:
                        self.update_encoder_ticks(int(res["enc_l"]), int(res["enc_r"]))
                    elif "ticks_l" in res and "ticks_r" in res:
                        self.update_encoder_ticks(int(res["ticks_l"]), int(res["ticks_r"]))
                    # Jika ESP32 mengirim koordinat jadi (opsional)
                    if "odom_x" in res and "odom_y" in res:
                        self.pose_x = float(res["odom_x"])
                        self.pose_y = float(res["odom_y"])
                        if "odom_yaw" in res:
                            self.pose_yaw = float(res["odom_yaw"])
            except (BlockingIOError, socket.error, ValueError):
                pass
        except Exception:
            pass


# ======================================================================
# 2. Controller: Logika Navigasi, Autopilot & State Machine
# ======================================================================
class Controller:
    def __init__(self, robot=None, vision=None, draw_overlay=False, settings_path=SETTINGS_PATH):
        self.robot = robot if robot is not None else RobotAPI()
        self.vision = vision
        self.draw_overlay = draw_overlay      # True hanya untuk mode jendela OpenCV
        self.settings_path = settings_path
        self._lock = threading.RLock()

        self.mode = "MANUAL"                  # MANUAL | AUTO
        self.phase = "IDLE"                   # IDLE | ALIGNING | DRIVING | PICKUP
        self.speed_scale = 1.0
        self.crosshair = dict(CROSSHAIR_DEFAULT)

        self._held = set()
        self._held_ts = 0.0
        self._pending_lock = None             # (nx, ny) ternormalisasi 0..1
        self._pickup_idx = -1
        self._pickup_next = 0.0
        self._cmd = (0.0, 0.0)
        self._events = []                     # pesan singkat untuk HUD
        self._last_vis = {}
        self._fps = 0.0
        self._last_t = time.time()
        self.link_ok = False
        self.source_name = "-"

        # State pelacakan memori arah target (search sweep jika target keluar layar)
        self._last_seen_norm_x = 0.0
        self._search_until = 0.0

        self._load_settings()

    # ------------------------------------------------------------------
    # Persistensi pengaturan
    # ------------------------------------------------------------------
    def _load_settings(self):
        try:
            with open(self.settings_path) as f:
                data = json.load(f)
            self.set_crosshair(data.get("crosshair", {}), save=False)
            self.speed_scale = _clamp(float(data.get("speed_scale", 1.0)), 0.3, 1.5)
        except Exception:
            pass

    def _save_settings(self):
        try:
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, "w") as f:
                json.dump({"crosshair": self.crosshair, "speed_scale": self.speed_scale}, f, indent=2)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Input: keyboard & aksi
    # ------------------------------------------------------------------
    def set_keys(self, codes):
        """Daftar kode tombol gerak yang SEDANG ditahan (heartbeat dari browser)."""
        with self._lock:
            self._held = {MOVE_KEYS[c] for c in codes if c in MOVE_KEYS}
            self._held_ts = time.time()
            if self._held and self.mode == "AUTO":
                self._set_mode("MANUAL", "Override manual")

    def press_gui(self, direction):
        """Untuk jendela OpenCV GUI."""
        with self._lock:
            self._held = {direction}
            self._held_ts = time.time()

    def do_action(self, name, value=None):
        """Aksi sekali tekan. Mengembalikan True bila dikenali."""
        with self._lock:
            if name == "estop":
                self.estop()
            elif name == "toggle_mode":
                self._set_mode("AUTO" if self.mode == "MANUAL" else "MANUAL")
            elif name == "mode":
                self._set_mode("AUTO" if str(value).upper() == "AUTO" else "MANUAL")
            elif name == "color":
                if self.vision and self.vision.set_color_mode(str(value)):
                    self._cancel_pickup()
                    self.robot.stop()
                    self.phase = "IDLE" if self.mode == "MANUAL" else "ALIGNING"
            elif name == "cycle_color":
                if self.vision:
                    order = ["RED", "GREEN", "BLUE", "YELLOW"]
                    curr = self.vision.active_color
                    nxt = order[(order.index(curr) + 1) % len(order)] if curr in order else "RED"
                    self.vision.set_color_mode(nxt)
                    self._cancel_pickup()
                    self.robot.stop()
                    self.phase = "IDLE" if self.mode == "MANUAL" else "ALIGNING"
            elif name == "cancel_target":
                self.cancel_target()
            elif name == "grip":
                self.robot.set_gripper("CLOSE" if str(value).lower() in ("close", "1", "true") else "OPEN")
            elif name == "lift":
                self.robot.set_lift("UP" if str(value).lower() in ("up", "1", "true") else "DOWN")
            elif name == "speed":
                step = 0.1 if float(value) > 0 else -0.1
                self.speed_scale = round(_clamp(self.speed_scale + step, 0.3, 1.5), 2)
                self._save_settings()
            elif name == "crosshair_toggle":
                self.crosshair["visible"] = not self.crosshair["visible"]
                self._save_settings()
            elif name == "crosshair_reset":
                self.crosshair = dict(CROSSHAIR_DEFAULT)
                self._save_settings()
            elif name == "crosshair_nudge":
                self.set_crosshair({"dx": self.crosshair["dx"] + int(value[0]),
                                    "dy": self.crosshair["dy"] + int(value[1])})
            else:
                return False
            return True

    def estop(self):
        """Henti darurat: stop motor, batalkan semua, kembali ke MANUAL."""
        self._held = set()
        self._cancel_pickup()
        if self.vision:
            self.vision.reset_tracker()
        self._pending_lock = None
        self.mode = "MANUAL"
        self.phase = "IDLE"
        self._cmd = (0.0, 0.0)
        self.robot.stop()
        self._event("E-STOP")

    def cancel_target(self):
        self._cancel_pickup()
        if self.vision:
            self.vision.reset_tracker()
        self._pending_lock = None
        self._cmd = (0.0, 0.0)
        self.robot.stop()
        self.phase = "IDLE" if self.mode == "MANUAL" else "ALIGNING"
        self._event("Target dibatalkan")

    def request_lock(self, nx, ny):
        """Klik pada video (koordinat ternormalisasi) -> lock target & pindah ke AUTO."""
        with self._lock:
            self._pending_lock = (_clamp(float(nx), 0.0, 1.0), _clamp(float(ny), 0.0, 1.0))

    def set_crosshair(self, data, save=True):
        with self._lock:
            c = self.crosshair
            if "visible" in data:
                c["visible"] = bool(data["visible"])
            if data.get("style") in CROSSHAIR_STYLES:
                c["style"] = data["style"]
            if data.get("color") in CROSSHAIR_COLORS:
                c["color"] = data["color"]
            for key, lo, hi in (("size", 4, 120), ("gap", 0, 60), ("thickness", 1, 6),
                                ("dx", -160, 160), ("dy", -120, 120)):
                if key in data:
                    try:
                        c[key] = int(_clamp(int(data[key]), lo, hi))
                    except (TypeError, ValueError):
                        pass
            if save:
                self._save_settings()

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------
    def _event(self, text):
        self._events.append((time.time(), text))
        self._events = self._events[-5:]

    def _set_mode(self, mode, reason=None):
        if mode == self.mode:
            return
        self.mode = mode
        self._cancel_pickup()
        self.robot.stop()
        self._cmd = (0.0, 0.0)
        self.phase = "ALIGNING" if mode == "AUTO" else "IDLE"
        self._event(reason or f"Mode {mode}")
        print(f"[MODE SWITCH] Mode berganti ke: {'MANUAL WSAD' if mode == 'MANUAL' else 'AUTO VISION NAVIGASI'}")

    def _cancel_pickup(self):
        self._pickup_idx = -1

    def _aim(self, frame_w, frame_h):
        return (frame_w // 2 + self.crosshair["dx"], frame_h // 2 + self.crosshair["dy"])

    def _manual_command(self, now):
        if self._held and now - self._held_ts > KEY_TIMEOUT:
            self._held = set()
        fwd = ("fwd" in self._held) - ("back" in self._held)
        turn = ("left" in self._held) - ("right" in self._held)
        v_lin = min(BASE_LINEAR * self.speed_scale, MAX_LINEAR)
        v_ang = BASE_ANGULAR * self.speed_scale
        lin = fwd * v_lin
        ang = turn * v_ang * (0.7 if fwd else 1.0)
        return lin, ang

    def _run_pickup(self, now):
        if now >= self._pickup_next:
            self._pickup_idx += 1
            if self._pickup_idx >= len(PICKUP_STEPS):
                if self.vision:
                    self.vision.reset_tracker()
                self._pickup_idx = -1
                self.phase = "ALIGNING"
                self._event("Pickup selesai")
                return 0.0, 0.0
            action, delay = PICKUP_STEPS[self._pickup_idx]
            if action == "stop":
                self.robot.stop()
            elif action == "lift_down":
                self.robot.set_lift("DOWN")
            elif action == "grip_close":
                self.robot.set_gripper("CLOSE")
            elif action == "lift_up":
                self.robot.set_lift("UP")
            self._pickup_next = now + delay
        return 0.0, 0.0

    def _auto_command(self, v, now):
        if self.phase == "PICKUP" and self._pickup_idx >= -1:
            return self._run_pickup(now)

        # 1. JIKA TARGET SEDANG TERKUNCI (TRACKING AKTIF)
        if v.get("tracking"):
            norm_x = v["norm_x"]
            vel_x = v.get("vel_x", 0.0)
            frame_w = v.get("frame_w", 320)

            # LEAD-PURSUIT: Hitung prediksi posisi masa depan (antisipasi gerakan target)
            # Jika target bergerak ke kanan, robot belok lebih awal ke kanan mendahului target
            lead_time = 0.25 # detik antisipasi
            pred_offset_x = (vel_x * lead_time) / (frame_w / 2.0)
            norm_x_lead = float(np.clip(norm_x + pred_offset_x, -1.0, 1.0))

            self._last_seen_norm_x = norm_x_lead
            self._last_vel_x = vel_x
            self._search_until = 0.0          # Reset waktu pencarian
        else:
            # 2. JIKA TARGET HILANG / TERGELINCIR DARI FRAME:
            # Lakukan sapuan pencarian (Search Sweep) cerdas ke arah vektor pelarian target.
            # Konvensi Differential Drive:
            #   ang > 0: Putar Kiri (CCW)
            #   ang < 0: Putar Kanan (CW)
            if self.phase in ("ALIGNING", "DRIVING") and now < self._search_until:
                # Prioritaskan arah vektor kecepatan pelarian (vel_x), jika diam gunakan posisi terakhir (norm_x)
                if abs(getattr(self, "_last_vel_x", 0.0)) > 15.0:
                    turn_sign = -1.0 if self._last_vel_x > 0 else 1.0  # Ke kanan -> ang < 0, Ke kiri -> ang > 0
                else:
                    turn_sign = -1.0 if self._last_seen_norm_x > 0 else 1.0
                return 0.0, float(turn_sign * 1.3 * self.speed_scale)

            self.phase = "ALIGNING"
            return 0.0, 0.0

        frame_h = v["frame_h"]
        target_cy = v["target_cy"]
        target_area = v["target_area"]
        area_limit = GRIP_AREA_REF * (v["frame_w"] * frame_h) / REF_AREA

        # Gunakan norm_x_lead untuk koreksi sudut belok yang antisipatif
        if abs(norm_x_lead) > 0.35:
            self.phase = "ALIGNING"

        if self.phase not in ("ALIGNING", "DRIVING"):
            self.phase = "ALIGNING"

        if self.phase == "ALIGNING":
            lin = 0.0
            ang = float(np.clip(-2.5 * norm_x_lead, -1.8, 1.8))
            if abs(norm_x_lead) <= 0.08:
                self.phase = "DRIVING"
            return lin, ang

        # DRIVING: maju adaptif, kecepatan turun saat mendekat
        dist_ratio = max(0.0, float(frame_h - target_cy) / float(frame_h))
        lin = float(np.clip(0.12 + 0.25 * dist_ratio, 0.12, 0.32)) * self.speed_scale
        lin = min(lin, MAX_LINEAR)
        ang = -1.3 * norm_x_lead

        # Catat waypoint lokal terakhir di odometri saat target terlihat jelas
        self._last_target_x = getattr(self.robot, "pose_x", 0.0)
        self._last_target_y = getattr(self.robot, "pose_y", 0.0)

        # Kondisi pemicu Pickup: target di tepi bawah frame (blind spot dekat gripper) atau area besar
        if target_cy > (frame_h - 4) or target_area > area_limit:
            self._event("Target tercapai -> pickup")
            print("[AUTO-GRIP] Target tercapai! Eksekusi jepit dan angkat...")
            self.phase = "PICKUP"
            self._pickup_idx = -1
            self._pickup_next = now
            return 0.0, 0.0
        return lin, ang

    # ------------------------------------------------------------------
    # Siklus utama (dipanggil tiap frame dari main.py)
    # ------------------------------------------------------------------
    def update(self, frame):
        """Memproses satu frame -> (frame_untuk_tampil, telemetri). Juga mengirim perintah ke robot."""
        now = time.time()
        with self._lock:
            h, w = frame.shape[:2]

            # Lock via klik dilakukan pada frame BERSIH (sebelum overlay apa pun)
            if self._pending_lock is not None:
                nx, ny = self._pending_lock
                self._pending_lock = None
                if self.vision and self.vision.lock_at_point(frame, int(nx * w), int(ny * h)):
                    self._held = set()
                    self._cancel_pickup()
                    if self.mode != "AUTO":
                        self.mode = "AUTO"
                    self.phase = "ALIGNING"
                    self._event("Target terkunci")
                else:
                    self._event("Lock gagal")

            if self.vision:
                frame_out, v = self.vision.process_frame(
                    frame, manual_mode=(self.mode == "MANUAL"),
                    aim=self._aim(w, h), draw=self.draw_overlay)
            else:
                frame_out, v = frame, {}

            if v.get("lost"):
                self._event("TARGET LOST - SEARCHING")
                # Berikan jendela waktu 1.5 detik untuk memutar badan ke arah terakhir target
                if self.mode == "AUTO":
                    self._search_until = now + 1.5
                else:
                    self.robot.stop()

                if self.phase != "PICKUP":
                    self.phase = "ALIGNING" if self.mode == "AUTO" else "IDLE"

            if self.mode == "MANUAL":
                lin, ang = self._manual_command(now)
            else:
                lin, ang = self._auto_command(v, now)

            self._cmd = (lin, ang)
            if self.phase != "PICKUP" or self.mode == "MANUAL":
                self.robot.move(lin, ang)

            dt = now - self._last_t
            self._last_t = now
            if dt > 0:
                self._fps = 0.9 * self._fps + 0.1 * (1.0 / dt) if self._fps else 1.0 / dt
            self._last_vis = v
            return frame_out, self.telemetry()

    def idle(self):
        """Dipanggil saat TIDAK ada frame baru: pastikan robot berhenti & HUD tahu link putus."""
        with self._lock:
            self._cmd = (0.0, 0.0)
            self._held = set()
            self._cancel_pickup()
            if self.phase == "PICKUP":
                self.phase = "ALIGNING"
            self.robot.stop()

    # ------------------------------------------------------------------
    # Telemetri untuk HUD
    # ------------------------------------------------------------------
    def telemetry(self):
        with self._lock:
            v = self._last_vis or {}
            now = time.time()
            targets = [{"id": t["id"], "bbox": list(t["bbox"])} for t in v.get("detected_targets", [])]
            bbox = list(v["bbox"]) if v.get("bbox") else None
            active_col = self.vision.active_color if self.vision else "RED"
            return {
                "mode": self.mode,
                "phase": self.phase,
                "color": active_col,
                "tracking": bool(v.get("tracking")),
                "lost": bool(v.get("lost")),
                "norm_x": round(float(v.get("norm_x", 0.0)), 3),
                "err_x": round(float(v.get("error_x", 0.0)), 1),
                "err_y": round(float(v.get("error_y", 0.0)), 1),
                "area": int(v.get("target_area", 0)),
                "bbox": bbox,
                "targets": targets,
                "target_center": [round(float(v.get("target_cx", 0)), 1), round(float(v.get("target_cy", 0)), 1)],
                "frame": [int(v.get("frame_w", 320)), int(v.get("frame_h", 240))],
                "aim": list(v.get("aim", (160, 120))),
                "lin": round(self._cmd[0], 2),
                "ang": round(self._cmd[1], 2),
                "grip": int(getattr(self.robot, "current_gripper", 0)),
                "lift": int(getattr(self.robot, "current_lift", 0)),
                "speed_scale": self.speed_scale,
                "keys": sorted(self._held),
                "fps": round(self._fps, 1),
                "link": bool(self.link_ok),
                "source": self.source_name,
                "battery_v": round(float(getattr(self.robot, "battery_v", 12.0)), 2),
                "battery_pct": int(getattr(self.robot, "battery_pct", 95)),
                "odom_x": round(float(getattr(self.robot, "pose_x", 0.0)), 3),
                "odom_y": round(float(getattr(self.robot, "pose_y", 0.0)), 3),
                "odom_deg": round(float(np.degrees(getattr(self.robot, "pose_yaw", 0.0))), 1),
                "obj_vel_x": round(float(v.get("vel_x", 0.0)), 1),
                "obj_vel_y": round(float(v.get("vel_y", 0.0)), 1),
                "obj_speed": round(float(v.get("speed", 0.0)), 1),
                "obj_dir": str(v.get("move_dir", "STILL")),
                "pred_target": list(v.get("pred_target", [0, 0])),
                "crosshair": dict(self.crosshair),
                "events": [{"t": round(now - t, 1), "text": s} for t, s in self._events if now - t < 4.0],
            }
