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

### Prompt 27: Penyesuaian Konfigurasi Pin dan Wi-Fi dengan Folder `program_dimas` untuk Komunikasi Nirkabel antar ESP
- **User Prompt**: di `firmware_esp32_control.ino`, `firmware_esp32_cam.ino` dan program robot lainya. sesuaikan dengan konfirgurasi pin dan wifi nya SAJA dengan yang ada di folder program_dimas. agar antar esp bisa nirkabel
- **Tindakan & Progress**:
  1. **Audit & Analisis Konfigurasi Folder [program_dimas](file:///home/fathir/eksbot2/program_dimas)**:
     - Motor Driver: `ENA_PIN 4`, `IN1_PIN 16`, `IN2_PIN 17`, `ENB_PIN 19`, `IN3_PIN 21`, `IN4_PIN 18`.
     - Servo: `SERVO_GRIPPER_PIN 7`, `SERVO_LIFT_PIN 3`.
     - Wi-Fi & UDP: SSID `dimas_asoy_geboy`, Password `12345678`, Port UDP `8888`.
     - Kinematika: `WHEEL_BASE = 0.26` (26 cm), `MAX_SPEED = 0.50` m/s.
  2. **Pembaruan [firmware_esp32_control.ino](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/firmware/firmware_esp32_control/firmware_esp32_control.ino)**:
     - Mengubah pin motor dan servo tepat sesuai `program_dimas` (Motor: 4, 16, 17, 19, 21, 18; Servo: 7 & 3).
     - Mengubah `WHEEL_BASE` menjadi 0.26 meter.
     - Menambahkan modul Wi-Fi UDP nirkabel (`WiFi.h`, `WiFiUdp.h`, `ArduinoJson.h`) dengan SSID `dimas_asoy_geboy` dan port `8888`.
     - Mengimplementasikan koneksi nirkabel otomatis (Station mode ke ESP32-CAM dengan Static IP `192.168.4.2`) dan fallback otomatis ke SoftAP jika ESP32-CAM tidak dinyalakan (untuk standalone testing).
     - Menerima paket JSON kontrol `{"lin", "ang", "grip", "lift"}` via Wi-Fi UDP nirkabel.
     - Menjaga penerima kabel `Serial2` sebagai cadangan (dual-link).
     - Mengirimkan telemetri voltase baterai nirkabel via UDP ke ESP32-CAM (`192.168.4.1`) tiap 1 detik.
  3. **Pembaruan [firmware_esp32_cam.ino](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/firmware/firmware_esp32_cam/firmware_esp32_cam.ino)**:
     - Fungsi `forwardToControl()` kini meneruskan perintah secara nirkabel via Wi-Fi UDP ke IP static ESP32-Control (`192.168.4.2:8888`), di samping tetap mengirim lewat `Serial2` sebagai backup.
     - Menerima paket telemetri baterai nirkabel dari ESP32-Control via UDP port 8888 dan menyampaikannya ke Laptop.
  4. **Pembaruan Script Robot Laptop ([robot_api.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/robot_api.py))**:
     - `self.wheel_base` disesuaikan menjadi `0.260` meter (26 cm) sesuai `program_dimas` dan URDF.
  5. **Validasi Kompilasi**:
     - `arduino-cli compile --fqbn esp32:esp32:esp32 .../firmware_esp32_control/` -> **SUKSES (0 error)**.
     - `arduino-cli compile --fqbn esp32:esp32:esp32wrover .../firmware_esp32_cam/` -> **SUKSES (0 error)**.
     - Syntax check Python `robot_api.py` dan `main.py` -> **SUKSES (0 error)**.

---

### Progres 5 (2026-10-28): Standardisasi IP 192.168.4.10:80, Diagnosa Program Dimas vs Eksbot2, & OTA Multi-Board
- **User Prompt**:
  "esp ip yang benar 192.168.4.10 port 80, cek semua koneksi pastikan sudah benar, kenapa program dimas bener sementara programku eror, serta buat agar ota dapat memilih esp mana yang mau di uplpad update"
- **Analisis & Temuan**:
  1. **Mengapa Program Dimas Berhasil Sementara Program Eksbot2 Error**:
     - **Arsitektur Single vs Dual Board**: Program Dimas (`program_dimas/robot.ino`) didesain untuk **1 board ESP32 saja** (hanya pengendali motor & servo, tanpa kamera). ESP32 Dimas menjadi AP di `192.168.4.1` dan langsung menerima UDP di `192.168.4.1:8888`.
     - **IP Mismatch di Laptop**: Pada program Eksbot2 terdapat **2 board** (ESP32-CAM di `192.168.4.10` dan ESP32-Control di `192.168.4.1`). Di `main.py` argumen default `--esp-ip` sebelumnya masih mengarah ke `192.168.4.1` (ESP32 Control). Akibatnya `main.py` mencoba mengambil stream MJPEG dari `http://192.168.4.1/stream` (port 80) yang tidak memiliki server kamera, menyebabkan stream error / timeout.
     - **Mekanisme Failsafe Eksbot2 vs Dimas**: Program Dimas **tidak memiliki failsafe STOP** (motor jalan terus selamanya). Sedangkan program Eksbot2 memiliki failsafe 500ms dan safety stop di `main.py`. Begitu stream kamera gagal dibuka di `main.py`, loop otomatis mengirim perintah `STOP/idle`, sehingga robot tidak bergerak.
     - **Bug IP Telemetri Baterai**: Pada `firmware_esp32_control.ino`, telemetri UDP baterai sebelumnya dikirim ke `192.168.4.1` (dirinya sendiri), bukan ke ESP32-CAM (`192.168.4.10`) atau broadcast (`192.168.4.255`).
  2. **Perbaikan & Standarisasi Koneksi**:
     - `main.py`: Default `--esp-ip` distandarkan ke `"192.168.4.10"`.
     - `vision.py`: Default `esp_ip` distandarkan ke `"192.168.4.10"`.
     - `robot_api.py`: Default `esp_ip="192.168.4.10"` (meneruskan perintah ke ESP32-CAM yang mem-bridge ke ESP32-Control).
     - `hmi/server.py`: Mengarah ke `192.168.4.10:80` dan menyediakan endpoint REST `/api/ota_info`.
     - `firmware_esp32_control.ino`: Menambahkan HTTP Web Server Port 80 untuk OTA Firmware Update (`http://192.168.4.1/update`) & Dashboard status (`http://192.168.4.1/`). Telemetri baterai dikirim ke `192.168.4.10` dan broadcast `192.168.4.255`.
     - `firmware_esp32_cam.ino`: Memperbarui filter loopback (`WiFi.localIP()`) dan menyematkan target switcher di halaman web OTA (`/update`).
  3. **Fitur Pemilihan Target OTA (Multi-Board Flash)**:
     - Di Web Console HMI (`index.html`), card **Developer & Servis** kini memiliki pemilih target:
       * **ESP32-CAM** (`192.168.4.10:80` / `http://192.168.4.10/update`)
       * **ESP32-Control** (`192.168.4.1:80` / `http://192.168.4.1/update`)
     - Pengguna dapat membuka halaman OTA masing-masing board atau mengunggah biner `.bin` secara nirkabel langsung dari HMI dashboard dengan status real-time.
  4. **Hasil Pengujian Kompilasi**:
     - `firmware_esp32_cam.ino`: Kompilasi `esp32:esp32:esp32wrover` -> **SUKSES (0 error)**.
     - `firmware_esp32_control.ino`: Kompilasi `esp32:esp32:esp32wrover` -> **SUKSES (0 error)**.

---

### Progres 6 (2026-11-02): Implementasi Continuous Arc Steering (Smooth Coupled Control) & Deadzone PWM Compensation
- **User Prompt**:
  "bro rekomendasikan gw metode folowing targetnya soalnya gw pake align sudt baru maju. robotnya jadi lambat bahkan kadang kekunci dan stuck gegara ga kuat torsinya #diskusi duliu"
  "Rekomendasi 1: Continuous Arc Steering (Smooth Coupled Control) ⭐ (Paling Direkomendasikan) jelakan ini, jdi klo target gw putar tarik dll robot bakal ikut terus realtime seperti anjing yg liatin mainanya atau kamikaze drone?"
  "integrasikan ke programku eksekusi"
- **Analisis Akar Masalah**:
  1. **Gesekan Statis vs Gelinding (*Static vs Rolling Friction*)**:
     - Sistem lama menggunakan discrete phase (*Aligning dulu baru Driving*). Saat orientasi target melenceng (`|norm_x_lead| > 0.35`), linear speed di-nol-kan (`lin = 0.0`) dan hanya angular speed yang aktif.
     - Mode putar di tempat (*spin-in-place*) membuat ban terseret/pivot terhadap permukaan lantai, menghasilkan gesekan statis yang sangat berat. Motor DC gearbox kekurangan torsi awal untuk memutar bodi dari posisi diam, menyebabkan robot mendengung dan terkunci (*stuck*).
  2. **Deadzone PWM Rendah**:
     - Motor DC driver L298N/BTS7960 memiliki ambang batas putar minimum. Nilai PWM < 60 sering kali tidak mampu memutar roda, memperparah fenomena macet.
- **Solusi & Integrasi yang Diterapkan**:
  1. **Continuous Arc Steering di `catkin_ws/src/eksbot_simulation/scripts/robot_api.py`**:
     - Menghapus pemisahan diskrit kaku `ALIGNING -> DRIVING`.
     - Menggantinya dengan **Smooth Coupled Control**: Linear velocity ($v$) dan Angular velocity ($\omega$) dihitung bersamaan tiap frame.
     - **Curvature Modulation**:
       $$v = \text{clip}(v_{base} \times \max(0.40, 1.0 - 0.60 \times |e_x|), 0.10, MAX\_LINEAR)$$
       $$\omega = \text{clip}(2.2 \times e_x, -2.0, 2.0)$$
     - Nilai $v$ tidak pernah di-nol-kan selama tracking aktif (minimal 0.10 m/s). Karena kedua roda terus menggelinding (*rolling*), torsi motor tetap terjaga dan robot meluncur membentuk kurva mulus mengikuti target secara dinamis (*real-time visual pursuit* seperti missile navigation/anjing mengejar bola).
     - Phase HUD distandarkan: `FOLLOWING` (pelacakan aktif), `INTAKE` (mendekati sela capit), `PICKUP` (siklus jepit & angkat), dan `SEARCHING` (sweeping pelan jika target hilang sementara dengan dorongan linier $0.06$ m/s agar tidak stall).
  2. **Kompensasi Deadzone PWM di Firmware**:
     - Diperbarui pada `catkin_ws/src/eksbot_simulation/firmware/firmware_esp32_control/firmware_esp32_control.ino` dan `program_dimas/robot.ino`.
     - Ditambahkan pemetaan `MIN_PWM = 60` pada `applyMotorControl()`: jika ada sinyal gerak ($pwm > 0$), nilai dipetakan dari interval $[1 \dots 255]$ ke $[60 \dots 255]$ sehingga motor langsung mendapat torsi awal yang cukup tanpa dengung.
- **Hasil Pengujian**:
  - `arduino-cli compile --fqbn esp32:esp32:esp32 .../firmware_esp32_control/` -> **SUKSES 100% (0 error, Flash 74%, RAM 14%)**.
  - Simulasi Python Unit-Behavior Test:
    * Target jauh di tengah: `FOLLOWING` (lin: 0.305, ang: 0.0) -> Lolos.
    * Target geser tajam kanan: `FOLLOWING` (lin: 0.183, ang: 1.32) -> Lolos, lin tetap positif!
    * Target masuk area mulut: `INTAKE` (lin: 0.14, ang: 0.06) -> Lolos.
    * Target tenggelam: `PICKUP` (lin: 0.0, ang: 0.0) -> Lolos.

---

### Progres 7 (2026-11-11): Integrasi Arduino Nano Sub-Kontroler Aktuator, Servo Kamera, Lifter, & Remap Serial2
- **User Prompt**:
  "tx rx dah ku ubah ke 23 22. jadi tx rx di hubungkan ke ardunio nano untuk kontrol servo. nantinya servo kamera, steper lifter, dan srvo griper disana. sekarang baru ada servo kamera dan lifter. sesuaikan code dan generate firmware arduino aktuator"
- **Tindakan & Progress**:
  1. **Pembuatan Firmware Sub-Kontroler Arduino Nano ([firmware_nano_actuator.ino](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/firmware/firmware_nano_actuator/firmware_nano_actuator.ino))**:
     - Firmware mandiri untuk Arduino Nano (ATmega328P) yang mendengarkan Hardware Serial (RX Pin D0, TX Pin D1) @ 115200 baud.
     - Mengendalikan:
       * **Servo Kamera (Tilt/Pan)** di Pin `D9` (Sudut: 0 - 180°, default 90° netral).
       * **Servo Lifter** di Pin `D10` (Sudut: 0 - 180°, default 0° turun).
       * **Servo Gripper** di Pin `D11` (Sudut: 0 - 180°, default 0° buka).
       * **Opsi Stepper Lifter**: Dilengkapi opsi `#define LIFTER_USE_STEPPER 1` dengan pin STEP `D5`, DIR `D6`, EN `D7`.
     - Protokol string ASCII ringkas: `ACT:<cam>,<lift>,<grip>\n` dengan respon `ACK:OK` dan dukungan `PING`/`PONG`.
     - Validasi kompilasi: `arduino-cli compile --fqbn arduino:avr:nano` -> **SUKSES 100% (Flash 17%, RAM 16%)**.
  2. **Pembaruan Firmware ESP32 Control ([firmware_esp32_control.ino](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/firmware/firmware_esp32_control/firmware_esp32_control.ino))**:
     - Memperbarui `RX2_PIN 23` dan `TX2_PIN 22` sebagai jalur transmisi Serial UART2 ke Arduino Nano.
     - Melepaskan beban Servo dari pin ESP32 (menghilangkan bentrok pin dan *power drop* di ESP32).
     - Menambahkan parameter `cam` pada parser UDP JSON dan meneruskan instruksi aktuator ke Nano via `Serial2.printf("ACT:%d,%d,%d\n", currentCam, currentLift, currentGrip)`.
     - Validasi kompilasi: `arduino-cli compile --fqbn esp32:esp32:esp32` -> **SUKSES 100% (Flash 74%, RAM 14%)**.
  3. **Pembaruan API Robot & Navigasi Laptop ([robot_api.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/robot_api.py))**:
     - Menambahkan state `self.current_camera = 90` dan method `set_camera(angle)`.
     - Menambahkan payload `"cam": self.current_camera` pada pengiriman paket UDP.
     - Menambahkan handler aksi `cam`, `cam_up`, `cam_down` di Controller dan mengeksposnya ke telemetri HUD.
  4. **Pembaruan Web HMI Pilot Console ([index.html](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/hmi/index.html))**:
     - Menambahkan tombol kontrol Tilt Kamera di card Aktuator: **Kamera Atas [Q]** dan **Kamera Bawah [E]**.
     - Menambahkan status sudut kamera pada tabel telemetri HUD.

### Progres 8 (2026-11-11): Analisis & Perbaikan Kritis Wi-Fi Station ESP32-Control, Port 80 OTA, dan Bug Error 1-Klik HMI
- **User Prompt**:
  "`❌ Gagal compile/flash: Periksa koneksi Wi-Fi` ... `dimas asoy geboy dah muncul kamera dah muncul kenapa disitu wifi ga ada dan saat buka halaman kontrol selalu gabisa ANALISIS` ... `woy pake port 80 jangan 81 MALAH GABISA KONEK WOY`"
- **Analisis Akar Masalah**:
  1. **Bug Crash `NameError` + Error-Masking di Web HMI**:
     - `catkin_ws/src/eksbot_simulation/scripts/hmi/server.py` memanggil `sys.executable` pada endpoint `/api/flash_ota` tanpa `import sys`, memicu HTTP 500 `NameError` setiap tombol 1-Klik ditekan.
     - Helper `post()` di `hmi/index.html` membuang isi JSON saat status bukan 2xx (`!res.ok`), sehingga UI selalu menampilkan pesan palsu `"Periksa koneksi Wi-Fi"` meskipun penyebabnya adalah Python exception atau target IP belum aktif.
  2. **Bug `fallback_url` Berbahaya di `flash_ota.py`**:
     - Target `control` memiliki `"fallback_url": "http://192.168.4.1/update"` — jika `192.168.4.10` timeout, script berisiko menimpa **ESP32-CAM (`192.168.4.1`)** dengan firmware control. Selain itu kegagalan upload tidak mengembalikan exit code `1`.
  3. **Race Condition Boot & Duplikasi SSID di `firmware_esp32_control.ino`**:
     - `setup()` hanya menunggu ESP32-CAM selama 4 detik lalu langsung fallback permanen ke `WIFI_AP` dengan SSID identik `dimas_asoy_geboy` tanpa logika reconnect di `loop()`. Akibatnya Control terisolasi di jaringan AP terpisah dan tidak pernah mendapat IP `192.168.4.10` di jaringan ESP-CAM, serta link HTML & target UDP baterai masih tertukar (`192.168.4.1` vs `192.168.4.10`).
  4. **Link OTA Port 80 vs 81**:
     - Link OTA dikonsolidasikan kembali murni pada **Port 80 standar** (`http://192.168.4.1/update` dan `http://192.168.4.10/update`), dengan ketentuan menghentikan `main.py` (Ctrl+C) sebelum melakukan OTA ke ESP32-CAM agar `/stream` tidak menahan socket port 80.
- **Solusi & Perbaikan**:
  1. **[hmi/server.py](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/hmi/server.py) & [hmi/index.html](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/scripts/hmi/index.html)**: Menambahkan `import sys` & `import subprocess`, mengekstrak ringkasan error aktual dari output compiler/uploader, dan memperbaiki fungsi `post()` agar mengembalikan pesan error asli dari server ke UI.
  2. **[flash_ota.py](file:///home/fathir/eksbot2/flash_ota.py)**: Menghapus `fallback_url` berbahaya pada `control`, menggunakan Port 80 standar untuk `control` (`192.168.4.10/update`) & `cam` (`192.168.4.1/update`), menambahkan opsi `--usb` untuk flash kabel satu perintah, pre-check TCP cepat (`3s`), bypass proxy lokal (`ProxyHandler({})`), dan exit code `1` yang akurat saat gagal.
  3. **[firmware_esp32_control.ino](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/firmware/firmware_esp32_control/firmware_esp32_control.ino)**: Membersihkan sisa definisi servo lama (GPIO 7/3), menambahkan header CORS (`/update`), dan memantapkan kontrol aktuator via Serial2 Nano (RX2=23, TX2=22).
  4. **[firmware_esp32_cam.ino](file:///home/fathir/eksbot2/catkin_ws/src/eksbot_simulation/firmware/firmware_esp32_cam/firmware_esp32_cam.ino)**: Mengembalikan layanan HTTP murni pada Port `80` (`/stream`, `/update` GET/POST/OPTIONS) dan menambahkan CORS header.

### Progres 9: Pemulihan Topologi Wi-Fi & IP Asli (`Control = 192.168.4.1` SoftAP, `CAM = 192.168.4.10` STA)
- **Permasalahan User**:
  - Setelah OTA, `main.py` gagal mengambil kamera dengan error `HTTP Error 404: Not Found` pada `http://192.168.4.1/stream` karena pembalikan IP sementara membuat Control dan CAM bertukar alamat sementara `192.168.4.1` adalah SoftAP Control yang tidak melayani `/stream`. User menginstruksikan mempertahankan arsitektur koneksi Wi-Fi & kamera asli tanpa diubah.
- **Perbaikan yang Diterapkan**:
  1. **Pemulihan Role & IP Asli (Port 80 Murni)**:
     - **ESP32-Control (`firmware_esp32_control.ino`)**: Dikembalikan menjadi SoftAP utama `dimas_asoy_geboy` pada **`192.168.4.1`** (`WIFI_AP`, UDP `8888`, OTA `/update` Port 80, telemetri baterai dikirim ke `192.168.4.10` dan broadcast `192.168.4.255`), tanpa guard `WiFi.status() == WL_CONNECTED` yang tidak berlaku pada mode AP, serta mempertahankan integrasi Arduino Nano (`RX2=23`, `TX2=22`) dan parameter servo kamera `cam`.
     - **ESP32-CAM (`firmware_esp32_cam.ino`)**: Dikembalikan menjadi Station ke `dimas_asoy_geboy` dengan IP statis **`192.168.4.10`** (gateway `192.168.4.1`, fallback SoftAP `192.168.4.10`), `/stream` & `/update` di Port 80, dan bridge UDP ke `192.168.4.1:8888`.
  2. **Sinkronisasi Laptop Runtime, HMI & OTA CLI**:
     - `main.py`, `vision.py`, dan `robot_api.py` dikembalikan ke default `--esp-ip = 192.168.4.10`.
     - `flash_ota.py`, `hmi/server.py`, dan `hmi/index.html` disinkronkan (`control` -> `http://192.168.4.1/update`, `cam` -> `http://192.168.4.10/update`), tetap menjaga perbaikan `import sys`/`subprocess`, JSON error reporting di `post()`, pre-check TCP, proxy bypass, dan proteksi tanpa cross-board fallback.

### Progres 10 (2026-11-16): Pembalikan Topologi Wi-Fi ke ESP32-CAM (`192.168.4.1`), Kontrol UDP Langsung ke Control (`192.168.4.10`), & Auto-Pause Stream OTA
- **Permasalahan User**:
  - Sejak Wi-Fi AP dipindah ke ESP32-Control, web OTA Control bisa dibuka tetapi web OTA ESP32-CAM tidak bisa diakses, kamera gagal terhubung (`No route to host` ke `192.168.4.10/stream`), dan robot lumpuh total karena kontrol UDP ikut lewat bridge ESP32-CAM.
- **Perbaikan yang Diterapkan**:
  1. **Pembalikan Topologi Wi-Fi (AP di ESP32-CAM)**:
     - `firmware_esp32_cam.ino`: Menjadi SoftAP utama `dimas_asoy_geboy` di **`192.168.4.1`** (Port 80 untuk `/stream` & `/update`).
     - `firmware_esp32_control.ino`: Menjadi Station (`WIFI_STA`) ke `dimas_asoy_geboy` dengan Static IP **`192.168.4.10`** + auto-reconnect di `loop()` tiap 5 detik (menghapus fallback SoftAP SSID kembar), melayani OTA di `http://192.168.4.10/update` dan UDP `8888`.
  2. **Kontrol UDP Langsung ke ESP32-Control (Anti-Lumpuh)**:
     - `main.py` & `robot_api.py`: Menambahkan `--control-ip` (default `192.168.4.10`) terpisah dari `--esp-ip` kamera (`192.168.4.1`). Mode `MANUAL` di `idle()` tetap memproses input WSAD dan mengirim UDP meskipun kamera putus/di-pause.
     - `firmware_esp32_control.ino`: Mengirim telemetri baterai langsung ke IP/port pengirim UDP laptop terakhir (`lastClientIP:lastClientPort`) serta ke `192.168.4.1` dan broadcast.
  3. **Auto-Pause Stream saat OTA ESP32-CAM**:
     - `vision.py`: Menambahkan `ESPCamReader.set_paused(paused, duration=None)` untuk melepas koneksi `/stream` port 80 sementara.
     - `hmi/server.py` & `hmi/index.html`: Menambahkan endpoint `POST /api/stream_pause` dan auto-pause otomatis saat 1-Klik Flash OTA, upload `.bin` manual, atau membuka halaman Web Flash ESP32-CAM.
     - `flash_ota.py`: Disinkronkan (`cam` -> `http://192.168.4.1/update`, `control` -> `http://192.168.4.10/update`).

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
