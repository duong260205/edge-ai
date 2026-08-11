# 🔐 Edge AI — Smart Door with Dual Authentication (Voice + Face)

Hệ thống **khóa cửa thông minh xác thực 2 lớp** chạy hoàn toàn trên **ESP32-S3** (Freenove ESP32-S3 WROOM Camera Module), sử dụng **AI trên thiết bị (Edge AI)**:

- 🔊 **Lớp 1 — Voice Authentication:** Nhận diện giọng nói chủ nhà bằng mô hình CNN (~13.6K tham số, INT8 ~12KB) chạy trên **TensorFlow Lite Micro**.
- 👤 **Lớp 2 — Face Recognition:** Nhận diện khuôn mặt bằng mô hình **ESP-DL MobileFaceNet** (pre-trained từ Espressif).
- 🚪 **Output:** Servo mở/đóng cửa + đèn LED RGB WS2812 báo trạng thái.
- 🌐 **Web UI:** Giao diện web tích hợp để đăng ký khuôn mặt, giọng nói, xem camera trực tiếp và chỉnh ngưỡng.

> Chỉ khi **cả giọng nói VÀ khuôn mặt** đều khớp thì cửa mới mở — bảo mật cao hơn nhiều so với xác thực đơn lớp.

---

## ✨ Tính năng chính

| Tính năng | Mô tả |
|-----------|-------|
| 🎤 Voice Authentication | Mic INMP441 (I2S), MFCC 32×13, CNN INT8 ~12KB, ngưỡng mặc định 0.7 |
| 👤 Face Recognition | ESP-DL MSRMNP detector + MobileFaceNet recognizer, tối đa 10 người, 5 template/người |
| 🔄 State machine | STANDBY → VOICE_TRIGGERED → FACE_AUTH → DOOR_OPEN, tự quay về STANDBY |
| 💡 LED RGB WS2812 | Xanh cố định = chờ FaceID, xanh nháy = thành công, đỏ nháy = thất bại |
| 🚪 Servo điều khiển cửa | PWM 50Hz (LEDC), mở 90°, đóng 0°, mở trong 5 giây |
| 🌐 Web Server | Port 80 — stream camera, enroll face/voice, chỉnh ngưỡng realtime |
| ⚙️ Ngưỡng chỉnh runtime | Detect/similarity threshold lưu NVS, chỉnh qua web |
| 🔋 Tiết kiệm năng lượng | FaceID chỉ chạy sau khi VoiceID khớp; mic nghỉ khi không ở STANDBY |

---

## 🔄 State Machine (Luồng hoạt động)

```
┌─────────────┐
│   STANDBY   │ ← VoiceID lắng nghe, FaceID TẮT, LED tắt
│ (Chờ đợi)   │
└──────┬──────┘
       │ Giọng nói khớp (score ≥ 0.7)
       ▼
┌─────────────────┐
│ VOICE_TRIGGERED │ ← Kích hoạt FaceID, LED XANH cố định
│                 │
└──────┬──────────┘
       │ Khuôn mặt khớp trong 10s?
       ▼
┌──────────┐  Yes  ┌────────────┐
│ FACE_AUTH│ ────→ │ DOOR_OPEN  │ ← Servo mở 90°, LED xanh nháy 3 lần
└──────────┘       └──────┬─────┘
       │ No (timeout)      │ Timer 5s
       ▼                   ▼
  ┌─────────┐        ┌────────────┐
  │ STANDBY │ ←───── │ Close door │
  └─────────┘        └────────────┘
```

| Trạng thái | LED | FaceID | Mic | Thời gian |
|-----------|-----|--------|-----|-----------|
| `STANDBY` | Tắt | Tắt | Lắng nghe | — |
| `VOICE_TRIGGERED` | 🟢 Xanh cố định | Bật | Nghỉ | — |
| `FACE_AUTH` | 🟢 Xanh cố định | Bật | Nghỉ | 10s timeout |
| `DOOR_OPEN` | 🟢 Nháy 3 lần | Tắt | Nghỉ | 5s rồi đóng cửa |

---

## 🔌 Sơ đồ chân GPIO (Pinout)

> Board: **Freenove ESP32-S3 WROOM Camera Module** (tương thích ESP32-S3-EYE)

### 📷 Camera OV2640

| Chức năng | GPIO |
|-----------|------|
| XCLK | 15 |
| SIOD (I2C SDA) | 4 |
| SIOC (I2C SCL) | 5 |
| D2 | 11 |
| D3 | 9 |
| D4 | 8 |
| D5 | 10 |
| D6 | 12 |
| D7 | 18 |
| D8 | 17 |
| D9 | 16 |
| VSYNC | 6 |
| HREF | 7 |
| PCLK | 13 |

### 🎙️ Micro INMP441 (I2S)

| Chức năng | GPIO |
|-----------|------|
| BCLK (SCK) | 40 |
| WS (L/R Select) | 41 |
| DATA (SD) | 42 |

### 🚪 Servo & 💡 LED

| Thiết bị | GPIO | Ghi chú |
|----------|------|---------|
| Servo motor | **47** | PWM 50Hz, 13-bit (LEDC Timer 1 / Channel 1) |
| LED RGB WS2812 | **48** | RMT driver (lưu ý: GPIO48 có thể xung đột JTAG) |

> ⚠️ **Lưu ý:** LEDC **Timer 0 / Channel 0** được camera XCLK sử dụng — servo dùng Timer 1 / Channel 1 để tránh xung đột.
> Debug bằng JTAG có thể làm LED không hoạt động (đã xử lý bằng warning trong log, LED bị disable).

---

## 🗂️ Cấu trúc thư mục

```
edge-ai/
├── main/
│   ├── main.cpp              # App chính: state machine, camera, WiFi, HTTP server
│   ├── camera_pins.h         # Định nghĩa chân GPIO
│   ├── face_recognition.cpp  # Nhận diện khuôn mặt (ESP-DL) + lưu database SPIFFS
│   ├── voice_auth.cpp        # Nhận diện giọng nói (TFLite Micro) + MFCC
│   ├── audio_capture.cpp     # Ghi âm I2S (INMP441, 16kHz, gain x4)
│   ├── http_handlers.cpp     # HTTP API cho voice (enroll/verify/speakers/settings)
│   ├── led_control.cpp       # Điều khiển LED WS2812
│   ├── servo_control.cpp     # Điều khiển servo PWM
│   ├── model_data.cc         # Mô hình voice TFLite (INT8, nhúng dạng C array)
│   ├── collect_data.py       # Tool thu âm dataset (sounddevice)
│   ├── select_esc50.py       # Tool import thêm noise từ ESC-50
│   └── train_quantize_export.py  # Train CNN + INT8 quantize + export C array
├── dataset/                  # Dữ liệu âm thanh: target/ (giọng chủ nhà), noise/ (tiếng ồn)
├── tools/
│   ├── analyze_tflite_model.py   # Phân tích model TFLite
│   └── dump_tflite_ops.py        # Liệt kê operators trong model
├── web_assets/               # Giao diện web (index, recognition, voice)
├── docs/
│   ├── lecture_voice_recognition.md   # Bài giảng chi tiết về pipeline voice
│   └── generate_report.py
├── partitions.csv            # Bảng phân vùng flash
├── sdkconfig.defaults        # Cấu hình build mặc định
└── voice_auth.tflite         # Mô hình voice đã train sẵn
```

---

## 🛠️ Yêu cầu hệ thống

- **ESP-IDF v5.x** (tested với bản 5.2+)
- **ESP32-S3** với **PSRAM 8MB** (Octal) — bắt buộc cho camera + AI
- Python 3.8+ (chỉ cần cho tool train model)

### Dependencies (quản lý tự động qua `idf_component.yml`)

| Component | Phiên bản | Mục đích |
|-----------|-----------|----------|
| `espressif/esp32-camera` | ^2.0.0 | Camera driver |
| `espressif/esp-dl` | ^3.0.0 | Nhận diện khuôn mặt |
| `espressif/human_face_detect` | ^0.3.0 | Face detection |
| `espressif/human_face_recognition` | ^0.3.0 | Face recognition |
| `espressif/led_strip` | ^3.0.0 | LED WS2812 |
| `espressif/esp-sr` | ^2.0.0 | Tính toán MFCC |
| `espressif/esp-tflite-micro` | ^1.0.0 | Voice model inference |

---

## 🔧 Cài đặt & Build

### 1. Cấu hình WiFi

Sửa **SSID/password** trong `main/main.cpp` (bắt buộc trước khi flash):

```cpp
// WiFi credentials - CHANGE THESE
#define WIFI_SSID "your_wifi_ssid"
#define WIFI_PASS "your_wifi_password"
```

### 2. Build

```bash
# Cài đặt ESP-IDF và set target
. $HOME/esp/esp-idf/export.sh        # hoặc theo cách cài ESP-IDF của bạn
idf.py set-target esp32s3

# Build
idf.py build
```

> ✅ `sdkconfig.defaults.esp32s3` đã cấu hình sẵn: PSRAM Octal 80MHz, flash 8MB, CPU 240MHz, camera DMA buffer 32KB.

### 3. Flash & Monitor

```bash
# Flash firmware (Windows: COM port, Linux/macOS: /dev/ttyUSB0)
idf.py -p COM3 flash

# Xem log (bấm Ctrl+] để thoát)
idf.py -p COM3 monitor
```

Sau khi khởi động, tìm IP trong log (`Got IP: 192.168.x.x`) rồi mở trình duyệt:

```
http://<ESP32-IP>/
```

---

## 🌐 Giao diện Web

| URL | Chức năng |
|-----|-----------|
| `http://<ip>/` | Trang chính — chụp ảnh & đăng ký khuôn mặt, quản lý database |
| `http://<ip>/stream` | Luồng camera MJPEG trực tiếp |
| `http://<ip>/recognition` | Camera live + overlay tên người được nhận diện |
| `http://<ip>/voice` | Đăng ký / kiểm tra giọng nói, danh sách speakers, chỉnh ngưỡng |
| `http://<ip>/status` | Trạng thái hệ thống (WiFi, camera, voice...) |

### Đăng ký khuôn mặt (Enroll Face)
1. Mở `http://<ip>/`, bấm **Capture Photo**
2. Nhập tên → bấm **Enroll Face** (đăng ký thêm 1-2 góc nhìn để tăng độ chính xác)
3. Kiểm tra danh sách trong **Enrolled Faces**

### Đăng ký giọng nói (Enroll Voice)
1. Mở `http://<ip>/voice`
2. Nhập tên → bấm **Start Enrollment** (nói **5 lần** liên tiếp theo hướng dẫn)
3. Xem danh sách **Enrolled Speakers**

---

## 📡 REST API

### Camera / Face
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/capture` | Chụp ảnh JPEG |
| GET/POST | `/enroll?name=X` | Đăng ký khuôn mặt |
| GET | `/faces` | Danh sách khuôn mặt đã đăng ký |
| GET | `/delete_all` | Xóa tất cả khuôn mặt |
| GET | `/reset_database` | Reset database khuôn mặt |
| GET | `/recognized_name` | Tên người đang nhận diện |
| GET | `/ping` | Kiểm tra kết nối |

### Voice
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/voice/enroll?name=X` | Đăng ký giọng nói (thu 5 mẫu) |
| POST | `/voice/verify?name=X` | Kiểm tra giọng nói (name tùy chọn) |
| GET | `/voice/speakers` | Danh sách speakers |
| DELETE | `/voice/speakers?name=X` | Xóa speaker |
| GET/POST | `/voice/settings` | Đọc/chỉnh ngưỡng & VAD sensitivity |

---

## 🎛️ Ngưỡng (Thresholds) có thể chỉnh

| Ngưỡng | Mặc định | Chỉnh qua | Mô tả |
|--------|---------|-----------|-------|
| Voice auth | 0.70 | Web `/voice` | Độ khớp giọng nói tối thiểu |
| VAD sensitivity | 0.75 | Web `/voice` | Độ nhạy phát hiện tiếng nói |
| Face detect | 0.30 | NVS (`face_recognition_set_detect_threshold`) | Lọc kết quả detector |
| Face similarity | 0.50 | NVS (`face_recognition_set_similarity_threshold`) | Độ khớp khuôn mặt tối thiểu |

> 💡 **Bảo mật cao hơn:** tăng thresholds (ví dụ voice 0.85, face 0.6) → giảm false positive nhưng có thể từ chối chủ nhà nhiều hơn.
> 💡 **Tiện lợi hơn:** giảm thresholds → dễ mở cửa hơn nhưng kém an toàn hơn.

---

## 🧠 Huấn luyện lại mô hình Voice (tuỳ chọn)

Nếu muốn model nhận diện **giọng của bạn** chính xác hơn:

```bash
# 1. Thu âm giọng bạn (class = target)
cd main
python collect_data.py
#   → đổi CLASS_NAME = "noise" trong script, thu tiếng ồn/người khác
python collect_data.py

# 2. (Tùy chọn) Import thêm noise từ ESC-50 dataset
python select_esc50.py path/to/esc50 ../esc50_selected --copy

# 3. Train + INT8 quantize + export C array
python train_quantize_export.py
#   → tạo file voice_auth.tflite, model_data.cc, model_data.h

# 4. Build lại firmware
cd ..
idf.py build
idf.py -p COM3 flash
```

> 📖 Xem chi tiết pipeline (MFCC, kiến trúc CNN, quantization, troubleshooting) trong [`docs/lecture_voice_recognition.md`](docs/lecture_voice_recognition.md).

### Tool phân tích model

```bash
python tools/analyze_tflite_model.py voice_auth.tflite
python tools/dump_tflite_ops.py voice_auth.tflite
```

---

## 🧩 Phân vùng Flash

| Partition | Loại | Kích thước | Mục đích |
|-----------|------|-----------|----------|
| `nvs` | data | 24K | Lưu cấu hình & thresholds |
| `phy_init` | data | 4K | Calibration WiFi |
| `factory` | app | 4MB | Firmware |
| `fr` | spiffs | 3MB | Database khuôn mặt |
| `web` | spiffs | 512K | Web assets |

---

## 🛠️ Troubleshooting nhanh

| Vấn đề | Giải pháp |
|--------|-----------|
| LED không sáng | GPIO48 xung đột JTAG — xem log cảnh báo; dùng dây nạp không dùng JTAG |
| Camera init fail | Kiểm tra PSRAM (cần `CONFIG_SPIRAM=y`), flash 8MB |
| Voice không nhận diện | Mic INMP441: kiểm tra chân WS/BCLK; nói cách mic ~10-20cm |
| False positive nhiều | Tăng voice threshold / face similarity threshold |
| Face không nhận diện được | Đăng ký nhiều góc mặt, ánh sáng đủ, chờ 10s timeout |
| ESP crash khi inference | Tăng `kTensorArenaSize` trong `voice_auth.cpp` (40KB → 48KB) |

---

## 📚 Tài liệu liên quan

- [`docs/lecture_voice_recognition.md`](docs/lecture_voice_recognition.md) — Bài giảng đầy đủ về toàn bộ pipeline voice recognition + face recognition

---

## 📄 License

Private project — vui lòng liên hệ chủ repo để biết chi tiết.
