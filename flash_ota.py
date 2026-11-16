#!/usr/bin/env python3
"""
Eksbot2 One-Click Firmware Compiler & OTA/USB Flasher
=====================================================
Alat bantu otomatis untuk mengompilasi file .ino langsung menjadi .bin
dan mengunggahnya secara nirkabel (OTA) ke ESP32 melalui Wi-Fi, atau via kabel USB (--usb).

Penggunaan Terminal:
  python3 flash_ota.py control         # Kompilasi .ino & Flash ESP32-Control via Wi-Fi (192.168.4.10)
  python3 flash_ota.py cam             # Kompilasi .ino & Flash ESP32-CAM via Wi-Fi (192.168.4.1)
  python3 flash_ota.py control --usb   # Kompilasi .ino & Flash ESP32-Control via Kabel USB
  python3 flash_ota.py cam --usb       # Kompilasi .ino & Flash ESP32-CAM via Kabel USB
  python3 flash_ota.py nano            # Kompilasi .ino & Flash Arduino Nano via USB

Tidak perlu lagi buka Arduino IDE atau export .bin manual!
Cukup edit file .ino, lalu jalankan script ini.
"""

import glob
import sys
import os
import socket
import subprocess
import time
import urllib.parse
import urllib.request
import urllib.error

ARDUINO_CLI = "/home/fathir/arduino-ide_2.3.10_Linux_64bit/resources/app/lib/backend/resources/arduino-cli"
LIB_PATH = "/home/fathir/.arduino15/libraries"
WORKSPACE = os.path.dirname(os.path.abspath(__file__))

TARGETS = {
    "control": {
        "name": "ESP32 Sistem Kontrol (Motor + Nano Aktuator)",
        "sketch": os.path.join(WORKSPACE, "catkin_ws/src/eksbot_simulation/firmware/firmware_esp32_control"),
        "fqbn": "esp32:esp32:esp32",
        "bin_rel": "build/esp32.esp32.esp32/firmware_esp32_control.ino.bin",
        "ota_urls": ["http://192.168.4.10/update"]
    },
    "cam": {
        "name": "ESP32-CAM (Kamera & SoftAP Utama)",
        "sketch": os.path.join(WORKSPACE, "catkin_ws/src/eksbot_simulation/firmware/firmware_esp32_cam"),
        "fqbn": "esp32:esp32:esp32wrover",
        "bin_rel": "build/esp32.esp32.esp32wrover/firmware_esp32_cam.ino.bin",
        "ota_urls": ["http://192.168.4.1/update"]
    },
    "nano": {
        "name": "Arduino Nano Sub-Kontroler Aktuator",
        "sketch": os.path.join(WORKSPACE, "catkin_ws/src/eksbot_simulation/firmware/firmware_nano_actuator"),
        "fqbn": "arduino:avr:nano",
        "bin_rel": "build/arduino.avr.nano/firmware_nano_actuator.ino.hex",
        "is_usb": True
    }
}

def compile_sketch(target_key):
    cfg = TARGETS[target_key]
    print(f"\n[1/2] ⚙️  Mengompilasi file .ino untuk {cfg['name']}...")
    cmd = [
        ARDUINO_CLI, "compile",
        "--export-binaries",
        "--fqbn", cfg["fqbn"],
        "--libraries", LIB_PATH,
        cfg["sketch"]
    ]
    t0 = time.time()
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print("\n❌ GAGAL KOMPILASI:")
        print(res.stderr)
        return False, None

    elapsed = time.time() - t0
    
    # Prioritaskan path biner yang sesuai dengan fqbn target (cfg["bin_rel"])
    found_bin = None
    expected_bin = os.path.join(cfg["sketch"], cfg["bin_rel"])
    if os.path.exists(expected_bin):
        found_bin = expected_bin
    else:
        build_dir = os.path.join(cfg["sketch"], "build")
        if os.path.exists(build_dir):
            for root, dirs, files in os.walk(build_dir):
                for f in sorted(files):
                    if cfg.get("is_usb"):
                        if f.endswith(".hex") and "bootloader" not in f:
                            found_bin = os.path.join(root, f)
                            break
                    else:
                        if f.endswith(".ino.bin") and not any(k in f for k in ["bootloader", "partitions", "merged"]):
                            found_bin = os.path.join(root, f)
                            break
                if found_bin:
                    break

    if not found_bin or not os.path.exists(found_bin):
        print(f"\n❌ File biner hasil kompilasi tidak ditemukan di {build_dir}")
        return False, None

    size_kb = os.path.getsize(found_bin) / 1024.0
    print(f"✅ Kompilasi .ino Sukses ({elapsed:.1f}s) | File: {os.path.basename(found_bin)} ({size_kb:.1f} KB)")
    return True, found_bin

def _tcp_reachable(url, timeout=3.0):
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, None
    except Exception as e:
        return False, e

def upload_ota(bin_path, urls, target_key):
    with open(bin_path, "rb") as f:
        bin_data = f.read()

    def do_post(target_url):
        req = urllib.request.Request(
            target_url,
            data=bin_data,
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": str(len(bin_data))
            },
            method="POST"
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=30) as resp:
            return resp.status, resp.read().decode('utf-8', errors='ignore')

    last_err = None
    for idx, url in enumerate(urls):
        print(f"\n[2/2] 📡 Mengunggah biner ke {url} via Wi-Fi...")
        ok_tcp, tcp_err = _tcp_reachable(url, timeout=3.0)
        if not ok_tcp:
            last_err = tcp_err
            if idx + 1 < len(urls):
                print(f"⚠️  Port {url} tidak aktif ({tcp_err}), mencoba port cadangan...")
                continue
            break

        try:
            do_post(url)
            print(f"🎉 SUKSES! Firmware berhasil di-flash ke {url}.")
            print("   ESP32 sedang me-reboot otomatis (tunggu 3-5 detik).")
            return True
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
            if idx + 1 < len(urls):
                print(f"⚠️  Gagal melalui {url} ({e}), mencoba URL cadangan...")

    primary_ip = urllib.parse.urlparse(urls[0]).hostname
    print(f"\n❌ GAGAL UPLOAD OTA ke {primary_ip}: {last_err}")
    print("💡 Tips Pemecahan Masalah:")
    print("   1. Pastikan laptop terhubung ke Wi-Fi 'dimas-cam' (atau 'dimas-control' jika hanya flash Control).")
    if target_key == "cam":
        print("   2. Jika menjalankan dari terminal manual, pause/matikan main.py dulu agar port 80 /stream bebas.")
        print("   3. Pastikan ESP32-CAM menyala dan memancarkan Wi-Fi 'dimas-cam' (192.168.4.1).")
        print("      -> Jika belum konek atau ter-flash firmware keliru, colok USB & jalankan: python3 flash_ota.py cam --usb")
    else:
        print("   2. Pastikan ESP32-Control sudah menyala dan terhubung ke Wi-Fi 'dimas-cam' (192.168.4.10).")
        print("      -> Atau konek ke Wi-Fi 'dimas-control' dan buka http://192.168.5.1/update di browser.")
    print(f"   4. Coba tes ping: ping {primary_ip}")
    return False

def upload_usb(cfg, target_key, explicit_port=None):
    print(f"\n[2/2] 🔌 Mengunggah ke {cfg['name']} via Kabel USB...")
    if explicit_port:
        found_port = explicit_port
    else:
        candidates = sorted(glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))
        found_port = candidates[0] if candidates else None
    if not found_port or not os.path.exists(found_port):
        print("❌ Port USB tidak ditemukan (/dev/ttyUSB0 atau /dev/ttyACM0)! Pastikan kabel data terpasang.")
        return False

    print(f"   Menggunakan port serial: {found_port}")
    cmd = [ARDUINO_CLI, "upload", "-p", found_port, "--fqbn", cfg["fqbn"], cfg["sketch"]]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0:
        print(f"🎉 SUKSES! Firmware {cfg['name']} berhasil di-flash via {found_port}.")
        return True
    if target_key == "nano":
        cmd_old = [ARDUINO_CLI, "upload", "-p", found_port, "--fqbn", "arduino:avr:nano:cpu=atmega328old", cfg["sketch"]]
        res2 = subprocess.run(cmd_old, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res2.returncode == 0:
            print(f"🎉 SUKSES! Firmware Arduino Nano (Old Bootloader) berhasil di-flash via {found_port}.")
            return True
        print(f"❌ Gagal upload ke Nano: {(res2.stderr or res.stderr).strip()}")
        return False
    print(f"❌ Gagal upload USB ke {cfg['name']}: {(res.stderr or res.stdout).strip()}")
    return False

def main():
    if len(sys.argv) < 2 or sys.argv[1].lower() in ["-h", "--help"]:
        print(__doc__)
        print("Target yang tersedia:")
        print("  control  -> ESP32 Kontrol Motor & Nano (Wi-Fi OTA, atau tambahkan --usb)")
        print("  cam      -> ESP32-CAM Streamer (Wi-Fi OTA, atau tambahkan --usb)")
        print("  nano     -> Arduino Nano Aktuator (USB)")
        return

    args = sys.argv[1:]
    target = args[0].lower()
    if target not in TARGETS:
        print(f"❌ Target '{target}' tidak dikenal. Pilih salah satu: control, cam, nano")
        sys.exit(1)

    use_usb = "--usb" in args
    explicit_port = None
    explicit_ip = None
    for i, a in enumerate(args):
        if a == "--port" and i + 1 < len(args):
            explicit_port = args[i + 1]
        elif a == "--ip" and i + 1 < len(args):
            explicit_ip = args[i + 1]
        elif a.startswith("/dev/tty"):
            explicit_port = a

    ok, bin_path = compile_sketch(target)
    if not ok:
        sys.exit(1)

    cfg = TARGETS[target]
    if cfg.get("is_usb") or use_usb:
        ok_up = upload_usb(cfg, target, explicit_port)
    else:
        ota_urls = [f"http://{explicit_ip}/update"] if explicit_ip else cfg["ota_urls"]
        ok_up = upload_ota(bin_path, ota_urls, target)

    if not ok_up:
        sys.exit(1)

if __name__ == "__main__":
    main()

