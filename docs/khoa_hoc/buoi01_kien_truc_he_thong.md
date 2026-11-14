# BUỔI 1 — KIẾN TRÚC HỆ THỐNG & BẢN ĐỒ "TRỤC TỰ CODE"

> ⏱️ Thời lượng: ~2.5 giờ · 📊 Độ khó: ⭐⭐ · 🎯 Mục tiêu: vẽ lại được kiến trúc toàn hệ thống, và biết chính xác trong các buổi tới bạn sẽ tự viết ra những file & hàm nào.

---

## 1.0. Bản đồ buổi học

```
[1.1 Sơ đồ kiến trúc] → [1.2 Luồng một lần mở cửa] → [1.3 Bản đồ file sẽ tự viết]
```

> 📖 Buổi này **chưa viết code C nào** — nhưng mọi buổi sau đều quay về sơ đồ của buổi này. Đọc chậm, vẽ ra giấy theo từng mục.

## 1.1. Kiến trúc toàn hệ thống — mỗi khối tồn tại vì lý do gì?

Hệ thống gồm **2 lớp xác thực nối tiếp nhau**:

```mermaid
flowchart TD
    subgraph INPUT["Đầu vào"]
        MIC["Mic INMP441 (I2S)"]
        CAM["Camera OV2640"]
    end
    subgraph L1["LỚP 1 — GIỌNG NÓI"]
        A1["audio_capture.cpp<br/>thu âm 3 giây"]
        A2["voice_auth.cpp<br/>VAD → MFCC 32×13"]
        A3["TFLite Micro CNN INT8"]
        SA{"score ≥ 0.70?"}
    end
    subgraph L2["LỚP 2 — KHUÔN MẶT"]
        F1["face_recognition.cpp<br/>JPEG → RGB888"]
        F2["MSRMNP: phát hiện mặt"]
        F3["MobileFaceNet → cosine"]
        SB{"similarity ≥ 0.5?"}
    end
    MIC --> A1 --> A2 --> A3 --> SA
    CAM --> F1 --> F2 --> F3 --> SB
    SA -- -->|đạt| F1
    SA & SB -- "cả hai cùng đạt trong 10s" --> SERVO["Servo mở cửa 5s"]
```

**Vì sao cần 2 lớp?** Giọng nói nhanh và rẻ (mô hình chỉ ~12 KB) nhưng dễ bị bắt chước — người thân có giọng giống, hoặc bạn bị cảm thì score trượt. Gương mặt khó bị lừa hơn nhưng chậm hơn và tốn pin khi camera bật. Ghép cả hai: cửa chỉ mở khi **cùng một người** có cả giọng và mặt khớp trong cùng một cửa sổ 10 giây.

**Vì sao có VAD (Voice Activity Detection) trước AI?** Suy luận AI mỗi lần tốn CPU. Nếu đưa mọi âm (quạt, gió, gõ cửa) vào chạy AI liên tục thì chip 240 MHz sẽ bị đè. VAD tính 2 số liệu rất rẻ (RMS và peak) để chip chỉ tốn công chạy AI khi "chắc chắn có người nói" — lớp gác cổng rẻ hơn phép FFT hàng nghìn lần.

## 1.2. Đi theo MỘT lần mở cửa — 7 bước

```
1. [STANDBY]         Task voice_auth liên tục: thu 3 giây → VAD → MFCC → CNN → score
2. score ≥ 0.70      → set event VOICE_AUTH_OK → LED xanh sáng
3. [VOICE_TRIGGERED] → máy trạng thái đánh thức task khuôn mặt đang "ngủ"
4. [FACE_AUTH]       Task khuôn mặt: chụp khung → decode JPEG → detector → recognize
5. similarity ≥ 0.5  → set event FACE_AUTH_OK → LED nháy xanh 3 lần
6. [DOOR_OPEN]       Servo quay đến 90°, đợi 5 giây, quay về 0° (cửa đóng)
7. Nếu 10 giây không có mặt khớp → timeout, về STANDBY, LED tắt
```

Các bước này nằm trong mã thật tại 2 chỗ (đọc để làm quen tên, chưa cần hiểu sâu):

- [`main/main.cpp`](../../main/main.cpp) — `voice_auth_task`, `state_machine_task`, `face_recognition_task` và **máy trạng thái 4 trạng thái** (`STATE_STANDBY`, `STATE_VOICE_TRIGGERED`, `STATE_FACE_AUTH`, `STATE_DOOR_OPEN`).
- [`main/voice_auth.cpp`](../../main/voice_auth.cpp) — cả pipeline giọng nói (FFT + MFCC + TFLM) như một "hộp đen" tạm thời; buổi 6–7 sẽ mở hộp này từng dòng.

## 1.3. Bản đồ "trục tự code" — bạn sẽ tự viết 10 thứ

Đến buổi 11, bạn có sản phẩm hoàn chỉnh viết tay. Mỗi buổi cho bạn 1–2 mảnh:

| Thứ tự | Bạn tự viết | Buổi | Kiểm chứng "đã xong" |
|---|---|---|---|
| 1 | `led_control.cpp` của riêng bạn | Buổi 3 | LED đổi màu theo lệnh |
| 2 | `servo_control.cpp` của riêng bạn | Buổi 3 | Servo quay 0°↔90° |
| 3 | `audio_capture.cpp` của riêng bạn | Buổi 4 | Log in ra biên độ giọng mình |
| 4 | `door_state.cpp` của riêng bạn | Buổi 5 | Máy trạng thái 4 trạng thái + event |
| 5 | `voice_features.cpp` của riêng bạn | Buổi 6 | Dump mảng 32×13, khớp với Python |
| 6 | `voice_model.cpp` của riêng bạn | Buổi 7 | Score 0..1 in ra log |
| 7 | Thu dataset + chạy script train | Buổi 8 | Model nhận giọng chính bạn |
| 8 | `face_module.cpp` của riêng bạn | Buổi 9 | Enroll + nhận diện mặt thật |
| 9 | `lock_http.cpp` của riêng bạn | Buổi 10 | Trang web + stream + API |
| 10 | Ghép tất cả vào `app_main()` | Buổi 11 | Full app trên code tự viết |

Code mẫu để đối chiếu từng mảnh nằm trong `main/`:
`led_control.cpp` → `servo_control.cpp` → `audio_capture.cpp` → `main.cpp` (máy trạng thái) → `voice_auth.cpp` (MFCC + TFLM) → `_train_quantize_export.py` + `collect_data.py` → `face_recognition.cpp` → `http_handlers.cpp` + `main.cpp` (web).

> 💡 **4 cái bẫy dễ chết** (nêu trước để bạn hiểu vì sao các buổi sau cứ lặp lại cảnh báo):
> 1. Số liệu MFCC/khung không khớp giữa C++ trên chip và Python lúc train — model chạy nhưng score sai âm thầm (buổi 6, 8).
> 2. Quên chuẩn hoá biên độ (chia cho max) trong cả 2 pipeline — đầu vào lệch partition, score trượt (buổi 6, 8).
> 3. Đăng thiếu op trong `MicroMutableOpResolver<8>` — `Invoke()` báo lỗi "not supported" (buổi 7).
> 4. Cấp phát AI buffer không dùng `MALLOC_CAP_SPIRAM` — bloat 40 KB tensor arena trên RAM nội 512 KB → hệ trong máy treo (buổi 7).

## 1.4. Bài tập về nhà

1. **Vẽ lại sơ đồ kiến trúc mục 1.1** ra giấy (hoặc Excalidraw) từ trí nhớ, không nhìn.
2. **Vẽ máy trạng thái 4 trạng thái** với điều kiện chuyển tiếp. Đáp án tham khảo chính là sơ đồ trong `main.cpp` (mục "STATE MACHINE DEFINITIONS").
3. Ghi lại bảng mục 1.3 vào sổ — 10 mảnh sản phẩm bạn sẽ nắm đủ.

## ✅ Checklist kết thúc buổi 1

- [ ] Vẽ được 2 lớp xác thực: giọng → khuôn mặt → cửa mở
- [ ] Trình bày được tại sao có VAD trước AI (tiết kiệm CPU)
- [ ] Kể được 10 mảnh tự code + buổi tương ứng của từng mảnh (mục 1.3)
- [ ] Lật `main.cpp`, tìm ra được `system_state_t` gồm 4 trạng thái nào

➡️ **Buổi tiếp theo**: [Buổi 2 — Cài ESP-IDF & tự tạo project đầu tiên](buoi02_cai_dat_espidf.md)
