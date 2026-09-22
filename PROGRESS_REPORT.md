# PROGRESS REPORT & LOG HISTORY - AUTOSTACK EXSBOT2

File ini merupakan **Laporan Progres & Histori Log Utama** yang WAJIB dibaca dan diperbarui oleh AI pada setiap prompt/interaksi agar AI tidak kehilangan jejak (*context*) mengenai proyek `eksbot2`.

---

## 📌 Status Terakhir Proyek
- **Tanggal Update Terakhir**: 2026-09-18
- **Status Workspace**: ROS Noetic Package `eksbot_simulation` Terkompilasi 100% (`catkin_make` Sukses).
- **Status Fitur Utama**:
  - [x] Arena Simulasi Gazebo AutoStack ($3.5\times 2.8\text{ m}$) (`autostack_arena.world`).
  - [x] Objek Kubus 3 Warna (Merah, Hijau, Biru $50\times 50\times 50\text{ mm}$, $30\text{ g}$).
  - [x] Robot Dummy Differential Drive + Vertical Lift + 2-Finger Gripper + ESP32-CAM.
  - [x] Script Computer Vision ROS (`visionTarget.py`) dengan HSV Masking + CSRT Tracking + `/cmd_vel` Publisher.
  - [x] Template Firmware ESP32 (`esp32_firmware_example.ino`) via `rosserial`.
  - [x] Script Perbaikan Jaringan ROS (`setup_env.sh`) untuk mengatasi `RLException: Unable to contact my own server`.
  - [x] Dokumentasi Utama (`README.md`) & `PROGRESS_REPORT.md`.

---

## 📜 Histori Prompt & Log Pengerjaan

### Prompt 1: Pembuatan Arena Simulasi, Kubus 3 Warna, Robot Dummy, Vision & ESP32 Setup
- **User Prompt**: Buatkan arena simulasi gazebo berdasarkan spek di `@spesifikasi`, kubus 3 warna, dummy robot, copy `visionTarget.py` dari folder `kuyang`, siapkan arsitektur ROS untuk laptop (comvis) dan ESP32 (kontrol).
- **Tindakan & Progress**:
  1. Membaca gambar spesifikasi di `/home/fathir/eksbot2/spesifikasi` (`spek_arena.jpeg`, `spek_kubus.jpeg`, `spek_robot.jpeg`).
  2. Mencari dan membaca `/home/fathir/kuyang/src/visionTarget.py`.
  3. Mengatur struktur paket ROS Catkin `/home/fathir/eksbot2/catkin_ws/src/eksbot_simulation`.
  4. Membuat generator tekstur arena `generate_arena_texture.py` dan memproduksi `arena_banner.png` serta model SDF `arena_ground`.
  5. Membuat 3 model SDF kubus ($50\times 50\times 50\text{ mm}$, $30\text{ g}$): `cube_red`, `cube_green`, `cube_blue`.
  6. Membuat dunia Gazebo `autostack_arena.world` dengan 24 kubus ter-spawn.
  7. Membuat model robot URDF `dummy_robot.urdf.xacro` dengan differential drive plugin & ROS camera plugin.
  8. Memperbarui `visionTarget.py` dengan integrasi ROS Image Subscriber (`/camera/image_raw`) dan Velocity Publisher (`/cmd_vel`).
  9. Membuat firmware template ESP32 `esp32_firmware_example.ino`.
  10. Mengompilasi paket dengan `catkin_make` (Status: 100% Sukses).

### Prompt 2: Pembuatan README & Panduan Running / Tuning
- **User Prompt**: Buatkan readme penjelasan, cara tuning program, cara run dll.
- **Tindakan & Progress**:
  1. Membuat `README.md` utama di `/home/fathir/eksbot2/README.md` dan paket ROS.
  2. Menyusun panduan running (simulasi & robot fisik), panduan tuning HSV, EMA smoothing, deadzone, proportional gain `/cmd_vel`, dan PWM/servo ESP32.

### Prompt 3: Update README Otomatis, Pembuatan PROGRESS_REPORT.md, & Troubleshooting RLException ROS IP
- **User Prompt**: Selalu update readme jika ada fitur baru, buatkan progresreport md untuk tiap prompt dan progres, serta atasi masalah `RLException: Unable to contact my own server at [http://192.168.0.112:38651/]`.
- **Tindakan & Progress**:
  1. **Analisis Penyebab Error**: `~/.bashrc` memiliki `export ROS_IP=192.168.0.112` dan `ROS_MASTER_URI=http://192.168.0.100:11311` yang terkonfigurasi ke IP statis lama yang tidak aktif di interface Wi-Fi (`wlo1` saat ini ber-IP `10.24.85.66`). ROS 1 gagal melakukan bind ke IP `192.168.0.112`.
  2. **Solusi Perbaikan**: Dibuat script otomatis `/home/fathir/eksbot2/setup_env.sh` (`ROS_MASTER_URI=http://localhost:11311` & `ROS_IP=127.0.0.1`). Diuji dengan `roslaunch --nodes eksbot_simulation arena_simulation.launch` (Sukses 100%).
  3. **Membuat File `PROGRESS_REPORT.md`** & **Memperbarui `README.md`**.

### Prompt 4: Penjelasan Lokasi Kode Robot, Cara Pengaturan, Pengertian API, dan Arsitektur Modular `simi26`
- **User Prompt**: Jelaskan aku code robotnya dimana, cara aturnya gimana, serta apa itu API, kenapa di simi26 ada API ada vision ada main. Jelaskan aku jgn ubah code.
- **Tindakan & Progress**: Menjelaskan struktur file `eksbot2`, konfigurasi vision/hardware, konsep API, dan arsitektur modular `simi26` (`vision.py`, `drone_api.py`, `main.py`).

### Prompt 5: Penjelasan Penerapan Arsitektur Modular pada `eksbot2` (Laptop, ESP32-CAM, ESP32)
- **User Prompt**: Kalau ini diterapkan ke eksbot 2 yang berbasis ESP apakah bisa? Nanti yang di-up ke masing-masing ESP atau laptop bagaimana jelaskan dulu.
- **Tindakan & Progress**:
  1. Menjelaskan secara rinci bahwa arsitektur modular (`main.py`, `vision.py`, `robot_api.py`) **100% SANGAT BISA** diterapkan pada `eksbot2`.
  2. Menjelaskan pembagian tugas & file yang di-upload / dijalankan pada masing-masing perangkat:
     - **ESP32-CAM**: Firmware MJPEG Streaming HTTP via Wi-Fi.
     - **ESP32 Kontroler**: Firmware C++ (`esp32_firmware_example.ino`) penerima topik ROS `/cmd_vel` & `/esp32/servo`.
     - **Laptop**: Pusat komputasi yang menjalankan `vision.py` (OpenCV), `robot_api.py` (ROS Publisher/Subscriber), dan `main.py` (Otak Strategi Misi).

---

## 🗺️ Peta File Utama Dalam Workspace

```
/home/fathir/eksbot2/
├── README.md                           # Dokumentasi utama proyek
├── PROGRESS_REPORT.md                  # Log progres & histori prompt (File Ini)
├── setup_env.sh                        # Script perbaikan/setup environment ROS IP
├── catkin_ws/
│   └── src/
│       └── eksbot_simulation/
│           ├── launch/
│           │   ├── arena_simulation.launch   # Launch Gazebo world + robot + kubus
│           │   └── vision_control.launch     # Launch ROS Vision Node
│           ├── worlds/
│           │   └── autostack_arena.world     # Dunia simulasi Gazebo AutoStack
│           ├── models/
│           │   ├── arena_ground/             # Tekstur & model spanduk 3.5m x 2.8m
│           │   ├── cube_red/                 # SDF Kubus Merah 50mm 30g
│           │   ├── cube_green/               # SDF Kubus Hijau 50mm 30g
│           │   └── cube_blue/                # SDF Kubus Biru 50mm 30g
│           ├── urdf/
│           │   └── dummy_robot.urdf.xacro    # URDF Robot Dummy + Gripper + Camera
│           └── scripts/
│               ├── visionTarget.py           # Vision Node ROS OpenCV CSRT
│               ├── generate_arena_texture.py # PNG Renderer arena_banner.png
│               └── esp32_firmware_example.ino # Firmware Arduino/ESP32
```

---

## 🚨 Troubleshooting Log & Solusi yang Pernah Diterapkan

| Tanggal | Isu / Error | Penyebab Utama | Solusi / Perbaikan |
|---|---|---|---|
| 2026-09-18 | `RLException: Unable to contact my own server at [http://192.168.0.112:38651/]` | `~/.bashrc` meng-export IP statis `192.168.0.112` & `ROS_MASTER_URI` ke IP lama yang sudah tidak aktif pada adapter Wi-Fi. | Jalankan `source /home/fathir/eksbot2/setup_env.sh` sebelum `roslaunch` untuk mengeset `ROS_MASTER_URI=http://localhost:11311` dan `ROS_IP=127.0.0.1`. |

---

## 🤖 Panduan Instruksi Untuk AI (AI Directives)
1. **Setiap kali menerima prompt baru dari user**: AI HARUS mengecek `PROGRESS_REPORT.md` untuk memahami konteks dan status terakhir.
2. **Setiap kali selesai mengerjakan fitur baru / perbaikan**: AI HARUS memperbarui `PROGRESS_REPORT.md` (menambahkan histori prompt baru) DAN memperbarui `README.md` jika terdapat perubahan/fitur baru.
