# Program Uji Kontrol Robot Langsung (Direct Wi-Fi - Tanpa Kamera)

Folder ini berisi **Program Khusus Uji Coba Pengujian Motor & Servo** secara langsung dari ESP32 Sistem Kontrol (tanpa ESP32-CAM & tanpa pemrosesan vision/kamera).

---

## 📁 Isi File
1. **`robot.ino`**: Firmware C++ untuk ESP32 Sistem Kontrol Motor & Servo. Memancarkan Wi-Fi Access Point dan mendengarkan paket UDP dari laptop. (Sebelumnya bernama `firmware_esp32_control_direct_wifi.ino`.)
2. **`main.py`**: Script Python Control Panel di Laptop untuk mengendalikan robot menggunakan keyboard WSAD, Gripper (J/K), dan Lift (U/I). (Sebelumnya bernama `test_manual_keyboard.py`.)

> **Catatan**: `robot.ino` memancarkan SSID `dimas_asoy_geboy` dengan IP `192.168.4.1`, sama dengan `firmware_esp32_cam.ino`. Jangan menyalakan keduanya bersamaan.

---

## 📌 Skema Pinout Wiring ESP32 Sistem Kontrol (sesuai `robot.ino`)

| Komponen | Nama Signal / Fungsi | Pin ESP32 |
|---|---|---|
| **Motor DC Kiri** | ENA (PWM Speed Left) | GPIO 4 |
| | IN1 (Direction 1 Left) | GPIO 16 |
| | IN2 (Direction 2 Left) | GPIO 17 |
| **Motor DC Kanan** | ENB (PWM Speed Right) | GPIO 19 |
| | IN3 (Direction 1 Right) | GPIO 21 |
| | IN4 (Direction 2 Right) | GPIO 18 |
| **Servo Gripper** | Signal Gripper Servo | GPIO 7 ⚠️ |
| **Servo Lift** | Signal Lift Servo | GPIO 3 ⚠️ |

> ⚠️ **Peringatan**: GPIO 6-11 terhubung ke SPI Flash internal (GPIO 7 dapat membuat ESP32 crash) dan GPIO 3 adalah RX0 (Serial USB). Pindahkan servo ke pin aman seperti GPIO 13, 14, 22, 23, 25, 26, 27, 32, atau 33.

---

## 🚀 Cara Menjalankan (Step-by-Step)

### Step 1: Upload Firmware ke ESP32 Sistem Kontrol
1. Buka file `robot.ino` di **Arduino IDE**.
2. Pastikan library **`ArduinoJson`** dan **`ESP32Servo`** sudah terinstall di Arduino IDE.
3. Hubungkan ESP32 Sistem Kontrol ke Laptop via kabel USB.
4. Pilih Board `ESP32 Dev Module` dan Port yang sesuai, lalu klik **Upload**.

### Step 2: Sambungkan Wi-Fi Laptop
1. Setelah dimuat, ESP32 Control akan menyalakan Wi-Fi Access Point:
   - **SSID**: `dimas_asoy_geboy` (atau `AutoStack-Control-Test`)
   - **Password**: `12345678`
   - **IP Server**: `192.168.4.1`
2. Sambungkan koneksi Wi-Fi Laptop Anda ke jaringan tersebut.

### Step 3: Jalankan Program Uji Keyboard di Laptop
Buka terminal di laptop dan jalankan:

```bash
cd /home/fathir/eksbot2/tes_manual_control
python3 main.py
```

---

## 🎮 Tombol Kontrol Keyboard

- **`W` / `S`**: Maju / Mundur
- **`A` / `D`**: Belok Kiri / Belok Kanan
- **`SPACE`**: Rem Darurat (Stop)
- **`J` / `K`**: Jepit (Gripper CLOSE 90°) / Buka (Gripper OPEN 0°)
- **`U` / `I`**: Angkat Lift (Lift UP 90°) / Turunkan Lift (Lift DOWN 0°)
- **`ESC`**: Keluar dari Program
