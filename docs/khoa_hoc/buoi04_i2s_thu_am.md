# BUỔI 4 — TỰ CODE THU ÂM I2S (MICRO INMP441)

> ⏱️ Thời lượng: ~3 giờ · 📊 Độ khó: ⭐⭐⭐ · 🎯 Mục tiêu: tự viết `main/audio_capture.cpp` — cấu hình I2S, đọc âm thanh từ micro, và hiểu vì sao code dự án có `>> 14` và "gain ×4".

---

## 4.0. Bản đồ buổi học

```
[4.1 Đấu nối + khái niệm I2S] → [4.2 Tự viết audio_capture.cpp] → [4.3 INT32 → INT16]
 → [4.4 Test biên độ] → [4.5 Đối chiếu code mẫu]
```

## 4.1. Đấu nối + khái niệm I2S từ con số 0

**Đấu INMP441** (chân định nghĩa trong [`main/audio_capture.h`](../../main/audio_capture.h)):

| Pin INMP441 | Nối vào ESP32 | Tên đầy đủ |
|---|---|---|
| SCK | GPIO 40 | Bit Clock — nhịp đồng bộ, mỗi bit 1 nhịp |
| WS | GPIO 41 | Word Select — báo "mẫu này thuộc kênh nào" |
| SD | GPIO 42 | Serial Data — dữ liệu âm thanh |
| L/R | GND | chọn đọc **kênh trái** |
| VDD / GND | 3V3 / GND | nguồn |

**I2S là gì?** Micro số không gửi "giá trị dB" mà gửi **mỗi mẫu 1 số nguyên** qua bus. Mỗi nhịp BCLK = 1 bit; mỗi lần WS lật là 1 "slot" (32 bit = 1 mẫu). 3 dây = một luồng số rất đơn giản và ổn định.

**Cấu hình trong code mẫu ([`main/audio_capture.cpp`](../../main/audio_capture.cpp)):**

```cpp
i2s_std_config_t std_cfg = {
    .clk_cfg  = I2S_STD_CLK_DEFAULT_CONFIG(SAMPLE_RATE),   // 16000 Hz
    .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(
                    I2S_DATA_BIT_WIDTH_32BIT,              // mỗi slot 32 bit
                    I2S_SLOT_MODE_MONO),                   // đọc 1 kênh
    .gpio_cfg = { .mclk = I2S_GPIO_UNUSED,
                  .bclk = (gpio_num_t)I2S_BCLK_PIN,        // 40
                  .ws   = (gpio_num_t)I2S_WS_PIN,          // 41
                  .dout = I2S_GPIO_UNUSED,                 // chỉ nhận, không phát
                  .din  = (gpio_num_t)I2S_DATA_PIN },      // 42
};
```

| Trường | Nghĩa | Nói đời thường |
|---|---|---|
| `clk_cfg` | tốc độ lấy mẫu | "16000 lần/giây — 1 mẫu cách nhau 62,5 micro-giây" |
| `slot_cfg` | độ rộng + số kênh | slot 32 bit để chứa đủ 24-bit dữ liệu của INMP441 |
| `gpio_cfg` | nối chân | 3 dây dữ liệu: bclk, ws, din |

## 4.2. Tự viết `audio_capture.cpp`

Tạo 2 file của riêng bạn. **`audio_capture.h`:**

```cpp
#pragma once
#include <stdint.h>
#include <stddef.h>

#define SAMPLE_RATE         16000
#define RECORD_SECONDS      1
#define TOTAL_SAMPLES       (SAMPLE_RATE * RECORD_SECONDS)
#define VERIFY_SAMPLE_COUNT 3   // task thật sẽ thu 3 khung liên tiếp
#define VERIFY_TOTAL_SAMPLES (SAMPLE_RATE * VERIFY_SAMPLE_COUNT)

bool audio_capture_init();
bool audio_capture_record(int16_t* buffer, size_t num_samples);
```

`audio_capture.cpp` — khung trống, **BẠN điền từ từ theo gợi ý:**

```cpp
#include "audio_capture.h"
#include "driver/i2s_std.h"
#include "esp_log.h"

static const char* TAG = "AUDIO";
static i2s_chan_handle_t rx_handle = nullptr;

bool audio_capture_init()
{
    // BƯỚC 1: I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_AUTO, I2S_ROLE_MASTER)
    //         rồi i2s_new_channel(&cfg, NULL, &rx_handle)
    // BƯỚC 2: điền i2s_std_config_t như mục 4.1
    // BƯỚC 3: i2s_channel_init_std_mode(rx_handle, &std_cfg)
    //         lỗi → i2s_del_channel; ok → i2s_channel_enable(rx_handle)
}

bool audio_capture_record(int16_t* buffer, size_t num_samples)
{
    // BƯỚC 1: vòng lặp đọc CHUNK 256 mẫu mỗi lần bằng i2s_channel_read:
    //         i2s_channel_read(rx_handle, chunk_buf, to_read * sizeof(int32_t),
    //                          &bytes_read, pdMS_TO_TICKS(1000))
    // BƯỚC 2: int32_t sample = chunk_buf[i] >> 14;  (mục 4.3)
    // BƯỚC 3: chống clipping: kẹp về [-32768, 32767]
    // BƯỚC 4: ghi vào buffer[] và tiếp tục đến khi đủ num_samples
}
```

## 4.3. INT32 → INT16 — chỗ dễ sai nhất của Driver I2S

INMP441 trả **24 bit left-justified trong slot 32 bit** — tức dữ liệu nằm ở **8 bit cao**, 8 bit thấp là 0. Dự án dịch `>> 14`:

- Dịch phải 14 bit = chia 2^14 = 16384 — vừa đưa 24-bit về mốc int16, vừa **khuếch đại ×4** (dịch 16 bit mới là "đúng tuyến tính", dịch 14 bit cho tín hiệu to hơn 4 lần).
- Vì khuếch đại, tín hiệu to dễ tràn → phải **clip (kẹp giá trị)**:

```cpp
size_t valid_samples = bytes_read / sizeof(int32_t);
for (size_t i = 0; i < valid_samples; i++) {
    int32_t sample = chunk_buf[i] >> 14;

    if (sample > 32767)  sample = 32767;     // kẹp trần — tiếng nổ không quá ngưỡng
    else if (sample < -32768) sample = -32768;

    buffer[samples_read++] = (int16_t)sample;
}
```

> 🧠 **Câu hỏi tư duy:** nếu bỏ hai dòng clip thì lỗi phát sinh khi nào? *(Âm quá to làm int16 tràn → giá trị nhảy lung tung → MFCC đọc sai → score sai mà không báo lỗi gì.)*

## 4.4. Test — "nghe được" bằng con số RMS

Thêm vào `app_main()` sau phần LED/Servo của buổi 3:

```cpp
#include "audio_capture.h"
#include <cmath>

audio_capture_init();
int16_t* buf = new int16_t[SAMPLE_RATE];   // 1 giây = 16000 mẫu

while (true) {
    if (audio_capture_record(buf, SAMPLE_RATE)) {
        int32_t sum = 0, peak = 0;
        for (int i = 0; i < SAMPLE_RATE; i++) {
            sum += buf[i] * (long)buf[i];
            int mag = buf[i] < 0 ? -buf[i] : buf[i];
            if (mag > peak) peak = mag;
        }
        float rms = sqrtf((float)sum / SAMPLE_RATE);
        printf("RMS=%.1f  PEAK=%d\n", rms, peak);
    }
    vTaskDelay(pdMS_TO_TICKS(200));
}
```

**RMS là gì?** Root-Mean-Square — "biên độ trung bình bình phương", con số chỉ mức năng lượng tín hiệu, chính là **giá trị VAD dùng** ở buổi 5 và 7. Trên log bạn sẽ thấy:

| Tình huống | RMS | PEAK |
|---|---|---|
| Im lặng (noise floor phòng) | ~0–20 | ~10–50 |
| Nói vào micro | ~100–2000 | có thể >5000 |
| Chỉ có tiếng nền | ~20–50 | ~50–200 |

**Ngưỡng VAD của dự án** (trong `voice_auth_verify()` của [`main/voice_auth.cpp`](../../main/voice_auth.cpp)):

```cpp
// có tiếng nói mới tính đặc trưng, không thì bỏ luôn (tiết kiệm CPU)
if (rms < 30.0f || !compute_features(audio, num_samples, features)) {
    *score_out = -1.0f;
    return false;
}
// và trong compute_features(), gate thứ hai:
if (max_val < 100) return false;    // peak quá nhỏ → chắc tiếng nền
```

## 4.5. Đối chiếu code mẫu — 2 điểm phải so phải

Mở [`main/audio_capture.cpp`](../../main/audio_capture.cpp):

1. Dự án đọc theo **CHUNK 256 mẫu mỗi vòng** — không đọc một lần 48000 mẫu đồng thời (đọc khối lớn dễ lỗi timeout và tiêu RAM).
2. `i2s_channel_read` có **timeout 1000 ms** tự set — nếu thiếu data người gọi (`task caller`) phải xử lý trả về `false`.

## 4.6. Bài tập về nhà

1. In RMS các tình huống: im lặng, nói, vỗ tay — ghi 3 con số vào nhật ký.
2. Thay `>> 14` bằng `>> 15` (amplitude nhỏ hơn 2 lần) hay `>> 12` (to 4 lần, dễ clip) — ghi chú chênh lệch số RMS.
3. Tìm trong `main/voice_auth.cpp` 2 ngưỡng VAD (`rms < 30`, `max_val < 100`) — nhớ hai con số để sang buổi 5 hiểu task thật chặn âm đâu.

## ✅ Checklist kết thúc buổi 4

- [ ] Đấu đúng INMP441 (SCK 40, WS 41, SD 42, L/R → GND)
- [ ] Giải thích được: slot 32-bit, left-justified 24-bit, dịch 14 bit + gain ×4
- [ ] Log RMS/PEAK thay đổi rõ ràng khi bạn nói
- [ ] Biết 2 ngưỡng VAD: RMS ≥ 30 và max_val ≥ 100
- [ ] Vòng đọc CHUNK 256 bằng `i2s_channel_read` đầy đủ, không tự gọm đọc một khối to

➡️ **Buổi tiếp theo**: [Buổi 5 — FreeRTOS & Máy trạng thái](buoi05_freertos_may_trang_thai.md)
