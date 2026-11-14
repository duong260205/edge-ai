# BUỔI 0 — KHỞI HÀNH: HIỂU BÀI TOÁN & CHUẨN BỊ MÁY

> ⏱️ Thời lượng: ~2 giờ · 📊 Độ khó: ⭐ · 🎯 Mục tiêu: nắm được hệ thống bạn SẼ TỰ CODE làm gì, chuẩn bị xong vật tư và công cụ, có mã nguồn trên máy.

---

## 0.1. Hệ thống bạn sẽ tự code là gì?

Hãy hình dung một ổ khóa "biết chủ": bạn đứng trước cửa, **nói một câu** — chip nhận ra giọng bạn. Ngay sau đó bạn **nhìn vào camera** — chip nhận ra mặt bạn. Cả hai cùng khớp trong 10 giây → servo quay, cửa mở. Người lạ thiếu một trong hai yếu tố → cửa vẫn đóng.

Điểm đặc biệt: **toàn bộ AI chạy ngay trên con chip ESP32-S3** — không gửi âm thanh/hình ảnh lên đám mây, không cần Internet. Chủ đề xuyên suốt khóa học gọi là **Edge AI** (AI trên rìa, tức trên thiết bị).

**Ba con số để "nếm thử" quy mô bài toán bạn sắp viết code cho:**

| Đại lượng | Giá trị | So sánh cho dễ hình dung |
|---|---|---|
| Mô hình giọng nói | ~12 KB INT8 (~13.600 tham số) | Nhỏ hơn 1 file ảnh chụp màn hình điện thoại |
| Mô hình khuôn mặt | MobileFaceNet của Espressif | Chạy realtime trên chip 240 MHz |
| RAM "sân chơi" AI | 8 MB PSRAM (bộ nhớ ngoài chip) | Gấp ~40 lần RAM nội của chip |

## 0.2. Bài toán chia nhỏ — bản đồ tâm lý 12 buổi

Một hệ thống lớn nghe có vẻ đáng sợ, nhưng khi chia thành mảnh, mỗi mảnh đều code được trong một buổi:

```
                  ┌─── BUỔI 2-4: TỪNG "CƠ BẮP" ───┐
                  │  LED + Servo + Thu âm I2S     │
                  └────────────┬───────────────────┘
                               ▼
TP4 (ngắn) ──────────── TỪNG "BỘ NÃO" ──────── TỰ CODE LẠI ĐƯỢC TOÀN BỘ ──► KẾT THÚC KHÓA
```

thay bằng: mỗi buổi viết 1–2 file, cuối khóa ghép lại thành `app_main()` hoàn chỉnh của riêng bạn:

```
BUỔI 0-1: Hiểu bài toán đã làm gì    BuOI 2-4: Viết từng "cơ bắp"   BuOI 5-7: Viết "bộ não"
  (không code)              │           LED, Servo, thu âm I2S           state machine + MFCC + TFLM
                            ▼
              BUỔI 8: Cho nó là CỦA BẠN       BUỔI 9-10: Viết 2 vùng còn lại
              thu giọng mình, train model        khuôn mặt + web/API
                            ▼
              BUỔI 11: Ghép + nghĩa bảo vệ + demo
```

> 💡 Khác biệt lớn nhất với khóa học cũ: trước đây "nạp firmware có sẵn rồi tìm hiểu". Bây giờ **mỗi buổi bạn mở VS Code và gõ code** — đáp án mẫu chỉ dùng để so sau khi tự viết xong vòng 1.

## 0.3. Kiểm tra máy tính của bạn (thực hành đầu tiên)

Chưa cần cài gì cả. Mở **Command Prompt** (Windows: `Win + R`, gõ `cmd`, Enter) và gõ lần lượt:

```bat
python --version
```
→ mong đợi `Python 3.x.x`. Nếu báo "not recognized": chưa lo, buổi 2 sẽ cài kèm ESP-IDF.

```bat
git --version
```
→ mong đợi `git version 2.x`. Chưa có thì tải tại [git-scm.com](https://git-scm.com/downloads).

```bat
wmic diskdrive get size,model
```
(Chỉ xem ổ còn trống ≥ 10 GB. Nếu `wmic` lỗi trên máy mới, dùng `Get-PSDrive` trong PowerShell cũng được.)

## 0.4. Lấy mã nguồn dự án

```bash
git clone <URL_REPO_DO_GIANG_VIEN_CAP> edge-ai
cd edge-ai
```

Mở thư mục bằng **VS Code** ([code.visualstudio.com](https://code.visualstudio.com)). Dành 20 phút đi dạo cấu trúc — chỉ cần lưu ý mỗi file thuộc "bài kiểm khóa của buổi nào":

```
edge-ai/
├── main/                      ← "đáp án mẫu" — file nào buổi nào đối chiếu
│   ├── main.cpp               ← buổi 5+9+10: state machine, task, HTTP server
│   ├── audio_capture.cpp/.h   ← buổi 4: THU ÂM I2S
│   ├── voice_auth.cpp/.h      ← buổi 6-7: MFCC + TFLM + ngưỡng 0.70
│   ├── face_recognition.cpp/.h ← buổi 9: camera + ESP-DL
│   ├── servo_control.cpp/.h   ← buổi 3: PWM servo
│   ├── led_control.cpp/.h     ← buổi 3: LED WS2812
│   ├── http_handlers.cpp/.h   ← buổi 10: web API
│   ├── training_config.json   ← buổi 8: các con số quy tắc vàng
│   └── collect_data.py + train_quantize_export.py ← buổi 8
├── dataset/                   ← dữ liệu âm giọng của bạn (buổi 8)
├── docs/khoa_hoc/             ← khóa học này
├── voice_auth.tflite          ← model đã train sẵn (bạn sẽ tự train lại ở buổi 8)
└── build.bat                  ← build nhanh trên Windows (buổi 2)
```

## 0.5. Checklist chuẩn bị vật tư

In bảng này ra hoặc chụp màn hình — mua/kiểm tra đủ trước buổi 3:

- [ ] Board **Freenove ESP32-S3 WROOM Camera Module** (kèm camera OV2640) — bắt buộc bản 8 MB flash + 8 MB PSRAM Octal
- [ ] Micro **INMP441** (I2S)
- [ ] Servo SG90 (hoặc tương đương)
- [ ] Dây jump nữ-nữ ≥ 15 sợi, đực-nữ ≥ 10 sợi
- [ ] Cáp USB có khả năng truyền dữ liệu (nhiều cáp chỉ sạc — sẽ không nạp được!)
- [ ] Máy tính ≥ 10 GB trống, Wi-Fi 2.4 GHz

> ⚠️ **Cảnh báo cáp USB**: đây là "bẫy" kinh điển. Nếu nạp firmware báo không tìm thấy cổng COM, thử cáp khác trước khi nghi ngờ board hỏng.

## 0.6. Bài tập về nhà

1. **Viết 5 câu** trả lời: "Chiếc khóa cửa này làm gì thêm mà dự án hiện chưa có?" (giữ lại, buổi 11 dùng để chọn hướng mở rộng).
2. Đọc lướt [`README.md`](../../README.md) của repo: chỉ mục "Tính năng chính" và "Sơ đồ chân GPIO".
3. Cài sẵn **VS Code** nếu chưa có.

## ✅ Checklist kết thúc buổi 0

- [ ] Kể được luồng 2 lớp xác thực trong 30 giây (giọng → gương mặt → cửa mở)
- [ ] Chạy được `python --version` và `git --version` thành công
- [ ] Đã clone repo, mở được thư mục `main/` trong VS Code
- [ ] Chỉ ra được: file nào sẽ đối chiếu ở buổi nào (bảng ở mục 0.4)
- [ ] Đủ vật tư theo mục 0.5 (hoặc đã đặt hàng)

➡️ **Buổi tiếp theo**: [Buổi 1 — Kiến trúc & bản đồ "trục tự code"](buoi01_kien_truc_he_thong.md)
