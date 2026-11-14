# BUỔI 3 — TỰ CODE LED WS2812 & SERVO (PWM)

> ⏱️ Thời lượng: ~3 giờ · 📊 Độ khó: ⭐⭐ · 🎯 Mục tiêu: tự viết `led_control.cpp` (LED WS2812 qua RMT) và `servo_control.cpp` (servo qua LEDC PWM) — những "cơ bắp" đầu tiên của khóa cửa.

---

## 3.0. Bản đồ buổi học

```
[3.1 Đấu nối] → [3.2 Tự viết led_control.cpp] → [3.3 Tự viết servo_control.cpp]
 → [3.4 Test] → [3.5 Đối chiếu code mẫu]
```

## 3.1. Đấu nối phần cứng (theo bảng pin của dự án)

Mở [`main/camera_pins.h`](../../main/camera_pins.h) — nguồn sự thật về chân:

| Linh kiện | Chân | Ghi chú |
|---|---|---|
| Camera OV2640 | XCLK 15, SIOD 4, SIOC 5, D0–D7 11/9/8/10/12/18/17/16, VSYNC 6, HREF 7, PCLK 13 | cắm sẵn trên board Freenove |
| LED WS2812 | GPIO 48 | thường là LED onboard của board |
| Servo SG90 | GPIO 47 | tín hiệu PWM, nguồn 5 V |
| Micro INMP441 | BCLK 40, WS 41, DATA 42 | sẽ dùng ở buổi 4 |

Kết servo: **dây tín hiệu (cam) → GPIO 47; dây 5V (đỏ) → 5V; dây GND (nâu) → GND**. Servo lớn cần nguồn ngoài — nếu servo giật làm chip reset (log báo *brownout*), đó là dấu hiệu thiếu dòng điện, không phải bug code.

## 3.2. Khái niệm nền tảng — RMT và WS2812

WS2812 là LED **"thông minh"**: bạn gửi cho nó **một chuỗi bit thời gian chính xác** — "HIGH ~0.8 µs rồi LOW ~0.45 µs" = bit 1; "HIGH ~0.25 µs rồi LOW ~0.75 µs" = bit 0. GPIO thường không giữ nhịp chính xác tới nano-giây — vì vậy dùng ngoại vi **RMT** của ESP32: cột hàng phát bit-time chính xác như một người đánh nhịp.

**`led_control.cpp` của riêng bạn:**

```cpp
#include "led_control.h"
#include "led_strip.h"

static led_strip_handle_t led_strip = NULL;

esp_err_t led_init(void)
{
    led_strip_config_t strip_config = {
        .strip_gpio_num = LED_WS2812_PIN,   // GPIO 48
        .max_leds = 1,
        .led_model = LED_MODEL_WS2812,
    };
    led_strip_rmt_config_t rmt_config = {
        .resolution_hz = 10 * 1000 * 1000,  // 10 MHz → độ phân giải 0.1 µs
    };
    return led_strip_new_rmt_device(&strip_config, &rmt_config, &led_strip);
}

void led_set_color(uint8_t r, uint8_t g, uint8_t b)
{
    led_strip_set_pixel(led_strip, 0, r, g, b);   // LED số 0 (chỉ có 1)
    led_strip_refresh(led_strip);                 // phát tín hiệu ra dây
}

void led_blink(uint8_t r, uint8_t g, uint8_t b, int times, int delay_ms)
{
    for (int i = 0; i < times; i++) {
        led_set_color(r, g, b);
        vTaskDelay(pdMS_TO_TICKS(delay_ms));
        led_set_color(0, 0, 0);
        if (i < times - 1) vTaskDelay(pdMS_TO_TICKS(delay_ms));
    }
}

void led_blink_red_fail(void)     { led_blink(255, 0, 0, 3, 200); }   // VoiceID fail
void led_blink_green_success(void){ led_blink(0, 255, 0, 3, 150); }   // FaceID OK
```

Ngoài ra phải **đăng ký component `led_strip`** vào project trước khi build: trong terminal chạy `idf.py add-dependency "espressif/led_strip^3.0.1"` (file gốc của dự án — [`main/idf_component.yml`](../../main/idf_component.yml)).

**Logic nghiệp vụ — nói đúng "tiếng khóa cửa" (buổi 5 sẽ gọi các hàm này):**

| Sự kiện | Hàm LED gọi | Màu |
|---|---|---|
| VoiceID fail | `led_blink_red_fail()` | đỏ nháy 3 lần |
| VoiceID OK (chờ mặt) | `led_set_color(0, 255, 0)` | xanh cố định |
| FaceID OK, mở cửa | `led_blink_green_success()` | xanh nháy 3 lần |
| Về STANDBY | `led_off()` | tắt |

## 3.3. Khái niệm nền tảng 2 — PWM và Servo

**PWM** (Pulse Width Modulation) = xung chữ nhật với "độ rộng mức HIGH" là tham số điều khiển. Servo RC đọc **xung 50 Hz theo độ rộng:**

- 500 µs → 0° (cửa đóng — mã `SERVO_ANGLE_CLOSED = 0`)
- 1500 µs → trung điểm
- 2500 µs → 180° (mã dự án dùng `SERVO_ANGLE_OPEN = 90°`)

Ngoại vi **LEDC** của ESP32-S3 tạo PWM theo "duty" (tỉ số HIGH). Công thức quy đổi — nằm trong code mẫu [`main/servo_control.cpp`](../../main/servo_control.cpp), hàm `angle_to_duty()`:

```cpp
static uint32_t angle_to_duty(int angle)
{
    if (angle < 0)   angle = 0;
    if (angle > 180) angle = 180;

    uint32_t pulse_us = SERVO_PULSE_MIN_US +
        (uint32_t)((float)(SERVO_PULSE_MAX_US - SERVO_PULSE_MIN_US) * angle / 180.0f);

    // PWM period = 1/50Hz = 20,000 µs ; 13-bit resolution = 8192 steps
    uint32_t duty = (uint32_t)((float)pulse_us / 20000.0f * 8191.0f);
    return duty;
}
```

**Đọc công thức:** pulse_us là "thời gian mức HIGH trong 20 ms"; LEDC duty là "phân số thời gian HIGH" quy theo resolution 13-bit (2^13 − 1 = 8191 cấp). 500–2500 µs chia cho 20000 µs = 2.5–12.5% duty.

**Điểm không tưởng — Timer 1 chứ không 0:** camera chiếm LEDC Timer 0 + Channel 0 (XCLK 20 MHz), nên servo phải dùng Timer/Channel 1 — khai trong `servo_control.h`:

```cpp
#define SERVO_PWM_FREQ_HZ    50               // servo đọc xung 50 Hz
#define SERVO_PWM_RESOLUTION LEDC_TIMER_13_BIT // 13 bit = 8192 cấp
#define SERVO_LEDC_TIMER     LEDC_TIMER_1     // tránh Timer 0 của camera
#define SERVO_LEDC_CHANNEL   LEDC_CHANNEL_1
```

## 3.4. Tự viết `servo_control.cpp`

Viết 2 hàm theo khung sau (đối chiếu mẫu [`main/servo_control.cpp`](../../main/servo_control.cpp) sau khi viết xong):

```cpp
esp_err_t servo_init(void)
{
    // BẠN LÀM 1: ledc_timer_config_t { LEDC_LOW_SPEED_MODE, 13-bit, freq 50 Hz, LEDC_TIMER_1 }
    // BẠN LÀM 2: ledc_channel_config_t { gpio SERVO_PIN, channel LEDC_CHANNEL_1, duty 0 }
}

void servo_set_angle(int angle)
{
    // BẠN LÀM 3: duty = angle_to_duty(angle)
    // BẠN LÀM 4: ledc_set_duty(...) rồi ledc_update_duty(...)
}
```

Đoạn `servo_set_angle` trong mã mẫu:

```cpp
void servo_set_angle(int angle)
{
    uint32_t duty = angle_to_duty(angle);
    ledc_set_duty(LEDC_LOW_SPEED_MODE, SERVO_LEDC_CHANNEL, duty);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, SERVO_LEDC_CHANNEL);
}
```

> 🧠 **Câu hỏi tư duy:** có cần `ledc_update_duty` không? *(Có — LEDC dùng "shadow register": set_duty chỉ ghi vào bộ nhớ tạm, phải update_duty mới push lên chip thực.)*

## 3.5. Test — cửa "sống"

Thêm vào `app_main()`:

```cpp
led_init();
led_set_color(0, 255, 0);  vTaskDelay(pdMS_TO_TICKS(1000));
led_set_color(255, 0, 0);  vTaskDelay(pdMS_TO_TICKS(1000));
led_off();

servo_init();
servo_close_door();                        // đóng cửa lúc khởi động
vTaskDelay(pdMS_TO_TICKS(1000));
servo_open_door();   // 90°
vTaskDelay(pdMS_TO_TICKS(2000));
servo_close_door();  // 0°
```

**Kết quả mong đợi:** LED xanh → đỏ → tắt; servo quay 90°, dừng 2 giây, quay về 0°.

## 3.6. Bài tập về nhà

1. Thay `servo_set_angle(45)` vào test — kiểm tra servo di chuyển mượt; nếu giật, điều chỉnh `SERVO_PULSE_MIN_US/MAX_US` theo datasheet servo thật.
2. Viết hàm `servo_demo()` tự chạy: 0° → 45° → 90° → 0°, mỗi bước 1 giây.
3. So bài của bạn với [`main/led_control.cpp`](../../main/led_control.cpp) và [`main/servo_control.cpp`](../../main/servo_control.cpp) — thiếu chỗ nào, đúng chỗ nào?

## ✅ Checklist kết thúc buổi 3

- [ ] Đấu đúng: servo → GPIO 47 + 5V + GND; LED WS2812 onboard GPIO 48
- [ ] Giải thích được: RMT làm gì cho WS2812; LEDC tạo PWM cho servo
- [ ] Tự viết được `led_control.cpp` và `servo_control.cpp` chạy được
- [ ] Servo đảo 0° → 90° → 0° mượt; LED xanh–đỏ–tắt đúng luồng
- [ ] Biết Timer/Channel 0 bị camera chiếm — servo luôn dùng Timer 1

➡️ **Buổi tiếp theo**: [Buổi 4 — Tự code thu âm I2S](buoi04_i2s_thu_am.md)
