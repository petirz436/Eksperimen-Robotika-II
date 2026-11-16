#!/usr/bin/env python3
"""
Eksbot2 Main Control Application (main.py)
------------------------------------------
Orkestrator tipis yang merangkai modul:

  vision.py          -> sumber gambar (open_source) + filter warna HSV + kontur + CSRT lock (VisionEngine)
  robot_api.py       -> interface robot UDP/ROS (RobotAPI) + navigasi/autopilot (Controller)
  hmi/               -> HMI web: stream MJPEG + HUD Canvas + kontrol browser (HMIServer)

Cara run:
  Robot fisik (TANPA ROS)    : python3 main.py                (= --source esp)
  Simulasi Gazebo (ROS)      : roslaunch eksbot_simulation modular_control.launch
                               atau: python3 main.py --source sim
  Uji tanpa robot (webcam)   : python3 main.py --source webcam
  Tambahan jendela OpenCV    : --gui        Tanpa membuka browser: --no-browser
"""

import argparse
import sys
import time
import webbrowser

import cv2 as cv
import numpy as np

from hmi import HMIServer
from robot_api import RobotAPI, Controller
from vision import open_source, HAS_ROS, VisionEngine

if HAS_ROS:
    import rospy


def parse_args():
    launched_by_ros = any(a.startswith("__name:=") for a in sys.argv)
    argv = [a for a in sys.argv[1:] if ":=" not in a]
    p = argparse.ArgumentParser(description="Eksbot2 Pilot Console")
    p.add_argument("--source", choices=["esp", "sim", "webcam"], default="sim" if launched_by_ros else "esp",
                   help="Sumber kamera & jalur perintah (default: esp, atau sim jika dari roslaunch)")
    p.add_argument("--esp-ip", default="192.168.4.1", help="IP ESP32-CAM SoftAP (default: 192.168.4.1)")
    p.add_argument("--control-ip", default="192.168.4.10", help="IP ESP32-Control UDP (default: 192.168.4.10)")
    p.add_argument("--esp-port", type=int, default=8888, help="Port UDP kontrol ESP32-Control (default: 8888)")
    p.add_argument("--stream-url", default=None, help="Override URL stream MJPEG (default: http://<esp-ip>/stream)")
    p.add_argument("--image-topic", default="/camera/image_raw", help="Topik kamera ROS (mode sim)")
    p.add_argument("--webcam", type=int, default=0, help="Index webcam (mode webcam)")
    p.add_argument("--port", type=int, default=8000, help="Port HMI web (dicoba naik jika terpakai)")
    p.add_argument("--no-browser", action="store_true", help="Jangan buka browser otomatis")
    p.add_argument("--gui", action="store_true", help="Tampilkan juga jendela OpenCV (keyboard via jendela)")
    return p.parse_args(argv)


# ============================================================
# Jendela OpenCV opsional (--gui): overlay sederhana dari telemetri
# ============================================================
GUI_KEYS = {
    ord('w'): "fwd", ord('s'): "back", ord('a'): "right", ord('d'): "left",
}
GUI_ACTIONS = {
    32: ("estop", None), ord('m'): ("toggle_mode", None),
    ord('1'): ("color", "RED"), ord('2'): ("color", "GREEN"), ord('3'): ("color", "BLUE"),
    ord('r'): ("cancel_target", None),
    ord('j'): ("grip", "close"), ord('k'): ("grip", "open"),
    ord('u'): ("lift", "up"), ord('i'): ("lift", "down"),
    ord('='): ("speed", 1), ord('+'): ("speed", 1), ord('-'): ("speed", -1),
    ord('c'): ("crosshair_toggle", None),
}


def draw_gui_overlay(frame, t):
    out = frame.copy()
    ax, ay = t["aim"]
    if t["crosshair"]["visible"]:
        cv.drawMarker(out, (int(ax), int(ay)), (0, 255, 0), cv.MARKER_CROSS, 24, 2)
    if t["tracking"] and t["bbox"]:
        x, y, w, h = t["bbox"]
        cv.rectangle(out, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cx, cy = t["target_center"]
        cv.line(out, (int(ax), int(ay)), (int(cx), int(cy)), (0, 0, 255), 1)
    else:
        for tg in t["targets"]:
            x, y, w, h = tg["bbox"]
            cv.rectangle(out, (x, y), (x + w, y + h), (0, 255, 255), 1)
            cv.putText(out, f"#{tg['id']}", (x, max(12, y - 4)), cv.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    cv.putText(out, f"{t['mode']} {t['phase']} {t['color']} {t['fps']:.0f}fps", (8, 18),
               cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv.putText(out, f"lin {t['lin']:.2f} ang {t['ang']:.2f}", (8, out.shape[0] - 8),
               cv.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    return out


def mouse_cb_factory(ctrl, state):
    def cb(event, x, y, flags, param):
        if event == cv.EVENT_LBUTTONDOWN and state.get("size"):
            w, h = state["size"]
            ctrl.request_lock(x / float(w), y / float(h))
    return cb


# ============================================================
# MAIN
# ============================================================
def main():
    args = parse_args()

    print("==================================================")
    print("      EKSBOT2 MODULAR CONTROL & VISION SYSTEM     ")
    print("==================================================")
    print(f"[MAIN] Sumber: {args.source}")

    use_ros = args.source == "sim"
    if use_ros:
        if not HAS_ROS:
            print("[MAIN] ERROR: --source sim membutuhkan ROS (source /opt/ros/noetic/setup.bash).")
            return 1
        rospy.init_node("eksbot2_main_node", anonymous=True, disable_signals=True)
        print("[MAIN] Mode ROS Simulasi: perintah -> /cmd_vel, kamera <- " + args.image_topic)
    else:
        stream_desc = args.stream_url or f"http://{args.esp_ip}/stream"
        print(f"[MAIN] Mode robot fisik TANPA ROS: kamera <- {stream_desc}, perintah -> UDP {args.control_ip}:{args.esp_port}")

    cam = open_source(args.source, esp_ip=args.esp_ip, esp_url=args.stream_url,
                      ros_topic=args.image_topic, webcam_index=args.webcam)
    robot = RobotAPI(esp_ip=args.control_ip, esp_port=args.esp_port, use_ros=use_ros)
    vision = VisionEngine()
    ctrl = Controller(robot, vision)
    ctrl.source_name = cam.name

    hmi = HMIServer(ctrl, cam=cam, port=args.port).start()
    urls = hmi.urls()
    print("[HMI] Buka di browser: " + "  |  ".join(urls))
    if not args.no_browser:
        try:
            webbrowser.open(urls[0])
        except Exception:
            pass

    gui_state = {}
    window = "Eksbot2 Control Center (OpenCV)"
    if args.gui:
        cv.namedWindow(window)
        cv.setMouseCallback(window, mouse_cb_factory(ctrl, gui_state))

    last_frame_time = time.time()
    last_idle_send = 0.0
    print("[MAIN] Berjalan. Tekan Ctrl+C di terminal untuk keluar. Legenda tombol: tekan H di HMI.")

    try:
        while True:
            if use_ros and rospy.is_shutdown():
                break

            ok, frame = cam.read()
            now = time.time()
            ctrl.link_ok = bool(cam.connected)

            if ok:
                last_frame_time = now
                frame_out, tel = ctrl.update(frame)
                hmi.publish(frame_out, tel)
                if args.gui:
                    gui_state["size"] = (frame_out.shape[1], frame_out.shape[0])
                    cv.imshow(window, draw_gui_overlay(frame_out, tel))
            else:
                # Menunggu frame baru dari stream kamera:
                # Mode MANUAL tetap kirim UDP agar robot tidak lumpuh meski kamera putus/pause OTA.
                # Mode AUTO berhenti aman jika link kamera putus > 1.5s.
                if ctrl.mode == "MANUAL":
                    if now - last_idle_send > 0.05:
                        ctrl.idle()
                        last_idle_send = now
                elif now - last_frame_time > 1.5 and now - last_idle_send > 0.2:
                    ctrl.idle()
                    last_idle_send = now
                time.sleep(0.003)

            if args.gui:
                key = cv.waitKey(1) & 0xFF
                if key == 27:
                    break
                if key != 255:
                    k = key | 0x20 if 65 <= key <= 90 else key   # huruf besar -> kecil
                    if k in GUI_KEYS:
                        ctrl.press_gui(GUI_KEYS[k])
                    elif k in GUI_ACTIONS:
                        ctrl.do_action(*GUI_ACTIONS[k])
    except KeyboardInterrupt:
        pass
    finally:
        robot.stop()
        time.sleep(0.05)
        robot.stop()
        cam.release()
        hmi.stop()
        if args.gui:
            cv.destroyAllWindows()
        if use_ros:
            rospy.signal_shutdown("main.py selesai")
        print("[MAIN] Program selesai dan robot dihentikan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
