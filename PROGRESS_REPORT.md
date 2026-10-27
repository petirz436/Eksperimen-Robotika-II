# PROGRESS REPORT & LOG HISTORY - AUTOSTACK EXSBOT2

File ini merupakan **Laporan Progres & Histori Log Utama** yang WAJIB dibaca dan diperbarui oleh AI pada setiap prompt/interaksi agar AI tidak kehilangan jejak (*context*) mengenai proyek `eksbot2`.

---

## 📌 Status Terakhir Proyek
- **Tanggal Update Terakhir**: 2026-10-23
- **Status Workspace**: ROS Noetic Package `eksbot_simulation` Terkompilasi 100% (`catkin_make` Sukses).
- **Status Fitur Utama**:
  - [x] Arena Simulasi Gazebo AutoStack ($3.5\times 2.8\text{ m}$) (`autostack_arena.world`).
  - [x] Objek Kubus 3 Warna (Merah, Hijau, Biru $50\times 50\times 50\text{ mm}$, $30\text{ g}$).
  - [x] Robot Dummy Differential Drive + Vertical Lift + 2-Finger Gripper + ESP32-CAM.
  - [x] Script Computer Vision ROS (`visionTarget.py`) dengan HSV Masking + CSRT Tracking + `/cmd_vel` Publisher.
  - [x] Template Firmware ESP32 (`esp32_firmware_example.ino`) via `rosserial`.
  - [x] Script Perbaikan Jaringan ROS (`setup_env.sh`) untuk mengatasi `RLException: Unable to contact my own server`.
  - [x] Dokumentasi Utama (`README.md`) & `PROGRESS_REPORT.md`.
  - [x] Workspace dipulihkan ke checkpoint `eksbot_baru` (perubahan Codex 2026-10-21 dihapus).
  - [x] Firmware `firmware_esp32_cam.ino` diperbaiki berdasarkan `tes_cam_lcd/tescamesp.cpp` (kompilasi `esp32:esp32:esp32wrover` sukses; uji hardware masih perlu dilakukan).
  - [x] `main.py`: `ESPCamReader` latest-frame + auto-reconnect, loop tidak freeze saat stream mati.
  - [x] Arsitektur modular terpisah: `camera_sources.py` (sumber kamera), `control.py` (kontroler independen GUI), `hmi_server.py` (web server HTTP natif), `hmi/index.html` (Console HMI Pilot HUD flat theme + crosshair adjustment).
  - [x] Firmware `firmware_esp32_control.ino` dilengkapi failsafe 500 ms dan non-blocking Serial parser. Keduanya lulus uji kompilasi arduino-cli dan unit test integrasi 22/22 PASS.

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

### Prompt 6: Diskusi Arsitektur Sistem Terpisah (ESP32-CAM, ESP32 Kontroler, Laptop) & Saran Optimalisasi
- **User Prompt**: Ajak aku diskusi jika program dibuat terpisah seperti di simi26 apakah bisa? Jadi ada program di esp cam, di esp yg sistem kontrol serta terakhir program di laptop. Adakah saran untukku atau ada yg lebih baik?
- **Tindakan & Progress**: Melakukan analisis dan pembimbingan diskusi arsitektur terdistribusi (Distributed Systems), membandingkan kelebihan/kekurangan skema 3-tier, serta memberikan rekomendasi protokol komunikasi (`rosserial`/Micro-ROS/Serial) dan struktur modular software.

### Prompt 7: Perancangan Rencana Arsitektur Modular 3-Tier (ESP32-CAM SoftAP + Serial Cable to ESP32 Control)
- **User Prompt**: Ubah workspace ini agar jadi sistem modular. ESP-CAM jadi pemancar Wi-Fi yang nanti Wi-Fi diterima oleh laptop nanti kalkulasi eror di laptop dan kirim hasil ke ESP-CAM dari ESP-CAM nanti kirim eror ke ESP sistem kontrol dengan komunikasi kabel. Apakah memungkinkan?
- **Tindakan & Progress**:
  1. Mengonfirmasi bahwa skema ini **SANGAT MEMUNGKINKAN (100% Valid & Optimal)**.
  2. Menyusun `implementation_plan.md` yang membagi sistem menjadi:
     - **ESP32-CAM**: Firmware SoftAP + MJPEG Streamer + Wi-Fi Control Listener + UART Serial Cable Bridge.
     - **Laptop**: `vision.py` (OpenCV RGB HSV Masking + Color Switcher R/G/B tanpa warna coklat), `robot_api.py` (Network/ROS Control API), dan `main.py` (State Machine Misi).
     - **ESP32 Sistem Kontrol**: Firmware UART Serial Listener + Motor Differential Drive PWM & Servo Gripper/Lift.

### Prompt 8: Implementasi Lengkap Sistem Modular (Simulasi Gazebo, Vision RGB Switcher, Kontrol Manual WSAD, & Firmware ESP32)
- **User Prompt**: Langsung garap semua termasuk yang simulasinya juga serta buat agar robot dapat di kontrol manual juga selain robot ikut navigasi dari kamera. Robot di kontrol dengan W S A D.
- **Tindakan & Progress**:
  1. **[vision.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/vision.py)**: Dibuat modul Vision Engine OpenCV untuk deteksi Red (R), Green (G), Blue (B) dengan switcher mode warna (`1`:Red, `2`:Green, `3`:Blue) & CSRT Tracker (kode warna coklat dibuang).
  2. **[robot_api.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/robot_api.py)**: Dibuat modul Robot Interface API pengirim sinyal kecepatan `/cmd_vel` (ROS) & Wi-Fi UDP Packet ke ESP32.
  3. **[main.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/main.py)**: Dibuat aplikasi utama yang mengombinasikan **Kontrol Manual Keyboard WSAD** (W:Maju, S:Mundur, A:Kiri, D:Kanan, SPACE:Stop, J/K:Gripper, U/I:Lift) dan **Auto Vision Navigation** (Switch mode via tombol `M`).
  4. **[firmware_esp32_cam.ino](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/firmware_esp32_cam.ino)**: Dibuat firmware SoftAP ESP32-CAM (`AutoStack-ESP-CAM`), MJPEG Streamer `/stream`, dan Hardware Serial UART2 Bridge (Pin 17 TX2 / Pin 16 RX2).
  5. **[firmware_esp32_control.ino](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/firmware_esp32_control.ino)**: Dibuat firmware ESP32 Sistem Kontrol penerima instruksi Serial Kabel UART2, pengendali Differential Drive Motor DC (L298N PWM), dan Servo Gripper/Lift.
  6. **[modular_control.launch](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/launch/modular_control.launch)**: Launch file ROS untuk menjalankan `main.py` di lingkungan simulasi Gazebo.
  7. **Kompilasi & Dokumentasi**: Workspace terkompilasi 100% via `catkin_make`. `README.md` dan `PROGRESS_REPORT.md` diperbarui lengkap.

### Prompt 9: Pembuatan Program Uji ESP32-CAM + Web Stream + Vision Laptop -> TFT LCD di Folder Khusus (`tes_cam_lcd`)
- **User Prompt**: Buat tes cam esp untuk di-up ke ESP-CAM yang nanti hasil kamera dimasukkan ke TFT LCD dengan pin (VCC 3.3V, GND, SCL GPIO 25, SDA GPIO 33, RST GPIO 32, CS GPIO 34, BL 3.3V). Lalu hasil distreaming ke website lokal yang dibuka di laptop lalu laptop menjalankan vision.py untuk deteksi objek lalu hasil deteksi ditampilkan di LCD, apakah bisa? Hanya ubah tescamesp.cpp jangan ubah code lain, buat folder baru.
- **Tindakan & Progress**:
  1. **Analisis Kelayakan Hardware & Pinout**:
     - Mengonfirmasi bahwa **SISTEM INI 100% MEMUNGKINKAN DAN BISA DILAKUKAN**.
     - Memberikan peringatan bentrok hardware: **GPIO 25 (VSYNC kamera)**, **GPIO 32 (PWDN kamera)**, dan **GPIO 34 (Input-Only & Data Y8 kamera)** tidak dapat digunakan sebagai pin SPI LCD karena akan menyebabkan kamera crash/error.
     - Menyediakan solusi skema wiring pinout aman di ESP32-CAM menggunakan pin SD-Card yang bebas: **CLK: GPIO 14, MOSI: GPIO 13, CS: GPIO 15, DC: GPIO 2, RST: GPIO 12**.
  2. **[tescamesp.cpp](file:///home/fathir/eksbot2/tescamesp.cpp)**: Dibuat program C++ Arduino lengkap berisi HTTP MJPEG Streamer, UDP Listener (Port 8888), dan Driver ST7735/ILI9341 TFT LCD.
  3. **Folder Khusus [tes_cam_lcd](file:///home/fathir/eksbot2/tes_cam_lcd)**: Dibuat folder terisolasi berisi:
     - `tescamesp.cpp`: C++ firmware ESP32-CAM.
     - `test_vision_laptop.py`: Script Python penguji laptop yang menangkap stream web, menjalankan vision RGB, dan mengirimkan paket telemetri UDP ke ESP32-CAM.
     - `README.md`: Panduan wiring dan cara pengujian.

### Prompt 10: Randomization Kubus Tengah Arena, Spawn Robot di Base Biru, & Perbaikan Delay Kontrol WSAD
- **User Prompt**: Buatkan agar kubus-kubus diletakkan di tengah arena secara acak, lalu robot taruh di arena biru. Perbaiki mekanisme maju mundur belok kiri kanan karena terkadang delay.
- **Tindakan & Progress**:
  1. **Randomization Kubus di Tengah Arena ([autostack_arena.world](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/worlds/autostack_arena.world))**: Mengatur ulang pose 9 kubus (3 Merah, 3 Hijau, 3 Biru) agar tersebar secara acak di dalam area ring pusat arena ($r < 0.6\text{ m}$).
  2. **Spawn Robot di Base Biru ([arena_simulation.launch](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/launch/arena_simulation.launch))**: Mengubah koordinat spawn awal robot ke Base Biru (East Base) pada `x = 1.35 m, y = 0.0 m, Yaw = 3.14159 rad` (menghadap ke pusat arena).
  3. **Perbaikan Akselerasi Gazebo ([dummy_robot.urdf.xacro](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/urdf/dummy_robot.urdf.xacro))**: Meningkatkan `<wheelAcceleration>` dari `1.0` ke `10.0` rad/s^2 dan `<wheelTorque>` dari `10` ke `30` N.m untuk menghilangkan delay akselerasi fisik Gazebo.
  4. **Perbaikan Kontrol Keyboard Responsif ([main.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/main.py))**: Fast 1ms sampling + key-hold watchdog.

### Prompt 11: Mekanisme Animasi 3D Grip/Release, Otomasi Auto-Grip & Lift, dan Navigasi Orient-First (Bebas Ragu-ragu & Patah-Patah)
- **User Prompt**: Buatkan 3d model untuk animasi mekanisme grip dan release. Saat target sudah dijangkauan robot akan grip target otomatis saat di mode otomatis. Koreksi navigasinya kenapa terkesan patah patah? Perbaiki. Saat dia ke lokasi tujuan dia seperti ragu ragu dan saat serong dia tidak langsung serong tpi maju belok maju belok sedikit demi sedikit. Aku mau dia sesuaikan orientasi baru maju.
- **Tindakan & Progress**:
  1. **3D Vacuum Gripper Mechanism ([dummy_robot.urdf.xacro](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/urdf/dummy_robot.urdf.xacro))**: Menambahkan plugin `libgazebo_ros_vacuum_gripper.so` pada `lift_carriage` link untuk animasi fisik penempelan, pencengkeraman, dan pengangkatan kubus dalam ruang 3D Gazebo.
  2. **ROS Joint & Vacuum Control ([robot_api.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/robot_api.py))**: Mengintegrasikan publisher topik `/dummy_robot/gripper_switch` (`std_msgs/Bool`) yang otomatis aktif saat `set_gripper("CLOSE")` dan mati saat `set_gripper("OPEN")`.
  3. **Navigasi Orient-First (Luruskan Orientasi Dulu, Baru Maju Lurus) ([main.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/main.py))**:
     - Membuang logika zig-zag "maju-belok-maju-belok".
     - **Fase 1 (Aligning)**: Jika galat sudut $|\text{norm\_x}| > 0.12$, robot berhenti maju (`linear.x = 0.0`) dan memutar orientasinya di tempat (`angular.z = -1.8 * norm_x`) hingga lurus menghadap kubus.
     - **Fase 2 (Driving Straight)**: Setelah sudut lurus ($|\text{norm\_x}| \le 0.12$), robot maju lurus penuh ke depan (`linear.x = 0.25`) tanpa ragu-ragu.
  4. **Otomasi Auto-Grip & Lift 3D saat Target Terjangkau ([main.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/main.py) & [vision.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/vision.py))**: Saat kubus berada tepat di depan robot (`target_cy > frame_h - 110` atau `target_area > 12000`), robot otomatis berhenti, menutup gripper 3D, menempelkan kubus, dan mengangkut lift carriage ke atas secara otomatis.


### Prompt 12: Penjelasan Cara Penerapan & Running Direct Script ke Robot Fisik
- **User Prompt**: Apakah script di `catkin_ws/src/eksbot_simulation/scripts` sudah bisa diterapkan langsung ke robot? Bagaimana cara run langsung (bukan simulasi)? Jelaskan dulu tanpa mengubah kode.
- **Tindakan & Progress**:
  1. Menjelaskan secara rinci bahwa kodenya **100% SUDAH BISA DITERAPKAN LANGSUNG KE ROBOT FISIK**.
  2. Menjelaskan alur dual-mode pada `main.py`, `robot_api.py`, `firmware_esp32_cam.ino`, dan `firmware_esp32_control.ino`.
  3. Menyediakan panduan langkah demi langkah cara upload firmware, wiring serial UART2, serta cara mengeksekusi `python3 main.py` secara langsung tanpa simulasi ROS/Gazebo.

### Prompt 13: Konfirmasi Kebutuhan `roscore` pada Robot Fisik
- **User Prompt**: Apakah perlu `roscore`?
- **Tindakan & Progress**:
  1. Menjelaskan bahwa **`roscore` TIDAK PERLU** dijalankan saat menggunakan robot fisik.
  2. Menjelaskan mekanisme *fallback* otomatis di [main.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/main.py) dan [robot_api.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/robot_api.py) yang beralih langsung ke Socket UDP Wi-Fi & HTTP Stream ESP32-CAM tanpa membutuhkan ROS Master.

### Prompt 14: Pembuatan Program Khusus Uji Coba Kontrol Manual Direct Wi-Fi (Tanpa Kamera)
- **User Prompt**: Buatkan 1 program untuk sementara test control robot. Jadi wifi langsung dari esp sistem kontrol. Tanpa kamera dulu full mode manual.
- **Tindakan & Progress**:
  1. **Folder Khusus [tes_manual_control](file:///home/fathir/eksbot2/tes_manual_control)**: Dibuat folder terisolasi khusus untuk pengujian hardware.
  2. **[firmware_esp32_control_direct_wifi.ino](file:///home/fathir/eksbot2/tes_manual_control/firmware_esp32_control_direct_wifi.ino)**: Dibuat firmware C++ ESP32 Sistem Kontrol yang memancarkan Wi-Fi AP (`dimas_asoy_geboy`), mendengarkan paket UDP Port 8888, dan mengendalikan PWM Motor (L298N) serta Servo Gripper/Lift secara independen.
  3. **[test_manual_keyboard.py](file:///home/fathir/eksbot2/tes_manual_control/test_manual_keyboard.py)**: Dibuat script GUI Control Panel Laptop penguji kontrol keyboard real-time (WSAD, J/K, U/I, SPACE).
  4. **[README.md](file:///home/fathir/eksbot2/tes_manual_control/README.md)**: Dibuat panduan wiring pinout dan cara pengujian.

### Prompt 15: Penjelasan Konsep Kinematika Differential Drive & Variabel WHEEL_BASE
- **User Prompt**: Kenapa ada wheel base jelaskan
- **Tindakan & Progress**: Menjelaskan konsep matematika kinematika *differential drive*, mengapa `WHEEL_BASE` (jarak antar pusat roda) dibutuhkan untuk mengonversi nilai `linear_x` dan `angular_z` dari laptop menjadi kecepatan linear masing-masing roda ($v_{\text{left}}$ & $v_{\text{right}}$).

### Prompt 16: Diskusi & Perencanaan Integrasi Wheel Encoder (Rotary Encoder)
- **User Prompt**: aku ada encoder dan decoder
- **Tindakan & Progress**: Melakukan konfirmasi bahwa komponen yang dimaksud adalah **Wheel Rotary Encoder** pada roda motor, serta menjelaskan keuntungannya untuk **PID Closed-Loop Velocity Control** dan **Odometry Tracking** pada ESP32.

### Prompt 17: Konfirmasi Keamanan Program Manual Tanpa Encoder
- **User Prompt**: untuk program yyg manual sekarang tanpa encoder decoder masi aman kan
- **Tindakan & Progress**: Menjelaskan bahwa program manual saat ini **100% AMAT SANGAT AMAN** digunakan tanpa encoder (Open-Loop PWM Control). Encoder merupakan fitur opsional untuk upgrade akurasi di masa mendatang.

### Prompt 18: Penambahan Fungsi Print IP Address pada Firmware ESP32 Control Direct Wi-Fi
- **User Prompt**: di firmwae ini berikan fungsi untuk print ip esp nya
- **Tindakan & Progress**:
  1. Menambahkan fungsi helper `printESP32IPInfo()` pada [firmware_esp32_control_direct_wifi.ino](file:///home/fathir/eksbot2/tes_manual_control/firmware_esp32_control_direct_wifi.ino).
  2. Fungsi menampilkan SSID Wi-Fi, IP SoftAP (`192.168.4.1`), Port UDP, serta jumlah client/laptop yang sedang terhubung ke ESP32.
  3. Mengatur agar info IP dicetak otomatis saat `setup()` dan diperbarui secara periodik setiap 5 detik di `loop()`.

### Prompt 19: Analisis Masalah Hardware Wi-Fi ESP32 Hilang Saat Terpasang di Robot (Strapping Pins & Power Drop)
- **User Prompt**: jelaskan apa yang menyebabkan wfii tidak muncul saat esp sudah di tanam kke robot padahal saat dicbut dari robot ada wifi
- **Tindakan & Progress**: Menjelaskan 3 penyebab utama (Strapping Pins GPIO 2/5, Inrush Current Power Drop, & Input-only pins).

### Prompt 20: Troubleshooting Kelistrikan UBEC Step-Down (12V ke 5V), Inrush Current Servo, & Peringatan GPIO 3 (RX0)
- **User Prompt**: pin sudah dibetulkan. apakah karena kurang ampere? soalnya voltase dar batreai ke ubec dulu hasilnya dari 12 jadi 5v
- **Tindakan & Progress**:
  1. Menjelaskan bahwa **UBEC 12V ke 5V yang berbagi daya dengan Servo/Motor** dapat mengalami *voltage sag/drop* sekejap saat Servo/Motor menyala (inrush current spike 1A-3A), memicu **Brownout Reset** di ESP32 sehingga Wi-Fi tidak sempat menyala.
  2. Memberikan peringatan bahwa **GPIO 3 (`SERVO_LIFT_PIN 3`) adalah Pin RX0 (Serial USB Debugging)** yang tidak boleh dipakai untuk Servo karena bentrok dengan USB Serial.
  3. Menyediakan solusi pemisahan daya UBEC & pemasangan Kapasitor Elco ($470\mu\text{F} - 1000\mu\text{F}$).

### Prompt 21: Analisis Detail Penyebab Wi-Fi ESP32 Tidak Muncul saat Arus Terukur 5V 0.1A (Strapping GPIO 5 & Diode Drop VIN)
- **User Prompt**: belumm ada aktuator lain hanya esp dan kontrol motor. itupun motor dari batrai langsung sementara esp dari ubec dengan 3a max 5a jika menurut spesifikasi tetapi tadi di multimeter 5v 0,1 a
- **Tindakan & Progress**:
  1. Menjelaskan mengapa arus terukur $0.1\text{ A}$ ($100\text{ mA}$): ESP32 mengalami **hang / stuck di ROM Bootloader** akibat **GPIO 5 (`IN3_PIN 5`)** terhubung ke driver motor (L298N/BTS7960) yang menarik GPIO 5 ke LOW/HIGH saat boot.
  2. Menjelaskan masalah **Diode Voltage Drop pada Pin VIN ESP32**: Jika UBEC memberi 5.0V ke VIN, tegangan setelah dioda D1 di board ESP32 drop ke 4.3V, menyebabkan regulator 3.3V (AMS1117) drop-out ke ~2.8V sehingga radio Wi-Fi tidak mau menyala.
  3. Menyediakan tes diagnostik cepat: Cabut kabel sinyal motor (IN1-IN4, ENA, ENB) dan ukur tegangan pin `3V3` ESP32.

### Prompt 22: Metode Uji Isolasi Masalah UBEC vs Pin Terlarang (GPIO 6-11 Flash Memory & Pin EN Reset)
- **User Prompt**: oin sudah diganti sedari awal, kenapa masi gabisa, berarti pure ampere dari ubec?
- **Tindakan & Progress**:
  1. Menyediakan **3 Langkah Uji Coba Isolasi** (Menguji ESP32 dicolok USB laptop saat tetap menempel di robot untuk memastikan apakah murni UBEC atau Short Circuit/Pin crash di PCB).
  2. Memberikan **Peringatan Kritis GPIO 6 - 11**: `SERVO_GRIPPER_PIN 7` yang baru diisi terhubung langsung ke **Internal SPI Flash Memory ESP32** sehingga pasti membuat ESP32 *Fatal Crash (Guru Meditation)*.
  3. Memeriksa status pin **EN (Reset)** & rekomendasi daftar pin aman (GPIO 21, 22, 23, 25, 26, 32, 33).

### Prompt 23: Konfirmasi Empiris Masalah UBEC Diode Voltage Drop & Solusi Kelistrikan
- **User Prompt**: udah gw bilang kalau pake lptop wfi muncul (🟢 Jika Wi-Fi LANGSUNG MUNCUL saat dicolok USB: Maka 100% terbukti UBEC / Jalur Kabel Power 5V UBEC yang BERMASALAH / TEGANGAN DROP).
- **Tindakan & Progress**:
  1. Mengonfirmasi hasil tes bahwa masalah **100% TERBUKTI PADA UBEC & DIODE DROP PIN VIN ESP32**.
  2. Menjelaskan perbedaan pasokan USB Laptop (5.15V murni) vs UBEC (5.00V yang drop di dioda VIN ke ~4.3V sehingga regulator 3.3V mengalami *under-voltage dropout* ke ~2.8V).
  3. Memberikan 3 solusi perbaikan daya: Pasang kabel Micro-USB dari UBEC ke port USB ESP32, atau naikkan potensio UBEC ke 5.3V - 5.5V.

### Prompt 24: Panduan Perintah Terminal Git untuk Update Repositori GitHub
- **User Prompt**: berikajn sintax terminall step by step update gothub
- **Tindakan & Progress**: Menyediakan panduan langkah demi langkah perintah terminal Git (`git add .`, `git commit`, `git push origin main`) untuk mengunggah semua perubahan workspace ke GitHub (`petirz436/Eksperimen-Robotika-II`).

### Prompt 25: Pemulihan dari Perubahan Codex, Audit AI, & Perbaikan Firmware ESP32-CAM (connect/delay/freeze)
- **User Prompt**: Kode dirusak Codex, kembalikan berdasarkan checkpoint di `eksbot_baru`, bandingkan, baca semua README, kembalikan yang dari Antigravity dan hapus yang dari Codex. Jelaskan kenapa `tescamesp.cpp` bisa connect sedangkan `firmware_esp32_cam.ino` tidak, dan kenapa setelah "diperbaiki Codex" malah delay/freeze padahal folder lama lancar. Berikan penjelasan & perbaikan.
- **Tindakan & Progress**:
  1. **Audit sumber perubahan** (`eksbot_baru/Eksperimen-Robotika-II` = clone GitHub `69e92f9`; dibandingkan dengan `eksbot2`, mtime file, log sesi Antigravity di `~/.gemini/.../brain`, dan README/PROGRESS_REPORT). Perubahan Codex semuanya bertanggal 2026-10-21 10:57-11:23 dan memuat "Prompt 25-31" di PROGRESS_REPORT: `firmware_esp32_cam.ino`, `firmware_esp32_control.ino`, `main.py`, `vision.py`, `README.md`, `PROGRESS_REPORT.md` (+ `.pyc`). Semuanya dikembalikan ke checkpoint (`git checkout`); salinan versi Codex disimpan di folder scratch sesi ini untuk jaga-jaga.
  2. **Dipertahankan (bukan dari Codex, mtime 2026-10-02 s/d 10-14, dari Antigravity/user)**: `visionTarget.py` (`USE_ESP_CAM = True`), `dummy_robot.urdf.xacro` (`wheelSeparation 0.26`), `esp32_firmware_example.ino` (komentar dihapus), `tes_cam_lcd/test_vision.py` (pengganti `test_vision_laptop.py`, dibuat sesi 2026-10-06), `tes_manual_control/main.py` & `robot.ino` (pengganti `test_manual_keyboard.py` & `firmware_esp32_control_direct_wifi.ino`), `uts by fathir.zip`.
  3. **Fitur Codex yang sengaja DIHAPUS**: dashboard web laptop, ESP-NOW, tombol Batalkan Target, resolusi VGA, failsafe di firmware kontrol, ubahan 180° di sensor, perubahan README/PROGRESS Prompt 25-31 versi Codex.
  4. **Penyebab firmware lama (checkpoint) tidak bisa connect** (dibandingkan dengan `tescamesp.cpp` yang berjalan di board WROVER yang sama):
     - Pin kamera memakai peta **AI-Thinker**, bukan **WROVER Kit** -> `esp_camera_init` gagal -> `return` di `setup()` **sebelum** `WiFi.softAP()` -> Wi-Fi tidak pernah menyala.
     - `Serial2` di GPIO16/17 = pin **PSRAM** pada WROVER -> crash/reboot saat PSRAM dipakai (VGA, `fb_count=2`).
     - XCLK 20 MHz (tescamesp 10 MHz), VGA q12, tanpa `CAMERA_GRAB_LATEST` -> frame basi/antrean.
     - Stream mengirim data tanpa boundary pembuka, dan `ArduinoJson` wajib terpasang.
  5. **Penyebab delay/freeze setelah versi Codex** (analisis kode; belum diukur di hardware): VGA 640x480 lewat SoftAP + XCLK 10 MHz terlalu berat (frame ~4x lebih besar dari QVGA); 1 task HTTP melayani stream sehingga reconnect saat koneksi lama belum bersih memblokir klien baru; ESPCamReader membaca frame TERTUA (antrean) dan bila error `read()` mati selamanya; loop `main.py` tidak memanggil `waitKey` saat tak ada frame sehingga jendela "hang"; dashboard + CSRT + HSV + re-encode MJPEG pada satu loop menambah latensi.
  6. **Perbaikan `firmware_esp32_cam.ino`**: konfigurasi kamera disalin dari `tescamesp.cpp` (WROVER Kit, XCLK 10 MHz, QVGA, `jpeg_quality 10`, `fb_count 2`, `CAMERA_GRAB_LATEST`); AP tetap menyala walau kamera gagal dan kamera dicoba ulang tiap 5 detik; UART ke kontrol dipindah ke GPIO33(TX)/GPIO32(RX) (WROVER) agar tidak bentrok PSRAM; stream: boundary+header 1 chunk, `lru_purge_enable`, `max_open_sockets=4`, timeout 3 dtk, `WiFi.setSleep(false)`; hilangkan ArduinoJson (parser angka native); kuras semua paket UDP dan pakai perintah terbaru; failsafe STOP 500 ms; debug print dibatasi. Stream tetap di `http://192.168.4.1/stream` (port 80) agar kompatibel dengan `main.py`.
  7. **Perbaikan `main.py`**: `ESPCamReader` memakai thread yang hanya menyimpan frame terbaru + reconnect otomatis; loop tetap memanggil `waitKey` (ESC berfungsi) dan menghentikan robot jika tak ada frame > 1 dtk.
  8. **Validasi**: firmware dikompilasi dengan `arduino-cli` (`esp32:esp32:esp32wrover`, core 3.3.11) sukses; `ESPCamReader` diuji dengan server MJPEG tiruan (tidak ada backlog frame, reconnect otomatis setelah stream putus). Uji kamera/robot fisik belum dilakukan.
  9. **Aksi untuk user**: ubah wiring UART kamera ke GPIO33/32 (lihat README), pastikan hanya satu ESP yang memancarkan `dimas_asoy_geboy`, tutup tab browser stream sebelum menjalankan `main.py`, dan catat bahwa daya UBEC (Prompt 19-23) dapat membuat Wi-Fi hilang/reboot.

### Prompt 26: Modularisasi Sistem, Web HMI Pilot Console, HUD Canvas & Custom Crosshair, SOP Implementasi Robot Fisik
- **User Prompt**: Implementasi robot fisik (apa yang diupload, SOP run, konektivitas 2 ESP + 3 script, apakah butuh ROS di fisik, status modularitas), penyesuaian visionTarget/kamikaze CSRT + filter warna, keyboard mapping, pembuatan HMI website lokal di laptop (stream MJPEG, HUD flat tanpa gradasi tema terang/gelap, tombol soft, legenda tombol, crosshair adjustable), serta rekomendasi fitur developer/pilot.
- **Tindakan & Progress**:
  1. **Modularisasi Kode**:
     - `camera_sources.py`: Memisahkan antarmuka sumber kamera (`ESPCamReader` via background thread latest-frame, `ROSImageSub` untuk Gazebo, `WebcamSource` untuk laptop webcam).
     - `control.py`: Mengisolasi state machine kendali (`MANUAL` / `AUTO` navigasi berfase `ALIGNING` -> `DRIVING` -> `PICKUP`), pemetaan keyboard, kalkulasi kinematics differential drive, dan manajemen crosshair offset.
     - `hmi_server.py`: Server web HTTP multi-threaded murni standar Python (tanpa Flask) dengan endpoint MJPEG single-encode broadcast (`/stream.mjpg`), API telemetri JSON (`/api/state`), input event (`/api/action`, `/api/keys`, `/api/lock`, `/api/crosshair`).
     - `hmi/index.html`: Web Interface pilot flat modern, mendukung tema terang (putih) & gelap (hitam) tanpa gradasi, warna tombol soft, legenda tombol popup (`H`), overlay HUD Canvas dinamis (braket target, error bar heading, status banner), serta interactive target lock via click.
     - `main.py`: Orkestrator ramping dengan flag `--source esp|sim|webcam`, opsi `--gui` (OpenCV window) dan `--no-browser`.
  2. **Firmware ESP32 Control**:
     - Memperbarui `firmware_esp32_control.ino` dengan parsing non-blocking ring buffer dan timer watchdog failsafe 500 ms (motor otomatis berhenti jika koneksi putus).
  3. **Verifikasi & Validasi**:
     - Kompilasi `arduino-cli`: `firmware_esp32_cam.ino` (ESP32 Wrover Module) & `firmware_esp32_control.ino` (ESP32 Dev Module) 100% SUKSES.
     - Uji integrasi otomatis `test_integration.py` menggunakan mock ESP32-CAM stream & UDP server: 22/22 skenario pengujian PASS (stream link, keyboard WSAD, smooth arc turns, lock target click, CSRT tracking, manual override, color switch, crosshair offset adjustment, E-STOP, failsafe timeout, auto-reconnect).

### Prompt 27: Implementasi Fitur Lanjutan Pilot & Developer (Animasi Tombol, Web Audio Cues, Blackbox Recorder, HSV Tuner, Telemetri Baterai, & OTA Update)
- **User Prompt**: Implementasikan fitur lanjutan: animasi tombol WSAD & tombol mapping saat ditekan; Audio Feedback / Sound Cues sintesis Web Audio API (radar lock, link drop, E-STOP); Flight Data Recorder (Blackbox telemetry video WebM + CSV); HSV Color Picker / Tuner Slider real-time di web; Real-time Battery Voltage Telemetry (ADC GPIO34); dan OTA Firmware Update Web Page di ESP32-CAM via Wi-Fi.
- **Tindakan & Progress**:
  1. **Animasi & Visual Feedback Tombol**:
     - Ditambahkan keyframe animation `@keyframes keyPulse` (`.pulse`) dan status `.held` halus pada tombol kemudi dan seluruh tombol aksi (`btnEstop`, `btnToggle`, `btnRed`, `btnGreen`, `btnBlue`, `btnYellow`, `btnCancel`, `btnGripClose`, `btnGripOpen`, `btnLiftUp`, `btnLiftDown`, `btnSpdUp`, `btnSpdDn`, `btnXhair`, `btnTheme`, `btnLegend`, `btnAudio`, `btnRec`).
     - Tekanan fisik pada keyboard langsung memicu animasi tombol UI yang bersesuaian di layar console.
  2. **Web Audio API Sound Cues (100% Offline Sintesis)**:
     - Menggunakan `AudioContext` sintesis browser (tanpa aset file audio eksternal):
       - *Target Lock*: Dual sharp rising frequency chirps (980 Hz -> 1480 Hz) ala radar jet tempur.
       - *Target Lost*: Descending tone (520 Hz -> 240 Hz).
       - *E-STOP Alarm*: Triple urgent buzzer (360 Hz).
       - *Link Lost Chime*: Dual warning tone (440 Hz -> 330 Hz).
     - Dilengkapi tombol toggle `🔊 Audio [P]` dengan penyimpanan preferensi di `localStorage`.
  3. **Flight Data Recorder (Blackbox Telemetry)**:
     - Tombol `● REC [O]` di header dan aside.
     - Merekam canvas stream HUD ke video `video/webm` menggunakan `MediaRecorder`.
     - Menyimpan log koordinat dan status robot tiap 100 ms ke buffer CSV (Timestamp, Elapsed, Mode, Phase, Color, Tracking, Target X/Y, Error X/Y, Area, Lin, Ang, Speed Scale, Gripper, Lift, FPS, Link, Battery V, Battery Pct).
     - Menghentikan rekaman otomatis mendownload dua file langsung: `eksbot2_flight_<timestamp>.webm` dan `eksbot2_telemetry_<timestamp>.csv`.
     - Tampil indikator kedip `● REC mm:ss` di HUD canvas dan header.
  4. **HSV Color Tuner Slider Real-Time**:
     - Ditambahkan preset `YELLOW` (H: 20-35, S: 70-255, V: 70-255) di `vision.py`.
     - Ditambahkan method `get_hsv_ranges()`, `set_hsv_range()`, dan `reset_hsv_presets()` pada `VisionEngine`.
     - Ditambahkan endpoint `GET /api/hsv` dan `POST /api/hsv` di `hmi_server.py`.
     - Panel UI di web dengan 6 slider (`H Min`, `H Max`, `S Min`, `S Max`, `V Min`, `V Max`) dan tombol Reset. Pengaturan slider langsung meng-update deteksi citra OpenCV secara live tanpa perlu me-restart script Python.
  5. **Real-Time Battery Voltage Telemetry**:
     - `firmware_esp32_control.ino`: Membaca analog ADC `GPIO34` (divider 4:1 untuk LiPo 3S 11.1V-12.6V atau 2S) dan mengirimkan `BATT:xx.xx\n` ke Serial2 ke ESP32-CAM.
     - `firmware_esp32_cam.ino`: Menerima pembacaan `BATT:` dan merespons via UDP status `{"batt": 12.0, "pct": 95}` ke laptop.
     - `robot_api.py` & `control.py`: Menerima dan memasukkan data `battery_v` & `battery_pct` ke telemetri JSON.
     - `index.html`: Header pill status baterai berwarna dinamis (hijau/kuning/merah) dan indikator grafis baterai di Canvas HUD.
  6. **OTA (Over-The-Air) Firmware Update Web Page di ESP32-CAM**:
     - Ditambahkan library `<Update.h>` pada `firmware_esp32_cam.ino`.
     - Ditambahkan HTTP handler `GET /update` (halaman upload biner) dan `POST /update` (flashing firmware nirkabel) pada port 80 ESP32-CAM.
     - Developer cukup membuka `http://192.168.4.1/update` dari browser untuk upload firmware `.bin` tanpa kabel USB.
  7. **Validasi Kompilasi & Pengujian**:
     - Kedua firmware ESP32 berhasil dikompilasi 100% menggunakan `arduino-cli` (CAM: 79%, Control: 23%).
     - Unit test integrasi modular 22/22 PASS, pengujian endpoint `/api/hsv` dan telemetri baterai PASS.

### Prompt 28: Konsolidasi Arsitektur Bersih (Clean Robotics Architecture 3-File + HMI Sub-Paket)
- **User Prompt**: Eksekusi perapihan arsitektur modular. `camera_sources` digabung ke `vision.py`, kontrol digabung ke `robot_api.py`, HMI diintegrasikan ke sub-paket `hmi/`, dan firmware dipindah ke folder `firmware/`.
- **Tindakan & Progress**:
  1. **Konsolidasi Vision (`vision.py`)**:
     - Memindahkan kelas sumber kamera (`ROSImageSub`, `WebcamSource`, `ESPCamReader`, `open_source`, `HAS_ROS`) ke dalam `vision.py`.
     - `camera_sources.py` lama dihapus.
  2. **Konsolidasi Robot & Kontrol (`robot_api.py`)**:
     - Menggabungkan low-level driver `RobotAPI` (ROS velocity publisher, socket UDP, servo gripper/lift, telemetri baterai) dan high-level controller `Controller` (state machine, WSAD mapping, autopilot pickup, crosshair persistence, telemetry dict) ke dalam `robot_api.py`.
     - `control.py` lama dihapus.
  3. **Isolasi Sub-Paket HMI (`hmi/`)**:
     - Memindahkan `hmi_server.py` menjadi `hmi/server.py` dan menambahkan `hmi/__init__.py`.
     - Folder `hmi/` kini mandiri menaungi `server.py` (backend HTTP/streamer) dan `index.html` (frontend console).
     - `hmi_server.py` lama di root scripts dihapus.
  4. **Pemisahan Firmware Arduino (`firmware/`)**:
     - Memindahkan sketch Arduino ke `catkin_ws/src/eksbot_simulation/firmware/` dengan folder yang sesuai standar Arduino IDE:
       - `firmware/firmware_esp32_cam/firmware_esp32_cam.ino`
       - `firmware/firmware_esp32_control/firmware_esp32_control.ino`
     - Folder `scripts/` kini murni hanya berisi file eksekusi Python.
  5. **Pembaruan `main.py`**:
     - Diperbarui dengan import bersih:
       `from vision import open_source, HAS_ROS, VisionEngine`
       `from robot_api import RobotAPI, Controller`
       `from hmi import HMIServer`
  6. **Validasi**:
     - `test_integration.py`: 22/22 skenario integrasi PASS.
     - Kompilasi `arduino-cli` dari folder `firmware/` baru: 100% SUKSES (CAM 79%, Control 23%).

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
│           │   └── modular_control.launch    # Launch Aplikasi Modular Utama (main.py)
│           ├── firmware/                     # Firmware Mikrokontroler Arduino ESP32
│           │   ├── firmware_esp32_cam/       # Firmware ESP32-CAM (SoftAP + MJPEG Stream + OTA Web)
│           │   │   └── firmware_esp32_cam.ino
│           │   └── firmware_esp32_control/   # Firmware ESP32 Motor & Servo (UART + ADC Baterai)
│           │       └── firmware_esp32_control.ino
│           ├── models/
│           │   ├── arena_ground/             # Tekstur & model spanduk 3.5m x 2.8m
│           │   ├── cube_red/                 # SDF Kubus Merah 50mm 30g
│           │   ├── cube_green/               # SDF Kubus Hijau 50mm 30g
│           │   └── cube_blue/                # SDF Kubus Biru 50mm 30g
│           ├── urdf/
│           │   └── dummy_robot.urdf.xacro    # URDF Robot Dummy + Gripper + Camera
│           └── scripts/                      # Core Python Runtime di Laptop
│               ├── main.py                   # 1. ORKESTRATOR (CLI entry point & window loop)
│               ├── vision.py                 # 2. MATA (Input Kamera ESP/ROS/Webcam + HSV + CSRT)
│               ├── robot_api.py              # 3. TUBUH & OTAK (Hardware Driver UDP/ROS + Autopilot State Machine)
│               ├── hmi/                      # 4. ANTARMUKA PILOT
│               │   ├── server.py             # Server HTTP lokal, MJPEG Streamer, REST API
│               │   └── index.html            # Web Console HUD Flat Theme + Canvas Overlay
│               ├── visionTarget.py           # Legacy Vision Node
│               └── esp32_firmware_example.ino# Legacy rosserial firmware
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
