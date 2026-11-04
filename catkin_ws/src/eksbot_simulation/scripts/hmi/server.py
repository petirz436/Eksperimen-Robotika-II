#!/usr/bin/env python3
"""
Eksbot2 HMI Web Server (hmi/server.py)
--------------------------------------
Server HTTP berbasis library standar Python (tanpa Flask) untuk HMI pilot di browser laptop.

Endpoint:
  GET  /               -> halaman HMI (index.html)
  GET  /stream.mjpg    -> video MJPEG (frame kamera BERSIH; HUD digambar di browser)
  GET  /api/state      -> telemetri JSON (dipolling browser ~10 Hz)
  GET  /api/hsv        -> range threshold warna HSV untuk kalibrasi
  GET  /api/health     -> status singkat untuk diagnosa developer
  POST /api/keys       -> {"codes": ["KeyW", ...]} tombol gerak yang ditahan (heartbeat)
  POST /api/action     -> {"name": "...", "value": ...}
  POST /api/lock       -> {"x": 0..1, "y": 0..1} klik target pada video
  POST /api/crosshair  -> {"style","color","size","gap","thickness","dx","dy","visible"}
  POST /api/hsv        -> set batas threshold HSV real-time tanpa restart
"""

import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2 as cv

WEB_DIR = os.path.dirname(os.path.abspath(__file__))


class FrameHub:
    """Menyimpan JPEG terbaru dan membangunkan klien stream saat ada frame baru."""

    def __init__(self, quality=80):
        self.quality = quality
        self._cond = threading.Condition()
        self._jpg = None
        self._seq = 0

    def publish(self, frame):
        ok, buf = cv.imencode(".jpg", frame, [cv.IMWRITE_JPEG_QUALITY, self.quality])
        if not ok:
            return
        with self._cond:
            self._jpg = buf.tobytes()
            self._seq += 1
            self._cond.notify_all()

    def wait_next(self, last_seq, timeout=1.0):
        with self._cond:
            if self._seq == last_seq:
                self._cond.wait(timeout)
            return self._seq, self._jpg


RECORDINGS_DIR = os.path.join(WEB_DIR, "recordings")


class VideoRecorder:
    """Perekam video sisi server (OpenCV VideoWriter) untuk flight recording tanpa membebani browser."""

    def __init__(self, record_dir=RECORDINGS_DIR):
        self.record_dir = record_dir
        os.makedirs(self.record_dir, exist_ok=True)
        self.is_recording = False
        self.writer = None
        self.filename = None
        self.filepath = None
        self.start_time = 0.0
        self.frames_written = 0
        self.frame_size = None
        self._lock = threading.Lock()

    def start(self, frame_size=(320, 240), fps=20.0):
        with self._lock:
            if self.is_recording:
                return self.filename
            ts = time.strftime("%Y%m%d_%H%M%S")
            self.filename = f"eksbot2_flight_{ts}.mp4"
            self.filepath = os.path.join(self.record_dir, self.filename)
            self.frame_size = frame_size
            fourcc = cv.VideoWriter_fourcc(*"mp4v")
            self.writer = cv.VideoWriter(self.filepath, fourcc, float(fps), frame_size)
            self.start_time = time.time()
            self.frames_written = 0
            self.is_recording = True
            print(f"[RECORDER] Mulai merekam video: {self.filepath} ({frame_size[0]}x{frame_size[1]} @ {fps:.1f}fps)")
            return self.filename

    def write(self, frame, telemetry=None):
        with self._lock:
            if not self.is_recording:
                return
            h, w = frame.shape[:2]
            if self.writer is None or (w, h) != self.frame_size:
                if self.writer:
                    self.writer.release()
                self.frame_size = (w, h)
                fourcc = cv.VideoWriter_fourcc(*"mp4v")
                self.writer = cv.VideoWriter(self.filepath, fourcc, 20.0, (w, h))

            frame_to_write = frame.copy()
            if telemetry:
                mode = telemetry.get("mode", "MANUAL")
                phase = telemetry.get("phase", "IDLE")
                spd = round(telemetry.get("speed_scale", 1.0) * 100)
                stamp = f"{mode} | {phase} | SPD {spd}% | {time.strftime('%H:%M:%S')}"
                cv.putText(frame_to_write, stamp, (8, h - 8), cv.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1, cv.LINE_AA)

            self.writer.write(frame_to_write)
            self.frames_written += 1

    def stop(self):
        with self._lock:
            if not self.is_recording:
                return None
            self.is_recording = False
            if self.writer:
                self.writer.release()
                self.writer = None
            dur = round(time.time() - self.start_time, 1)
            print(f"[RECORDER] Selesai merekam: {self.filename} ({self.frames_written} frame, {dur}s)")
            return {
                "filename": self.filename,
                "filepath": self.filepath,
                "duration_s": dur,
                "frames": self.frames_written,
            }


class HMIServer:
    def __init__(self, controller, host="0.0.0.0", port=8000, max_port_tries=10):
        self.controller = controller
        self.hub = FrameHub()
        self.recorder = VideoRecorder(RECORDINGS_DIR)
        self.started = time.time()
        self.httpd = None
        self.port = None

        handler = self._make_handler()
        last_err = None
        for p in range(port, port + max_port_tries):
            try:
                self.httpd = ThreadingHTTPServer((host, p), handler)
                self.httpd.daemon_threads = True
                self.port = p
                break
            except OSError as e:
                last_err = e
        if self.httpd is None:
            raise RuntimeError(f"Tidak ada port kosong {port}-{port + max_port_tries - 1}: {last_err}")

        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self.recorder.stop()
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()

    def publish(self, frame, telemetry=None):
        self.hub.publish(frame)
        if self.recorder.is_recording:
            self.recorder.write(frame, telemetry)

    def urls(self):
        urls = [f"http://localhost:{self.port}"]
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("192.168.4.10", 80))
            except Exception:
                s.connect(("192.168.4.1", 80))
            ip = s.getsockname()[0]
            s.close()
            if not ip.startswith("127."):
                urls.append(f"http://{ip}:{self.port}")
        except Exception:
            pass
        return urls

    # ------------------------------------------------------------------
    def _make_handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt, *args):
                pass   # Jangan banjiri terminal pilot

            # ---------------- helpers ----------------
            def _send(self, code, body, ctype="application/json"):
                if isinstance(body, (dict, list)):
                    body = json.dumps(body).encode()
                elif isinstance(body, str):
                    body = body.encode()
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _json_body(self):
                n = int(self.headers.get("Content-Length") or 0)
                if n <= 0 or n > 65536:
                    return {}
                try:
                    return json.loads(self.rfile.read(n) or b"{}")
                except Exception:
                    return {}

            # ---------------- GET ----------------
            def do_GET(self):
                path = self.path.split("?")[0]
                if path in ("/", "/index.html"):
                    return self._static("index.html", "text/html; charset=utf-8")
                if path == "/stream.mjpg":
                    return self._stream()
                if path == "/api/state":
                    return self._send(200, server.controller.telemetry())
                if path == "/api/hsv":
                    if hasattr(server.controller, "vision") and server.controller.vision:
                        return self._send(200, server.controller.vision.get_hsv_ranges())
                    return self._send(200, {"active": "RED", "ranges": {}})
                if path == "/api/ota_info":
                    return self._send(200, {
                        "targets": [
                            {
                                "id": "esp32_cam",
                                "name": "ESP32-CAM",
                                "role": "Kamera & Vision Bridge",
                                "ip": "192.168.4.10",
                                "port": 80,
                                "update_url": "http://192.168.4.10/update",
                                "stream_url": "http://192.168.4.10/stream"
                            },
                            {
                                "id": "esp32_control",
                                "name": "ESP32-Control",
                                "role": "Sistem Motor & Servo (AP)",
                                "ip": "192.168.4.1",
                                "port": 80,
                                "update_url": "http://192.168.4.1/update",
                                "status_url": "http://192.168.4.1/"
                            }
                        ]
                    })
                if path.startswith("/recordings/"):
                    fname = os.path.basename(path)
                    fpath = os.path.join(RECORDINGS_DIR, fname)
                    if os.path.isfile(fpath):
                        return self._send_file(fpath, "video/mp4", fname)
                    return self._send(404, {"error": "file not found"})
                if path == "/api/record/status":
                    return self._send(200, {
                        "recording": server.recorder.is_recording,
                        "file": server.recorder.filename,
                        "duration_s": round(time.time() - server.recorder.start_time, 1) if server.recorder.is_recording else 0.0,
                        "frames": server.recorder.frames_written,
                    })
                if path == "/api/health":
                    t = server.controller.telemetry()
                    return self._send(200, {
                        "uptime_s": round(time.time() - server.started, 1),
                        "link": t["link"], "source": t["source"], "fps": t["fps"],
                        "mode": t["mode"], "phase": t["phase"],
                    })
                self._send(404, {"error": "not found"})

            def _send_file(self, filepath, ctype, download_name=None):
                try:
                    size = os.path.getsize(filepath)
                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(size))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    if download_name:
                        self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    with open(filepath, "rb") as f:
                        while True:
                            chunk = f.read(65536)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                except Exception:
                    pass

            def _static(self, name, ctype):
                try:
                    with open(os.path.join(WEB_DIR, name), "rb") as f:
                        data = f.read()
                except OSError:
                    return self._send(500, f"File HMI {name} tidak ditemukan di {WEB_DIR}", "text/plain")
                self._send(200, data, ctype)

            def _stream(self):
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                seq = -1
                try:
                    while True:
                        new_seq, jpg = server.hub.wait_next(seq, timeout=1.0)
                        if jpg is None or new_seq == seq:
                            continue
                        seq = new_seq
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                         + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass
                self.close_connection = True

            # ---------------- POST ----------------
            def do_POST(self):
                path = self.path.split("?")[0]
                body = self._json_body()
                ctrl = server.controller
                if path == "/api/keys":
                    codes = body.get("codes", [])
                    ctrl.set_keys(codes if isinstance(codes, list) else [])
                    return self._send(200, {"ok": True})
                if path == "/api/action":
                    ok = ctrl.do_action(str(body.get("name", "")), body.get("value"))
                    return self._send(200 if ok else 400, {"ok": ok})
                if path == "/api/record":
                    action = body.get("action", "toggle")
                    if action == "start":
                        t = ctrl.telemetry() if hasattr(ctrl, "telemetry") else {}
                        fps = float(t.get("fps", 20.0) or 20.0)
                        fw, fh = t.get("frame", (320, 240))
                        fname = server.recorder.start(frame_size=(fw, fh), fps=fps)
                        return self._send(200, {"ok": True, "recording": True, "file": fname})
                    elif action == "stop":
                        res = server.recorder.stop()
                        if res:
                            return self._send(200, {
                                "ok": True, "recording": False,
                                "file": res["filename"],
                                "duration_s": res["duration_s"],
                                "frames": res["frames"],
                                "download_url": f"/recordings/{res['filename']}"
                            })
                        return self._send(200, {"ok": True, "recording": False})
                    elif action == "toggle":
                        if server.recorder.is_recording:
                            res = server.recorder.stop()
                            return self._send(200, {
                                "ok": True, "recording": False,
                                "file": res["filename"] if res else None,
                                "download_url": f"/recordings/{res['filename']}" if res else None
                            })
                        else:
                            t = ctrl.telemetry() if hasattr(ctrl, "telemetry") else {}
                            fps = float(t.get("fps", 20.0) or 20.0)
                            fw, fh = t.get("frame", (320, 240))
                            fname = server.recorder.start(frame_size=(fw, fh), fps=fps)
                            return self._send(200, {"ok": True, "recording": True, "file": fname})
                if path == "/api/lock":
                    try:
                        ctrl.request_lock(float(body["x"]), float(body["y"]))
                    except (KeyError, TypeError, ValueError):
                        return self._send(400, {"ok": False})
                    return self._send(200, {"ok": True})
                if path == "/api/crosshair":
                    ctrl.set_crosshair(body)
                    return self._send(200, {"ok": True, "crosshair": ctrl.crosshair})
                if path == "/api/hsv":
                    if not hasattr(ctrl, "vision") or not ctrl.vision:
                        return self._send(400, {"ok": False})
                    if body.get("reset"):
                        ctrl.vision.reset_hsv_presets()
                        return self._send(200, ctrl.vision.get_hsv_ranges())
                    c = body.get("color")
                    if c:
                        ok = ctrl.vision.set_hsv_range(
                            c, body.get("h_min", 0), body.get("h_max", 179),
                            body.get("s_min", 0), body.get("s_max", 255),
                            body.get("v_min", 0), body.get("v_max", 255)
                        )
                        return self._send(200 if ok else 400, {"ok": ok, "data": ctrl.vision.get_hsv_ranges()})
                    return self._send(400, {"ok": False})
                self._send(404, {"error": "not found"})

        return Handler
