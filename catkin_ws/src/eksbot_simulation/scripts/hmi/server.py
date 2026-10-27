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


class HMIServer:
    def __init__(self, controller, host="0.0.0.0", port=8000, max_port_tries=10):
        self.controller = controller
        self.hub = FrameHub()
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
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()

    def publish(self, frame):
        self.hub.publish(frame)

    def urls(self):
        urls = [f"http://localhost:{self.port}"]
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
                if path == "/api/health":
                    t = server.controller.telemetry()
                    return self._send(200, {
                        "uptime_s": round(time.time() - server.started, 1),
                        "link": t["link"], "source": t["source"], "fps": t["fps"],
                        "mode": t["mode"], "phase": t["phase"],
                    })
                self._send(404, {"error": "not found"})

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
