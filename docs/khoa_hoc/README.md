# 🔐 KHÓA HỌC: TỰ CODE KHÓA CỬA THÔNG MINH EDGE AI (GIỌNG NÓI + KHUÔN MẶT) TỪ CON SỐ 0

Chào mừng bạn đến với khóa học thực hành **12 buổi**. Khóa học này khác mọi khóa bạn từng học ở một điểm: **bạn không chạy firmware có sẵn để xem nó làm gì — bạn tự code toàn bộ hệ thống từ một project trống.** Cuối khóa, sản phẩm bạn tự tay viết bằng code của chính mình.

Mã nguồn của dự án (thư mục `main/`) chỉ có vai trò **đáp án mẫu để đối chiếu** sau mỗi bước — như lời giải của đề toán.

---

## 👥 Dành cho ai?

- Cần biết trước: **C/C++ cơ bản** (biến, hàm, vòng lặp, mảng) và **Python cơ bản**.
- Không cần biết: ESP-IDF, FreeRTOS, AI, DSP — mọi khái niệm đều giải thích từ con số 0, có ví dụ đời thường trước khi gặp code.

## 🎯 Mục tiêu: sau 12 buổi, TỰ CODE LẠI ĐƯỢC TOÀN BỘ

| Nhóm năng lực | Tự viết được gì |
|---|---|
| Nền tảng ESP-IDF | Project CMake từ template trống, build/flash/monitor |
| Ngoại vi | Driver LED WS2812 (RMT), Servo (LEDC PWM), Micro I2S thu âm |
| DSP | FFT + cửa sổ Hann + đặc trưng MFCC 32×13 bằng esp-dsp |
| AI giọng nói | Lượng hóa INT8, TFLite Micro: interpreter, tensor arena, op resolver, Invoke → score |
| AI khuôn mặt | Camera OV2640 + ESP-DL: detector → MobileFaceNet → cosine |
| Hệ điều hành | FreeRTOS: task, mutex, event group, binary semaphore, máy trạng thái 4 trạng thái |
| Web | HTTP server: MJPEG stream, multipart upload, REST API JSON, trang HTML nhúng |
| Pipeline dữ liệu | Hiểu từng dòng script thu âm + train + quantize + xuất model sang C |

> ⚠️ **Quy ước quan trọng xuyên suốt khóa học:** để mọi buổi khớp với đáp án mẫu trong `main/`, khi tự code các bước tính toán (MFCC, chuẩn hóa, lượng hóa) bạn phải dùng **đúng các con số** của dự án: `sample_rate 16000, frame 512, hop 512, 13 dải, 32 khung, ngưỡng 0.70`. Sai 1 con số là AI "đọc nhầm bảng ký hiệu" — buổi 8 sẽ giải thích tại sao.

## 🗓️ Lộ trình: mỗi buổi = 1 sản phẩm mang về

| Buổi | Tên | Bạn tự viết ra gì |
|---|---|---|
| [0](buoi00_khoi_hanh.md) | Khởi hành | Kiểm soát máy tính, có repo, đọc hiểu bài toán |
| [1](buoi01_kien_truc_he_thong.md) | Kiến trúc & "trục tự code" | Bản đồ các file bạn sẽ tự viết, vẽ lại kiến trúc |
| [2](buoi02_cai_dat_espidf.md) | Cài ESP-IDF & project đầu tiên | Chữ **"Hello từ ESP32-S3"** nháy LED trên chip của chính bạn |
| [3](buoi03_led_servo.md) | Tự code LED + Servo | `led_control.cpp` + `servo_control.cpp` — cửa biết mở/đóng |
| [4](buoi04_i2s_thu_am.md) | Tự code thu âm I2S | `audio_capture.cpp` — nghe được giọng qua mic |
| [5](buoi05_freertos_may_trang_thai.md) | FreeRTOS & máy trạng thái | State machine 4 trạng thái + event group + mutex |
| [6](buoi06_mfcc.md) | Tự code MFCC | `compute_features()` — âm thanh thành "ảnh 32×13" |
| [7](buoi07_tflm.md) | Tự code TFLite Micro | Quantize INT8 + Interpreter + `Invoke()` → score |
| [8](buoi08_thu_am_va_train.md) | Thu âm & huấn luyện (2 con đường) | Thu dataset giọng mình, chạy train → model → nạp lên chip |
| [9](buoi09_khuon_mat.md) | Tự code nhận diện khuôn mặt | Camera + ESP-DL: enroll/recognize workshop đầy đủ |
| [10](buoi10_web_api.md) | Tự code HTTP server & API | Stream camera, trang web nhúng, REST API quản trị |
| [11](buoi11_tour_ma_nguon_va_tong_ket.md) | Tour mã nguồn & tổng kết | Ghép mọi thứ thành sản phẩm hoàn chỉnh, demo + bảo vệ |

## 🧪 Cách học (đọc 1 lần, nhớ mãi)

1. **Đề bài trước, đáp án sau.** Mỗi mục của mỗi buổi có 3 lớp: *(1)* Mục tiêu — làm gì và vì sao; *(2)* **Các bước tự code** — bằng tay; *(3)* *"Đối chiếu đáp án mẫu"* — mở file thật của `main/` để so, có giải thích từng dòng mà bạn hay thắc mắc.
2. **Kiểm khóa trước khi đi tiếp.** Mỗi buổi kết thúc bằng *Checklist tự kiểm* — chưa đủ 100%, đừng sang buổi sau. Bản đồ buổi cuối (buổi 11) là nơi bạn chốt "tự code lại được tổng thể".
3. **Ghi vào nhật ký lỗi.** Mỗi lỗi hãy chép: (1) lỗi gốc, (2) lệnh chạy, (3) cách giải quyết. Tập này quý hơn mọi tài liệu khác khi bạn làm dự án xong.
4. **Hỏi đúng chỗ.** Khi hỏi, luôn kèm: bước nào + lệnh đã chạy + log lỗi đầy đủ.

## 📖 Tài liệu của dự án dùng khi cần

| Tài liệu | Khi nào cần |
|---|---|
| [`README.md`](../../README.md) | Bảng GPIO, bảng API, tổng quan |
| [`main/audio_capture.h`](../../main/audio_capture.h) | Các hằng số âm thanh (SAMPLE_RATE, I2S pins) |
| [`main/training_config.json`](../../main/training_config.json) | Cấu hình trích đặc trưng khi train (quy tắc vàng) |
| [`docs/BAO_CAO_DU_AN.md`](../BAO_CAO_DU_AN.md) | Báo cáo chi tiết toàn bộ hệ thống |
| [`tools/analyze_tflite_model.py`](../../tools/analyze_tflite_model.py) | Phân tích cấu trúc .tflite |

## Xa hơn (sau khóa, tùy chọn)

- **Edge Impulse** — nền tảng no-code/low-code: dùng *thay thế* con đường tự viết script train của buổi 8 khi cần nhanh (buổi 8 sẽ so sánh 2 con đường để bạn chọn).
- **Đo lường khoa học** — sau khi model chạy, ý tưởng mở rộng là đo Accuracy/FAR/FRR để dự án bạn "có số đo chuẩn" như bài báo khoa học.

---

*Bây giờ là buổi 0. Chúc bạn tự tay viết được chiếc khóa cửa AI đầu tiên của mình.*
