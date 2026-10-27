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
2. **ESP32-WROVER / ESP32-CAM (Wi-Fi SoftAP & Bridge)**:
   - `firmware_esp32_cam.ino`: Bertindak sebagai Wi-Fi Access Point (`SSID: dimas_asoy_geboy`, Pass `12345678`, IP: `192.168.4.1`), streamer MJPEG `http://192.168.4.1/stream` (QVGA 320x240), listener UDP port `8888`, dan penerus data kontrol via **Kabel Serial UART2** (WROVER: TX=GPIO33, RX=GPIO32). Konfigurasi kamera identik dengan `tes_cam_lcd/tescamesp.cpp` yang terbukti stabil. Dilengkapi failsafe STOP jika laptop berhenti mengirim data > 500 ms.
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
│           ├── firmware/                     # Firmware Mikrokontroler Arduino ESP32
│           │   ├── firmware_esp32_cam/       # Firmware ESP32-CAM (SoftAP + MJPEG Stream + OTA Web)
│           │   │   └── firmware_esp32_cam.ino
│           │   └── firmware_esp32_control/   # Firmware ESP32 Motor & Servo (UART + ADC Baterai)
│           │       └── firmware_esp32_control.ino
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
│               ├── main.py                   # 1. ORKESTRATOR (CLI entry point & window loop)
│               ├── vision.py                 # 2. MATA (Input Kamera ESP/ROS/Webcam + HSV + CSRT)
│               ├── robot_api.py              # 3. TUBUH & OTAK (Hardware Driver UDP/ROS + Autopilot State Machine)
│               ├── hmi/                      # 4. ANTARMUKA PILOT
│               │   ├── server.py             # Server HTTP lokal, MJPEG Streamer, REST API
│               │   └── index.html            # Web Console HUD Flat Theme + Canvas Overlay
│               ├── visionTarget.py           # Single-script Vision (Legacy)
│               └── esp32_firmware_example.ino# ROSSerial Firmware (Legacy)
└── spesifikasi/                              # Gambar acuan spesifikasi
└── tes_cam_lcd/                              # Uji kamera + LCD (tescamesp.cpp = referensi firmware kamera yang stabil)
└── tes_manual_control/                       # Program khusus uji manual robot (Direct Wi-Fi ESP32, tanpa kamera)
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

1. **Flash Firmware ESP32-WROVER/CAM**:
   - Buka `catkin_ws/src/eksbot_simulation/scripts/firmware_esp32_cam.ino` di Arduino IDE (tanpa library tambahan, ArduinoJson tidak lagi dibutuhkan).
   - Board: **ESP32 Wrover Module** (PSRAM aktif). Model kamera dipilih lewat `#define CAMERA_MODEL_...` di baris atas (default `WROVER_KIT`, sama dengan `tescamesp.cpp`).
   - Setelah upload, Serial Monitor (115200) harus menampilkan `Kamera siap.` lalu `ESP32-CAM Access Point Aktif`. Board memancarkan Wi-Fi `dimas_asoy_geboy` (Pass: `12345678`).
   - **Matikan ESP lain yang juga memancarkan `dimas_asoy_geboy` / IP `192.168.4.1`** (mis. `tes_manual_control/robot.ino`). Dua AP dengan nama & IP sama membuat laptop salah konek.

2. **Flash Firmware ESP32 Sistem Kontrol**:
   - Buka `catkin_ws/src/eksbot_simulation/scripts/firmware_esp32_control.ino` di Arduino IDE.
   - Hubungkan kabel Hardware Serial UART2 (**JANGAN gunakan GPIO16/17 di sisi WROVER karena dipakai PSRAM**):
     - **WROVER GPIO33 (TX)** $\rightarrow$ **ESP32 Control GPIO16 (RX2)**.
     - **WROVER GPIO32 (RX)** $\leftarrow$ **ESP32 Control GPIO17 (TX2)**.
     - **GND** WROVER terhubung ke **GND** ESP32 Control.
   - Flash ke ESP32 Sistem Kontrol.

3. **Jalankan Aplikasi Web HMI di Laptop**:
   - Hubungkan Wi-Fi Laptop ke access point `dimas_asoy_geboy` (Pass: `12345678`).
   - Jalankan script `main.py` (Mode Fisik default, **TIDAK BUTUH ROS**):
     ```bash
     python3 catkin_ws/src/eksbot_simulation/scripts/main.py
     ```
   - Browser laptop otomatis membuka **`http://localhost:8000`** (Web Console HMI Pilot).
   - Tampilan Web dilengkapi:
     - **Live Video Stream & Canvas HUD** (Braket target CSRT, Heading bar error, crosshair target, telemetry battery, indikator status).
     - **Tema Flat**: Tema Terang (Background Putih) & Tema Gelap (Background Hitam), tombol warna soft.
     - **Animasi Tombol Responsif**: Tombol WSAD dan tombol aksi menyala/berkedip (`pulse` & `held`) dengan halus saat ditekan via keyboard/klik.
     - **Audio Feedback / Sound Cues**: Sintesis Web Audio API (suara radar chirp saat lock target, suara descending saat target lepas, alarm darurat E-STOP, chime down saat Wi-Fi putus). Toggle via tombol `[P]`.
     - **Flight Data Recorder (Blackbox Telemetry)**: Tombol `● REC [O]` untuk merekam video HUD `.webm` dan menyimpan log telemetri per 100ms ke `.csv` (auto-download saat dihentikan).
     - **HSV Tuner Live di Web**: Slider pengaturan `H_min, H_max, S_min, S_max, V_min, V_max` interaktif untuk kalibrasi pencahayaan ruangan tanpa restart program.
     - **Telemetri Baterai Real-Time**: Pill header `🔋 12.0V · 95%` dan meter baterai di HUD dari pembacaan ADC ESP32.
     - **OTA Update Firmware Web Page**: Akses `http://192.168.4.1/update` untuk upload biner `.bin` nirkabel ke ESP32-CAM via browser.
     - **Crosshair Tuner**: Dapat diatur (ukuran, celah, ketebalan, warna, dan offset X/Y) atau digeser via `Shift` + Panah Keyboard.
     - **Popup Legenda Tombol**: Tekan tombol `H` atau klik tombol "Legenda" di navbar atas.
     - **Opsi GUI OpenCV Lama**: Jalankan `python3 main.py --gui` jika ingin jendela OpenCV pop-up tetap aktif bersamaan.

4. **Keamanan & Failsafe**:
   - ESP32-CAM & ESP32-Control dilengkapi timer failsafe 500 ms (otomatis berhenti jika sinyal terputus).
   - Selalu lakukan uji coba awal dengan roda robot diganjal/terangkat.

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

5. **ESP32-CAM Stream dropped / Timeout / Delay / Freeze**:
   - Pakai konfigurasi kamera `QVGA (320x240)`, `jpeg_quality 10-12`, `xclk 10 MHz`, `fb_count 2` + `CAMERA_GRAB_LATEST` (sudah default di `firmware_esp32_cam.ino`). Jangan naikkan ke VGA lewat SoftAP: bandwidth ESP32 AP hanya ~1-2 MB/s dan latensi akan menumpuk.
   - Wi-Fi tidak muncul sama sekali: cek Serial Monitor. `Kamera Error: 0x...` berarti model board/pin kamera salah (WROVER Kit vs AI-Thinker). Firmware lama berhenti total pada error ini sehingga AP tidak pernah menyala; sekarang AP tetap menyala dan kamera dicoba ulang tiap 5 detik.
   - Jangan memakai GPIO16/17 untuk UART di board WROVER/PSRAM (bentrok dengan PSRAM -> crash/reboot).
   - Tegangan: WROVER + kamera + Wi-Fi butuh arus puncak tinggi. Jika Wi-Fi hilang/reboot saat memakai UBEC tetapi normal lewat USB laptop, lihat catatan power di `PROGRESS_REPORT.md` (Prompt 19-23).
   - Hanya satu klien yang bisa menonton `/stream` bersamaan; tutup tab browser stream sebelum menjalankan `main.py`.
