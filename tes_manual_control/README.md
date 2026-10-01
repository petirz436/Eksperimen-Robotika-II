# Program Uji Kontrol Robot Langsung (Direct Wi-Fi - Tanpa Kamera)

Folder ini berisi **Program Khusus Uji Coba Pengujian Motor & Servo** secara langsung dari ESP32 Sistem Kontrol (tanpa ESP32-CAM & tanpa pemrosesan vision/kamera).

---

## 📁 Isi File
1. **`firmware_esp32_control_direct_wifi.ino`**: Firmware C++ untuk ESP32 Sistem Kontrol Motor & Servo. Memancarkan Wi-Fi Access Point dan mendengarkan paket UDP dari laptop.
2. **`test_manual_keyboard.py`**: Script Python GUI Control Panel di Laptop untuk mengendalikan robot menggunakan keyboard WSAD, Gripper (J/K), dan Lift (U/I).

---

## 📌 Skema Pinout Wiring ESP32 Sistem Kontrol

| Komponen | Nama Signal / Fungsi | Pin ESP32 |
|---|---|---|
| **Motor DC Kiri** | ENA (PWM Speed Left) | GPIO 12 |
| | IN1 (Direction 1 Left) | GPIO 14 |
| | IN2 (Direction 2 Left) | GPIO 27 |
| **Motor DC Kanan** | ENB (PWM Speed Right) | GPIO 13 |
| | IN3 (Direction 1 Right) | GPIO 26 |
| | IN4 (Direction 2 Right) | GPIO 25 |
| **Servo Gripper** | Signal Gripper Servo | GPIO 18 |
| **Servo Lift** | Signal Lift Servo | GPIO 19 |

---

## 🚀 Cara Menjalankan (Step-by-Step)

### Step 1: Upload Firmware ke ESP32 Sistem Kontrol
1. Buka file `firmware_esp32_control_direct_wifi.ino` di **Arduino IDE**.
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
python3 test_manual_keyboard.py
```

---

## 🎮 Tombol Kontrol Keyboard

- **`W` / `S`**: Maju / Mundur
- **`A` / `D`**: Belok Kiri / Belok Kanan
- **`SPACE`**: Rem Darurat (Stop)
- **`J` / `K`**: Jepit (Gripper CLOSE 90°) / Buka (Gripper OPEN 0°)
- **`U` / `I`**: Angkat Lift (Lift UP 90°) / Turunkan Lift (Lift DOWN 0°)
- **`ESC`**: Keluar dari Program
