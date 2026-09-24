# AutoStack Challenge - Gazebo Simulation & ROS Vision Target ESP32

Dokumentasi lengkap proyek simulasi Gazebo, robot dummy (differential drive + gripper + ESP32-CAM), objek kubus 3 warna, pemrosesan vision (*Computer Vision*) di laptop, dan arsitektur kontroler terdistribusi menggunakan **ROS Noetic** dan **ESP32**.

---

## 📋 Daftar Isi
1. [Penjelasan Proyek & Arsitektur](#1-penjelasan-proyek--arsitektur)
2. [Spesifikasi Teknis](#2-spesifikasi-teknis)
3. [Struktur Direktori Workspace](#3-struktur-direktori-workspace)
4. [Persiapan Lingkungan (Network Fix & Environment Setup)](#4-persiapan-lingkungan-network-fix--environment-setup)
5. [Cara Menjalankan (Running Guide)](#5-cara-menjalankan-running-guide)
   - [A. Menjalankan Simulasi Gazebo & Vision (Simulasi)](#a-menjalankan-simulasi-gazebo--vision-simulasi)
   - [B. Menjalankan Pada Robot Fisik (ESP32-CAM & ESP32)](#b-menjalankan-pada-robot-fisik-esp32-cam--esp32)
6. [Panduan Tuning Program (Tuning Guide)](#6-panduan-tuning-program-tuning-guide)
   - [A. Tuning Threshold Warna HSV (Merah, Hijau, Biru)](#a-tuning-threshold-warna-hsv-merah-hijau-biru)
   - [B. Tuning Exponential Moving Average (EMA) & Deadzone](#b-tuning-exponential-moving-average-ema--deadzone)
   - [C. Tuning Pengendali Kecepatan Robot (P-Controller /cmd_vel)](#c-tuning-pengendali-kecepatan-robot-p-controller-cmd_vel)
   - [D. Tuning ESP32 (PWM Motor & Sudut Servo Gripper)](#d-tuning-esp32-pwm-motor--sudut-servo-gripper)
7. [Histori Progres & Log AI (`PROGRESS_REPORT.md`)](#7-histori-progres--log-ai-progress_reportmd)
8. [Troubleshooting & Perbaikan Masalah Umum](#8-troubleshooting--perbaikan-masalah-umum)

---

## 1. Penjelasan Proyek & Arsitektur

Proyek ini dirancang untuk menyelesaikan tantangan **AutoStack Challenge**, di mana sebuah robot bertugas mendeteksi, mendekati, mengambil, dan menumpuk kubus berwarna (Merah, Hijau, Biru) di atas Stacking Pad arena.

### Arsitektur Sistem Terdistribusi (Laptop + ESP32-CAM + ESP32):
```
### Arsitektur Sistem Terdistribusi Modular (Laptop + ESP32-CAM + ESP32 Kontroler):
```
+-----------------------------------------------------------------------------------+
|                                   LAPTOP                                          |
|                                                                                   |
|  +--------------------+        +---------------+       +-----------------------+  |
|  | Gazebo / ESP32-CAM | -----> |   vision.py   | ----> |        main.py        |  |
|  | Image Stream       |        | (RGB Switcher)|       | (Manual WSAD / Auto)  |  |
|  +--------------------+        +---------------+       +-----------+-----------+  |
|                                                                    |              |
|                                                                    v              |
|                                                        +-----------------------+  |
|                                                        |      robot_api.py     |  |
|                                                        | (/cmd_vel / UDP ESP)  |  |
|                                                        +-----------+-----------+  |
+--------------------------------------------------------------------|--------------+
                                                                     | (Wi-Fi UDP)
                                                                     v
+-----------------------------------------------------------------------------------+
|                                   ROBOT FISIK                                     |
|                                                                                   |
|  +---------------------+      (Kabel UART2)       +----------------------------+  |
|  | ESP32-CAM           | -----------------------> | ESP32 SISTEM KONTROL       |  |
|  | (SoftAP + Streamer) |                          | (Driver L298N & Servo)     |  |
|  +---------------------+                          +----------------------------+  |
+-----------------------------------------------------------------------------------+
```

1. **Laptop (Pusat Komputasi Vision, Kontrol Manual WSAD & Autonavigasi)**:
   - `vision.py`: Modul OpenCV pengolahan citra RGB (Red, Green, Blue) dengan *Color Switcher* (Tombol `1`: Red, `2`: Green, `3`: Blue).
   - `robot_api.py`: Modul antarmuka pengiriman perintah gerak & servo ke ROS (`/cmd_vel`) atau Wi-Fi UDP Socket.
   - `main.py`: Aplikasi utama dengan dukungan **Kontrol Manual Keyboard (WSAD, Gripper J/K, Lift U/I)** serta **Mode Vision Auto Navigasi**.
2. **ESP32-CAM (Wi-Fi SoftAP & Bridge)**:
   - `firmware_esp32_cam.ino`: Bertindak sebagai Wi-Fi Access Point (`SSID: AutoStack-ESP-CAM`, IP: `192.168.4.1`), streamer MJPEG `/stream`, dan penerus data kontrol via **Kabel Serial UART2 (TX2/RX2)**.
3. **ESP32 Sistem Kontrol (Aktuator Motor & Servo)**:
   - `firmware_esp32_control.ino`: Membaca instruksi serial kabel dari ESP32-CAM, mengendalikan PWM Motor DC (L298N/BTS7960) dan Servo Gripper/Lift.

---

## 3. Struktur Direktori Workspace

```
eksbot2/
├── README.md                           # Dokumentasi utama proyek (File Ini)
├── PROGRESS_REPORT.md                  # Laporan progres & histori log AI
├── setup_env.sh                        # Script perbaikan/setup environment ROS IP
├── catkin_ws/
│   └── src/
│       └── eksbot_simulation/
│           ├── CMakeLists.txt
│           ├── package.xml
│           ├── launch/
│           │   ├── arena_simulation.launch   # Membuka Gazebo + Arena + Robot + Kubus
│           │   ├── vision_control.launch     # Membuka Node ROS Vision Target Lama
│           │   └── modular_control.launch    # Launch Aplikasi Modular Utama (main.py)
│           ├── worlds/
│           │   └── autostack_arena.world     # Definisi dunia simulasi
│           ├── models/
│           │   ├── arena_ground/             # Tekstur & model spanduk arena
│           │   ├── cube_red/                 # SDF Kubus Merah
│           │   ├── cube_green/               # SDF Kubus Hijau
│           │   └── cube_blue/                # SDF Kubus Biru
│           ├── urdf/
│           │   └── dummy_robot.urdf.xacro    # URDF Robot Dummy & Sensor
│           └── scripts/
│               ├── main.py                   # Aplikasi Utama (Manual WSAD & Auto Navigasi)
│               ├── vision.py                 # Core Vision Engine RGB & CSRT Tracker
│               ├── robot_api.py              # Robot Interface API (ROS / Wi-Fi UDP)
│               ├── firmware_esp32_cam.ino    # Firmware ESP32-CAM SoftAP & UART Bridge
│               ├── firmware_esp32_control.ino# Firmware ESP32 Sistem Kontrol Motor/Servo
│               ├── visionTarget.py           # Single-script Vision (Legacy)
│               └── esp32_firmware_example.ino# ROSSerial Firmware (Legacy)
└── spesifikasi/                              # Gambar acuan spesifikasi
```

---

## 4. Persiapan Lingkungan (Network Fix & Environment Setup)

Jika Anda menemui error saat `roslaunch`:
```
RLException: Unable to contact my own server at [http://192.168.0.112:38651/]
```
Hal ini terjadi karena variabel lingkungan `ROS_IP` atau `ROS_MASTER_URI` di `~/.bashrc` di-set ke alamat IP statis lama yang tidak lagi aktif pada jaringan Wi-Fi Anda.

### Solusi Cepat:
Jalankan script `setup_env.sh` sebelum mengeksekusi `roslaunch`:
```bash
cd /home/fathir/eksbot2
source setup_env.sh
```

---

## 5. Cara Menjalankan (Running Guide)

### A. Menjalankan Simulasi Gazebo & Control Center (Simulasi)

1. **Buka Terminal 1 - Jalankan Simulasi Gazebo**:
   ```bash
   cd /home/fathir/eksbot2
   source setup_env.sh
   roslaunch eksbot_simulation arena_simulation.launch
   ```

2. **Buka Terminal 2 - Jalankan Aplikasi Modular Utama (`main.py`)**:
   ```bash
   cd /home/fathir/eksbot2
   source setup_env.sh
   roslaunch eksbot_simulation modular_control.launch
   # ATAU jalankan script langsung:
   # python3 catkin_ws/src/eksbot_simulation/scripts/main.py
   ```

3. **Cara Mengontrol Robot via Keyboard & Vision**:
   - **`M`**: Perpindahan Mode antara **MANUAL WSAD** $\leftrightarrow$ **AUTO VISION NAVIGASI**.
   - **`W` / `S`**: Maju / Mundur (Mode Manual).
   - **`A` / `D`**: Belok Kiri / Belok Kanan (Mode Manual).
   - **`SPACE`**: Stop / Rem Darurat.
   - **`J` / `K`**: Jepit Gripper (Close) / Buka Gripper (Open).
   - **`U` / `I`**: Angkat Lift (Up) / Turunkan Lift (Down).
   - **`1` / `2` / `3`**: Switch Target Warna Vision (`1`: Merah, `2`: Hijau, `3`: Biru).
   - **`R`**: Reset Lock Target Vision.
   - **`ESC`**: Keluar dari Aplikasi.

---

### B. Menjalankan Pada Robot Fisik (ESP32-CAM & ESP32 Sistem Kontrol)

1. **Flash Firmware ESP32-CAM**:
   - Buka `catkin_ws/src/eksbot_simulation/scripts/firmware_esp32_cam.ino` di Arduino IDE.
   - Flash ke ESP32-CAM. Board akan memancarkan Wi-Fi Access Point `AutoStack-ESP-CAM` (Pass: `12345678`).

2. **Flash Firmware ESP32 Sistem Kontrol**:
   - Buka `catkin_ws/src/eksbot_simulation/scripts/firmware_esp32_control.ino` di Arduino IDE.
   - Hubungkan kabel Hardware Serial UART2:
     - **ESP32-CAM Pin 17 (TX2)** $\rightarrow$ **ESP32 Control Pin 16 (RX2)**.
     - **ESP32-CAM Pin 16 (RX2)** $\rightarrow$ **ESP32 Control Pin 17 (TX2)**.
     - **GND** ESP32-CAM terhubung ke **GND** ESP32 Control.
   - Flash ke ESP32 Sistem Kontrol.

3. **Jalankan Aplikasi Laptop**:
   - Hubungkan Wi-Fi Laptop ke `AutoStack-ESP-CAM`.
   - Jalankan `main.py`:
     ```bash
     python3 catkin_ws/src/eksbot_simulation/scripts/main.py
     ```

---

## 6. Panduan Tuning Program (Tuning Guide)

### A. Tuning Threshold Warna HSV (Merah, Hijau, Biru)
File Target: [visionTarget.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/visionTarget.py#L25-L35)

Jika pencahayaan ruangan/kamera berubah, sesuaikan rentang Hue (H: 0-180), Saturation (S: 0-255), Value (V: 0-255):

```python
# --- KUBUS MERAH (Red) ---
HSV_LOWER = np.array([0, 100, 100])
HSV_UPPER = np.array([10, 255, 255])
HSV_LOWER2 = np.array([170, 100, 100]) # Merah membungkus rentang Hue 170-180
HSV_UPPER2 = np.array([180, 255, 255])

# --- KUBUS HIJAU (Green) ---
# HSV_LOWER = np.array([35, 100, 100])
# HSV_UPPER = np.array([85, 255, 255])

# --- KUBUS BIRU (Blue) ---
# HSV_LOWER = np.array([90, 100, 100])
# HSV_UPPER = np.array([130, 255, 255])
```
> **Tips Tuning**: Jika kontur bayangan terlalu banyak terdeteksi, naikkan nilai minimal Saturation (`S`) dan Value (`V`) ke 120-150.

---

### B. Tuning Exponential Moving Average (EMA) & Deadzone
File Target: [visionTarget.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/visionTarget.py#L12-L17)

```python
ALPHA = 0.35            # Faktor smoothing EMA (0.1 - 0.9)
DEADZONE = 20           # Pixel deadzone error (5 - 30 px)
MIN_CONTOUR_AREA = 500  # Luas piksel minimal kontur terdeteksi
```

- **`ALPHA` (Smoothing)**:
  - Nilai lebih kecil (`0.1 - 0.2`): Hasil posisi target sangat halus/smooth, tetapi memiliki keterlambatan (*lag*).
  - Nilai lebih besar (`0.5 - 0.8`): Respons sangat cepat, namun pergerakan dapat bergetar jika piksel berfluktuasi.
- **`DEADZONE`**:
  - Apabila galat posisi target $|CX_{target} - CX_{center}| < \text{DEADZONE}$, error akan di-nol-kan agar robot tidak bergoyang saat target sudah berada tepat di tengah.

---

### C. Tuning Pengendali Kecepatan Robot (P-Controller `/cmd_vel`)
File Target: [visionTarget.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/visionTarget.py#L225-L235)

```python
# Angular Velocity (Kecepatan Belok / Steering)
twist_msg.angular.z = -1.2 * norm_x

# Linear Velocity (Kecepatan Maju)
if abs(norm_x) < 0.3:
    twist_msg.linear.x = 0.15  # Kecepatan saat target di tengah
else:
    twist_msg.linear.x = 0.05  # Pelan-pelan saat sedang belok tajam
```

- **Jika robot belok terlalu lambat**: Naikkan penguat proportional `1.2` menjadi `1.8` - `2.5`.
- **Jika robot berbelok melampaui target (*overshoot*)**: Turunkan penguat ke `0.6` - `0.8`.

---

### D. Tuning ESP32 (PWM Motor & Sudut Servo Gripper)
File Target: [esp32_firmware_example.ino](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/esp32_firmware_example.ino#L35-L55)

```cpp
// Konversi kecepatan linear/angular ke PWM (0 - 255)
int pwm_left  = constrain(abs(v_left) * 255.0 / 0.5, 0, 255);
int pwm_right = constrain(abs(v_right) * 255.0 / 0.5, 0, 255);

// Minimal Deadband PWM Motor DC (Agar motor dapat berputar pada kecepatan rendah)
if (pwm_left > 0 && pwm_left < 45) pwm_left = 45;
if (pwm_right > 0 && pwm_right < 45) pwm_right = 45;
```

---

## 7. Histori Progres & Log AI (`PROGRESS_REPORT.md`)

Setiap progres pengerjaan, histori prompt, dan perubahan arsitektur dicatat secara otomatis dalam file [PROGRESS_REPORT.md](file:///home/fathir/eksbot2/PROGRESS_REPORT.md) agar AI selalu memiliki konteks yang konsisten.

---

## 8. Troubleshooting & Perbaikan Masalah Umum

1. **`RLException: Unable to contact my own server at [http://192.168.0.112:38651/]`**:
   - Jalankan `source /home/fathir/eksbot2/setup_env.sh` di setiap terminal sebelum mengeksekusi `roslaunch`.

2. **Gazebo lambat atau patah-patah**:
   - Pastikan komputer Anda menggunakan GPU Dedicated jika ada.
   - Atur `real_time_update_rate` di [autostack_arena.world](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/worlds/autostack_arena.world#L20) dari `1000` menjadi `500`.

3. **OpenCV `cv_bridge` Error pada Python 3**:
   - Jalankan perintah rebuild workspace: `cd catkin_ws && catkin_make -DPYTHON_EXECUTABLE=/usr/bin/python3`.

4. **Kamera Gazebo tidak muncul topik `/camera/image_raw`**:
   - Periksa daftar topik aktif dengan: `rostopic list`.
   - Pastikan plugin Gazebo ROS camera terinstal dengan benar (`sudo apt install ros-noetic-gazebo-plugins`).

5. **ESP32-CAM Stream dropped / Timeout**:
   - Turunkan resolusi kamera ESP32-CAM ke `QVGA (320x240)` atau `VGA (640x480)` dan atur kualitas JPEG ke 12-15.
