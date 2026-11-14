# Buổi 11 — Ghép tất cả: tour mã nguồn dự án & tổng kết khóa học

## 11.0. Mục tiêu buổi học

Bạn đã tự viết từng khối (11 file `mycourse/`). Buổi cuối:
1. **Tour mã nguồn thật** của dự án — đọc flow đầy đủ trong `main/main.cpp` từ `app_main()`: mỗi khối bạn học đặt vào vị trí nào
2. **Bản đồ tự kiểm tổng thể** — mức "tự code lại được toàn bộ": gặp 1 chủ đề bất kỳ, bạn giải thích được trong 2 phút
3. **Sản phẩm cuối** — chạy firmware hoàn chỉnh: nói giọng → chờ xác nhận mặt → mở cửa; toàn bộ qua web

## 11.1. Tour `app_main()` — khớp từng khối đã học

Mở `main/main.cpp`, tìm `app_main()` (dòng ~1440). Trình tự gọi — mỗi lời gọi ứng với một buổi đã học:

```cpp
extern "C" void app_main(void)
{
    // ── NỀN TẢNG ──────────────────────────────────
    nvs_flash_init();              // lưu profile giọng + ngưỡng (buổi 7 NVS)
    ESP_ERROR_CHECK(esp_netif_init());          // Wi-Fi nền cho web (buổi 10)
    ...
    // ── NGOẠI VI ─────────────────────────────────
    led_init();                    // LED WS2812 (buổi 3)
    servo_init();                  // Servo LEDC PWM (buổi 3)
    audio_capture_init();          // Mic I2S thu âm (buổi 4)
    camera_init();                 // Camera OV2640 (buổi 9)
    ...
    // ── HỆ ĐIỀU HÀNH ─────────────────────────────
    door_state_init();             // event group + mutex (buổi 5)
    // ── AI GIỌNG NÓI ─────────────────────────────
    voice_auth_init();             // TFLM + model + profile NVS (buổi 6–7)
    // ── AI KHUÔN MẶT ─────────────────────────────
    face_recognition_init();       // Detector + Recognizer ESP-DL (buổi 9)
    // ── WEB ──────────────────────────────────────
    wifi_connect();                // kết nối Wi-Fi (buổi 10)
    web_server_start();            // HTTP server + handler (buổi 10)
    // ── CÁC TASK ─────────────────────────────────
    xTaskCreate(voice_auth_task, ...);   // thu âm → MFCC → AI → set event (5–8)
    xTaskCreate(face_task, ...);         // chụp → detect → recognize → set event (9)
    xTaskCreate(state_machine_task, ...);// máy trạng thái 4 trạng thái (buổi 5)
}
```

> Tip khi đọc code lớn: bấm `Ctrl+F` tìm mỗi dòng có `init()` hay `xTaskCreate()` — đó là các "khối khởi động", dừng lại ở từng khối để hỏi "khối này làm gì?"

## 11.2. Flow tổng thể sản phẩm — hoạt động đầy đủ

```
Task giọng (voice)
   ┌────────────────────────────────────────────┐
   │ thu 3 giây audio → MFCC → AI → score≥0.70  │
   └──────────────────────┬─────────────────────┘
                          ▼  VOICE_OK_EVENT (event group)

Task mặt (face)
   ┌────────────────────────────────────────────┐
   │ chụp khung → detect → recognize embedding  │
   └──────────────────────┬─────────────────────┘
                          ▼  FACE_OK_EVENT (event group)

Máy trạng thái (buổi 5)
   VOICE_OK && FACE_OK trong ~3 giây?
      │
      ▼  đúng cả hai → mở
   servo_open_door() + LED xanh
      │ chờ 5 giây
      ▼
   servo_close_door() + LED tắt

   chỉ 1 trong 2 đúng  → nháy đỏ 3 lần (kèm "cửa khóa")
```

Sự kiện quan trọng nhất: **cả hai task cùng "vote" đúng** trong cửa sổ thời gian ~3 giây (`state_cache_ms`, buổi 5). Chỉ 1 trong 2 đúng → cửa KHÔNG mở, nháy đỏ 3 lần. Đây chính là **xác thực 2 yếu tố (2FA)** — giọng là thứ bạn "có" (biết nói, gắn với con người), mặt là thứ bạn "là" — kết hợp nhau vừa để chặn giả mạo (record giọng / in ảnh mặt giấy).


## 11.3. Bản đồ tự kiểm tổng thể — "tự code lại được toàn bộ"

Với mỗi mục, tự giảng giải trong 2 phút không xem tài liệu. Ký hiệu ×3: ✅ làm được nhắm mắt; 🔶 cần xem lại; ❌ phải học lại buổi đó.

| Nhóm | Chủ đề kiểm tra | Buổi |
|---|---|---|
| Nền tảng | Tạo project ESP-IDF; giải thích `CMakeLists.txt` + `idf_component.yml`; flash + monitor | 2 |
| Ngoại vi | RMT cho WS2812; LEDC PWM tính duty từ góc servo; I2S RX mode: BCLK/WS/DATA | 3–4 |
| Hệ điều hành | Tạo task + ưu tiên; event group bits; binary sema; máy trạng thái 4 trạng thái | 5 |
| DSP | Vì sao Hann; công thức FFT; dải năng lượng (bin → 13); log + ε; chuẩn hóa /max | 6 |
| AI giọng | Khối tensor arena; INT8 lượng hóa qua lại; op resolver; Invoke; điểm gộp 0.35/0.65 | 7 |
| Dữ liệu + train | 80 file 2 lớp; quy tắc vàng 4 con số; CNN nhỏ; lượng hóa representative; export C | 8 |
| AI mặt | jpeg→RGB; detector/recognizer; embedding + cosine; FB return; SPIFFS persistence | 9 |
| Web | httpd; MJPEG multipart; URL → handler; HTML nhúng; PIN admin | 10 |
| Kiến trúc | app_main thứ tự; 2FA event group; Wi-Fi trước server | 11 |

## 11.4. Mở rộng khi bạn muốn đi xa hơn (tùy chọn)

**Mức 2 — mở rộng sát với dự án:**
- **Nhiều profile giọng** (nhiều thành viên nhà): mở rộng `voice_profile_t` thành mảng — kết hợp sửa UI web
- **MQTT / thông báo**: khi có người lạ thử truy cập, gửi tin nhắn cho chủ nhà qua broker (dịch vụ pub/sub)
- **Huấn luyện lại khuôn mặt bằng model tùy biến** với **Edge Impulse**, đối chiếu chất lượng với model có sẵn của ESP-DL
- **HTTPS / token** — đổi web server sang TLS: `esp_https_server`; nâng PIN → token-based login

**Mức 3 — đi xa hơn (nghiên cứu, sáng tạo):**
- **Đo FAR/FRR như bài báo khoa học**: thu tập test, đo "AI nhận sai bao nhiêu" — mặt số đo chuẩn cho đồ án/báo cáo của bạn
- **Thử với dataset công khai** (LibriSpeech / TIMIT) để benchmark model với dữ liệu chuẩn
- **Low-power**: sleep giữa các lượt chờ — chỉ thức khi phát hiện tiếng động

## 11.5. Checklist cuối khóa — chốt

- [ ] Firmware của chính bạn chạy được flow 2FA: nói giọng + mặt → cửa mở
- [ ] Enroll giọng + enroll mặt từ trang web, đổi ngưỡng, xóa tất cả
- [ ] Giải thích được mỗi file `main/*.cpp` trong 2 phút
- [ ] Nhật ký lỗi của bạn có ≥ 15 mục — quý cho các dự án sau
- [ ] (Tùy chọn) Đo được FAR/FRR trên tập test của bạn

**Chúc mừng bạn hoàn thành khóa học.** Từ "không biết chip ESP32 là gì" đến "tự code được cả hệ nhận diện giọng + khuôn mặt trên nền Edge AI" — sản phẩm này bạn có thể trưng bày, viết báo cáo, hoặc mở rộng thành đồ án thực tế.

