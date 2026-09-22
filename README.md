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
+-------------------------------------------------------------------------+
|                              LAPTOP (ROS)                               |
|                                                                         |
|  +---------------------+      +------------------+                   |
|  | Gazebo / ESP32-CAM  | ---> | visionTarget.py  |                   |
|  | Image Stream        |      | (Color & CSRT)   |                   |
|  +---------------------+      +--------+---------+                   |
|                                        |                             |
|                                        v                             |
|                               +------------------+                   |
|                               | Topik ROS        |                   |
|                               | /cmd_vel         |                   |
|                               | /esp32/servo     |                   |
|                               +--------+---------+                   |
+----------------------------------------|--------------------------------+
                                         | (rosserial / USB / Wi-Fi)
                                         v
+-------------------------------------------------------------------------+
|                           ESP32 (KONTROLER)                             |
|                                                                         |
|  +---------------------+      +------------------+                   |
|  | Driver Motor        | <--- | esp32_firmware   |                   |
|  | L298N / BTS7960     |      | (Motor & Servo)  |                   |
|  +---------------------+      +------------------+                   |
+-------------------------------------------------------------------------+
```

1. **Laptop (Pusat Komputasi Vision & Logika Navigation)**:
   - Menerima image feed dari kamera Gazebo (`/camera/image_raw`) atau stream HTTP MJPEG dari ESP32-CAM fisik (`http://<IP_ESP32_CAM>/stream`).
   - Node `visionTarget.py` memproses deteksi warna HSV, penjejakan *CSRT Tracker*, dan kalkulasi galat posisi (*error offset*).
   - Menghasilkan perintah kecepatan `cmd_vel` (linier & angular) serta perintah servo.
2. **ESP32 (Sistem Kontrol Hardware)**:
   - Berfungsi sebagai aktuator kontroler yang menerima sinyal `/cmd_vel` via `rosserial` atau Wi-Fi UDP Socket.
   - Mengendalikan PWM motor DC kiri & kanan serta servo penumpuk kubus.

---

## 2. Spesifikasi Teknis

### A. Arena AutoStack (`autostack_arena.world`)
- **Spanduk Total**: $350 \times 280\text{ cm}$ ($3.5\text{ m} \times 2.8\text{ m}$).
- **Ring Lingkaran**:
  - Diameter luar: $\varnothing 200\text{ cm}$ (Radius $1.0\text{ m}$).
  - Diameter dalam: $\varnothing 160\text{ cm}$ (Radius $0.8\text{ m}$).
- **3 Base Tim**: Merah (Selatan), Hijau (Barat), Biru (Timur) ukuran $90 \times 70\text{ cm}$.
- **Pad Stacking (Kuning)**: Ukuran $40 \times 40\text{ cm}$ di ujung setiap base tim.
- **Gerbang (Gate)**: Lebar $45\text{ cm}$ ke area ring.

### B. Objek Kubus (`cube_red`, `cube_green`, `cube_blue`)
- **Dimensi**: $50 \times 50 \times 50\text{ mm}$ ($0.05\text{ m}$).
- **Massa**: $30\text{ gram}$ ($0.03\text{ kg}$).
- **Warna**: Merah, Hijau, Biru (8 buah untuk masing-masing warna).

### C. Robot Dummy (`dummy_robot.urdf.xacro`)
- **Footprint Awal**: $22 \times 22\text{ cm}$ (Batas maks: $25 \times 25\text{ cm}$).
- **Tinggi Maksimum**: $40\text{ cm}$ (Batas maks: $45\text{ cm}$).
- **Penggerak**: Differential Drive (2 roda penggerak + 2 caster).
- **Mekanisme**: Vertical lift slider & 2-finger gripper servo.
- **Kamera**: ESP32-CAM Gazebo Camera Sensor (FOV 1.1 rad, resolusi 640x480 @ 30 FPS).

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
│           │   └── vision_control.launch     # Membuka Node ROS Vision Target
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
│               ├── generate_arena_texture.py # Renderer tekstur arena.png
│               ├── visionTarget.py           # Core Vision & Control ROS Node
│               └── esp32_firmware_example.ino # Firmware Arduino/ESP32
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
*Script ini secara otomatis mengatur `ROS_MASTER_URI=http://localhost:11311` dan `ROS_IP=127.0.0.1` serta menge-source workspace Catkin.*

Jika ingin menggunakannya untuk robot fisik pada jaringan Wi-Fi:
```bash
source setup_env.sh network
```

---

## 5. Cara Menjalankan (Running Guide)

### A. Menjalankan Simulasi Gazebo & Vision (Simulasi)

1. **Buka Terminal dan Setup Environment**:
   ```bash
   cd /home/fathir/eksbot2
   source setup_env.sh
   cd catkin_ws
   catkin_make
   ```

2. **Jalankan Simulasi Gazebo**:
   ```bash
   roslaunch eksbot_simulation arena_simulation.launch
   ```
   *Jendela Gazebo akan terbuka menampilkan Arena AutoStack, Robot Dummy, dan 24 Kubus.*

3. **Jalankan Node Vision (Terminal Baru)**:
   ```bash
   cd /home/fathir/eksbot2
   source setup_env.sh
   roslaunch eksbot_simulation vision_control.launch
   ```
   *Jendela OpenCV akan terbuka menampilkan feed dari kamera simulasi.*

4. **Cara Mengontrol Target Vision**:
   - **Klik Mouse**: Klik kiri pada kubus berwarna di jendela OpenCV untuk mengunci (*LOCK*) target tersebut.
   - **Tombol Angka (1-9)**: Tekan angka 1-9 pada keyboard untuk memilih target terdeteksi.
   - **Tombol 'R'**: Menghapus kunci target (*RESET / UNLOCK*) dan kembali ke mode deteksi multi-target.
   - **Tombol 'ESC'**: Keluar dari aplikasi vision.

---

### B. Menjalankan Pada Robot Fisik (ESP32-CAM & ESP32)

1. **Konfigurasi ESP32-CAM**:
   - Hubungkan ESP32-CAM ke jaringan Wi-Fi lokal.
   - Buka file [visionTarget.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/visionTarget.py) dan ubah parameter konfigurasi:
     ```python
     USE_ESP_CAM = True
     ESP_CAM_URL = "http://172.20.10.3/stream"  # Ganti IP sesuai ESP32-CAM Anda
     ```

2. **Upload Firmware ke ESP32**:
   - Buka [esp32_firmware_example.ino](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/esp32_firmware_example.ino) di Arduino IDE.
   - Sesuaikan PIN motor driver (IN1, IN2, ENA, IN3, IN4, ENB) dan servo.
   - Flash ke board ESP32.

3. **Jalankan ROS Serial Bridge di Laptop**:
   ```bash
   rosrun rosserial_python serial_node.py _port:=/dev/ttyUSB0 _baud:=115200
   ```

4. **Jalankan Vision Node**:
   ```bash
   rosrun eksbot_simulation visionTarget.py
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
