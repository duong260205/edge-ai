# BUỔI 2 — CÀI ESP-IDF & TỰ TẠO PROJECT ĐẦU TIÊN

> ⏱️ Thời lượng: ~3 giờ · 📊 Độ khó: ⭐⭐ · 🎯 Mục tiêu: cài xong ESP-IDF, và **tự tay tạo một project trống** (không dùng example có sẵn) để flash chữ "Hello" + nháy LED lên chip — bước viết code đầu tiên của bạn.

---

## 2.0. Bản đồ buổi học

```
[2.1 Cài ESP-IDF] → [2.2 Tạo project TỪ TEMPLATE TRỐNG] → [2.3 Tự viết main.cpp]
 → [2.4 Build] → [2.5 Flash/monitor] → [2.6 Đối chiếu build.bat dự án]
```

## 2.1. Cài ESP-IDF (khung cứng chờ bạn)

ESP-IDF là **bộ công cụ chính thức của Espressif** — chứa: trình biên dịch `xtensa-esp32s3-elf-gcc`, thư viện phần cứng (driver, FreeRTOS), và công cụ `idf.py`.

**Cài theo hướng dẫn chính thức của Espressif (mới nhất tại thời điểm học):**

1. Tải **ESP-IDF 5.x** cho Windows tại [dl.espressif.com/dl/esp-idf](https://dl.espressif.com/dl/esp-idf/) (Installer Offline lớn ~1.5 GB) hoặc dùng **VS Code Extension "ESP-IDF"** (khuyến nghị — tích hợp terminal + build + flash trong VS Code).
2. Chọn bản **ESP32-S3** khi installer hỏi chip. Cần ~6 GB.
3. Sau khi xong, mở **"ESP-IDF 5.x Terminal"** từ menu Start. Terminal này có biến môi trường (PATH cho toolchain) — mọi lệnh `idf.py` đều **chỉ chạy được trong đó**. Đây là bẫy số 1 của người mới: mở cmd thường rồi thắc mắc "không nhận lệnh idf.py".

## 2.2. Tạo project TRỐNG của riêng bạn (không dùng example!)

ESP-IDF có sẵn hàng trăm example — nhưng mục tiêu của khóa học là bạn **tự dựng khung từ template trống**, vì khi tự dựng bạn hiểu từng file là gì.

```bash
mkdir C:/code/lock
cd C:/code/lock
```

Tạo 3 file bằng tay (bạn gõ, đừng copy cả khối):

**`CMakeLists.txt`** (cấp cao nhất — khai báo "đây là project ESP-IDF"):

```cmake
cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(lock)
```

**`main/CMakeLists.txt`** (khai báo component `main` gồm những 
```

```cmake
idf_component_register(SRCS "main.cpp"
                       INCLUDE_DIRS ".")
```

**`main/main.cpp`** — code đầu tiên bạn tự viết từ con số 0:

```cpp
#include <cstdio>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"

#define LED_PIN GPIO_NUM_2   // LED GPIO 48 là pin WS2812 trên board; GPIO 2 là LED thường (nếu có)

extern "C" void app_main(void)
{
    gpio_reset_pin(LED_PIN);
    gpio_set_direction(LED_PIN, GPIO_MODE_OUTPUT);

    while (true) {
        gpio_set_level(LED_PIN, 1);          // bật
        printf("Hello tu ESP32-S3!\n");       // in qua UART — bạn sẽ thấy trong monitor
        vTaskDelay(pdMS_TO_TICKS(1000));      // ngủ task 1000 ms (không while-empty!)
        gpio_set_level(LED_PIN, 0);          // tắt
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

**Giải thích từng dòng (3 khái niệm mới):**

| Dòng | Khái niệm mới | Giải thích đời thường |
|---|---|---|
| `gpio_set_direction` | GPIO là chân ra/vào | Mỗi chân có thể là "đầu vào" hay "đầu ra". GPIO_MODE_OUTPUT nghĩa là "chân này mình điều khiển, không nhận đọc". |
| `extern "C"` | C vs C++ linkage | ESP-IDF's App entry gọi hàm `app_main` theo phong cách C (không máng đổi tên kiểu C++). Không `extern "C"` → linker không tìm thấy → báo lỗi "undefined reference". |
| `vTaskDelay` | FreeRTOS sleep | while trống sẽ chiếm CPU liên tục; `vTaskDelay` đưa task vào trạng thái ngủ — nhường CPU cho các task khác. |

## 2.3. Build

Trong **ESP-IDF Terminal** (terminal có sẵn cầu có một "ESP-IDF" label nhé):

```bash
cd C:/code/lock
idf.py set-target esp32s3     # chỉ làm 1 LẦN đầu — nhận diện chip target
idf.py build                  # mỗi lần sửa code
```

**Đọc build output — là kỹ năng cần luyện:**

- `CC ... main.cpp` → đang compile file source
- Link thành công kết thúc bằng `Project build complete` + báo kích thước flash/RAM. File bin cuối cùng: **`build/lock.bin`** (tên lấy từ tên project).
- Lỗi người mới hay gặp nhất: "undefined reference to `app_main`" — do thiếu `extern "C"`.

## 2.4. Flash & Monitor lần đầu

1. **Cắm cáp USB (chân truyền dữ liệu!)** vào board. Đợi đèn cáp sáng.
2. `idf.py -p COM5 flash monitor` → COM5 tùy theo cổng Windows gán (xem Device Manager; trên Linux là `/dev/ttyUSB0`).
3. Kết quả mong đợi trong monitor:

```
I (xxx) main_task: Started on cpu0
Hello tu ESP32-S3!
Hello tu ESP32-S3!
```

LED (nếu GPIO 2 có) nháy 1 giây/lần. Nhấn `Ctrl+]` để thoát monitor.

> ⚠️ **Bẫy cáp USB**: nếu "A serial monitor init" hay không thấy cổng COM — 90% cáp chỉ có chân sạc nhưng không có data TX/RX.

## 2.5. Đối chiếu với dự án có sẵn — hiểu mình đang nằm ở đâu

Mở file [`build.bat`](../../build.bat) — file build nhanh của dự án:

```bat
call env.bat
idf.py build
idf.py flash monitor
```

So sánh: dự án đi cùng một con đường — `idf.py build + flash monitor + env.bat`, chỉ thêm file `env.bat` để **không phải mở ESP-IDF Terminal riêng** mà dùng CMD thường (env.bat tự set biến môi trường). Bạn có thể tạo giống. Lưu ý `partitions.csv` của dự án — bảng phân vùng flash, sẽ dùng ở buổi 9 (partition `fr` cho face.db).

## 2.6. Tinh chỉnh bạn cần sau khi build đầu tiên: bật PSRAM

Mở `sdkconfig.defaults` — chuẩn tự động load khi `set-target`:

```
CONFIG_IDF_TARGET="esp32s3"
CONFIG_SPIRAM=y
CONFIG_SPIRAM_MODE_OCT=y
CONFIG_SPIRAM_SPEED_80M=y
CONFIG_ESP32S3_DEFAULT_CPU_FREQ_240=y
CONFIG_ESP32S3_DATA_CACHE_64KB=y
```

Đây là các cấu hình đặc trưng dự án đang dùng: PSRAM Octal 80 MHz (sân chạy AI 8 MB) và tần số CPU 240 MHz. File gốc của dự án là [`sdkconfig.defaults`](../../sdkconfig.defaults) + [`sdkconfig.defaults.esp32s3`](../../sdkconfig.defaults.esp32s3) — đối chiếu nếu có gì lệch.

## 2.7. Bài tập về nhà

1. **Sửa và flash lại**: đổi chuỗi "Hello" thành tên bạn; đổi chu kỳ nhấn xuống máy 500 ms. Buộc phải rebuild.
2. **Tự giải thích được 3 khái niệm:** GPIO, task delay, extern "C" (viết 3 câu cho bố/mẹ hiểu).
3. Đối chiếu [`sdkconfig.defaults`](../../sdkconfig.defaults) của dự án với của bạn — người sao chê chỗ khác nhau thiết về `CONFIG_X` gì.

## ✅ Checklist kết thúc buổi 2

- [ ] ESP-IDF terminal chạy được `idf.py` (không "not recognized")
- [ ] Project trống tự tạo 3 file: `CMakeLists.txt`, `main/CMakeLists.txt`, `main/main.cpp`
- [ ] Chữ "Hello tu ESP32-S3!" hiện trong monitor, LED nháy
- [ ] Hiểu `vTaskDelay` so với while trống (không treo task)
- [ ] Đối chiếu được `build.bat` / `env.bat` / `sdkconfig.defaults` của dự án

➡️ **Buổi tiếp theo**: [Buổi 3 — Tự code LED WS2812 & Servo](buoi03_led_servo.md)
