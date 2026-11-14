# Buổi 6 — Tự code bộ trích đặc trưng MFCC ("cái tai của con chip")

## 6.0. Mục tiêu buổi học

Buổi 4 bạn làm chip **nghe được** (thu được mảng số nguyên 16-bit). Buổi 6 bạn làm chip **hiểu được** giọng nói đó là của ai — bằng cách tự viết hàm `compute_features()` biến 1 giây âm thanh thành "ảnh số học" 32×13.

Sau buổi này, với hàm `compute_features()` của dự án:
- Bạn giải thích được **tại sao** chia 1 giây thành 32 khung và dùng cửa sổ Hann
- Tự thay hằng số `32`, `13` và dự đoán chính xác lượng RAM cần thêm
- Chỉ ra được đúng 10 dòng code hay sai nhất khi tự viết

## 6.1. Vì sao không cho AI "nghe âm thanh thô"?

Mảng âm thanh 1 giây có 16000 số. Mỗi số chỉ là giá trị áp suất tại một thời điểm 1/16000 giây — quá nhiều số, và mạng nơ-ron nhỏ trên chip không "nhìn" thấy được dáng giọng trong đống số thô.

Hình dung: nói "aaaaaa" 1 giây có hàng nghìn dao động; nói "iiiiii" cũng vậy — nhưng **hình dạng** dao động rất khác nhau. Cái chip cần biết là hình dạng đó, chứ không phải từng rung lắc nhỏ.

Giải pháp: rút gọn 16000 số thành **dáng phổ** (spectral shape):
- Chia âm thanh thành các đoạn ngắn gọi là **khung** (frame)
- Với mỗi khung, chạy FFT (Biến đổi Fourier rời rạc) → biết trong khung đó có những tần số nào: tần số trầm (thấp) hiện cột bên trái, cao (nhọn) bên phải
- Chia phổ thành 13 dải → cộng năng lượng mỗi dải → lấy log

Kết quả: 32 khung × 13 dải = "ảnh" 416 số. Nhỏ gọn, ổn định, hợp làm đầu vào mạng nơ-ron.

> Nếu chưa từng học DSP, hãy nghĩ: "âm thanh như một bó sợi dây đan vào nhau. FFT tách bó đó thành các nhịp rung riêng: mỗi nhịp là một tần số đơn, cao thì tần số lớn, to thì tần số nhỏ."


## 6.2. Các bước tự code — theo thứ tự

Viết mới file `mycourse/audio_features.h` + `mycourse/audio_features.cpp` (nhánh riêng của bạn, để đối chiếu với `main/voice_auth.cpp` sau).

### Bước 1 — Đặt hằng số và cấp phát vùng làm việc

```cpp
// audio_features.h
#pragma once
#include <stdint.h>
#include <stddef.h>

#define SAMPLE_RATE   16000   // 16000 mẫu/giây (buổi 4)
#define FRAME_SIZE    512     // mỗi khung 512 mẫu
#define NUM_FRAMES    32      // 32 khung
#define NUM_BANDS     13      // 13 dải tần
#define FEATURE_COUNT (NUM_FRAMES * NUM_BANDS)  // 416

bool features_init();        // cấp phát PSRAM
bool compute_features(const int16_t* audio, int num_samples, float* out);
```

```cpp
// audio_features.cpp (phần khởi tạo)
#include "audio_features.h"
#include "esp_dsp.h"
#include "esp_heap_caps.h"
#include <string.h>
#include <math.h>

static float* hann_window = nullptr;   // cửa sổ Hann 512 số
static float* fft_buf      = nullptr;  // 1024 số = 512 phần (phần thực + phần ảo)

bool features_init()
{
    // 1) Cửa sổ Hann — mảng 512 float
    hann_window = (float*)heap_caps_malloc(512 * sizeof(float), MALLOC_CAP_SPIRAM);
    if (hann_window == nullptr) return false;
    dsps_wind_hann_f32(hann_window, 512);   // esp-dsp điền sẵn công thức Hann

    // 2) Bộ đệm FFT — 2 * 512 số (phần thực, phần ảo)
    fft_buf = (float*)heap_caps_malloc(1024 * sizeof(float), MALLOC_CAP_SPIRAM);
    if (fft_buf == nullptr) return false;

    // 3) Khởi tạo bảng hệ số FFT trong esp-dsp
    dsps_fft2r_init_fc32(nullptr, CONFIG_DSP_MAX_FFT_SIZE);
    return true;
}
```

**Giải thích dòng quan trọng:**

| Dòng code | Nó làm gì | Vì sao cần |
|---|---|---|
| `heap_caps_malloc(..., MALLOC_CAP_SPIRAM)` | Cấp phát bộ nhớ Pine (PSRAM) ngoài chip, 8MB | Thường RAM trong chip quá nhỏ, FFT làm việc trên PSRAM |
| `dsps_wind_hann_f32(win, 512)` | Esp-dsp tính sẵn công thức Hann (0→512 số) | Không cần tự tính từng `0.5*(1-cos(...))` |
| `dsps_fft2r_init_fc32(...)` | Chuẩn bị bảng bit-reversal & twiddle factor | Bắt buộc trước khi dùng `dsps_fft2r_fc32` |

### Bước 2 — Cửa sổ Hann: xóa "tiếng nhấp nháy" mép khung

Giả sử bạn cắt một đoạn âm 512 mẫu, đùng một cái cắt lìa. Hai đầu đoạn đó bị "cắt đột ngột" — sẽ tạo ra **tiếng click** giả trong phổ (spectral leakage). Cửa sổ Hann làm cho khung "nhỏ dần về 0" ở hai đầu:

```
cửa sổ Hann = 0.5 * (1 - cos(2*pi*n / N))   với n = 0..N-1
                n=0: 0.0
                n=256: 1.0
                n=511: ~0.0
```

Nói thẳng: "giảm âm lượng các mẫu rìa khung xuống 0, giữ mạnh phần giữa — để biên âm không bị kéo giãn khi rời khung." Không có bước này, phổ sai, đặc trưng cũng sai (kể cả AI vẫn chạy nhưng kém chính xác).

### Bước 3 — Viết vòng lặp chính: 32 khung

```cpp
bool compute_features(const int16_t* audio, int num_samples, float* out)
{
    if (audio == nullptr || out == nullptr || num_samples <= 0 ||
        fft_buf == nullptr || hann_window == nullptr) return false;

    // Bước 3.1: tìm |max| — chuẩn hóa âm lượng
    int max_val = 0;
    for (int i = 0; i < num_samples; ++i) {
        int v = (int)audio[i];
        if (v < 0) v = -v;
        if (v > max_val) max_val = v;
    }
    // Giọng quá nhỏ (max < 100) coi như không nói gì → fail
    if (max_val < 100) return false;

    // Bước 3.2: chia khung + FFT + đo.energy dải
    for (int i = 0; i < NUM_FRAMES; i++) {
        // Xóa sạch bộ đệm FFT (32 lượt dùng chung 1 bộ đệm)
        memset(fft_buf, 0, 1024 * sizeof(float));
        int base = i * FRAME_SIZE;   // 0, 512, 1024, ... 15872

        // Nạp 512 mẫu (chuẩn hóa /max rồi nhân cửa sổ Hann)
        for (int j = 0; j < FRAME_SIZE && (base + j) < num_samples; j++) {
            float sample = (float)audio[base + j] / (float)max_val;
            fft_buf[j*2]     = sample * hann_window[j];
            fft_buf[j*2 + 1] = 0.0f;
        }

        // FFT - esp-dsp yêu cầu nhầm lẫn trước rồi hoán vị sau
        dsps_fft2r_fc32(fft_buf, FRAME_SIZE);
        dsps_bit_rev_fc32(fft_buf, FRAME_SIZE);

        // Đo năng lượng 13 dải
        for (int b = 0; b < NUM_BANDS; b++) {
            float energy = 0.0f;
            int bin_start = b * (256 / NUM_BANDS);        // 0, 19, 38, ...
            int bin_end   = (b + 1) * (256 / NUM_BANDS);  // 19, 38, 57, ...

            for (int bin = bin_start; bin < bin_end; bin++) {
                float re = fft_buf[bin*2];
                float im = fft_buf[bin*2 + 1];
                energy += (re*re + im*im);
            }

            // Chia 512^2 để "vừa vặn" khoảng giá trị, cộng 1e-6 tránh log(0)
            float energy_norm = energy / (512.0f * 512.0f);
            out[i * NUM_BANDS + b] = logf(energy_norm + 1e-6f);
        }
    }
    return true;
}
```


> Ghi chú nhỏ: trong code thật của dự án, hàm này nằm trong `main/voice_auth.cpp`, tên `compute_features()` (khoảng dòng 95–138). Khóa học tách code ra file riêng cho bạn dễ tập trung — bên `mycourse/` của bạn.

## 6.3. Chỗ chuyên môn: chỗ nào "như MFCC", chỗ nào khác

Trong code ta vừa viết có 3 khác biệt so với "MFCC chuẩn" trong sách:

| Thành phần | MFCC chuẩn | Cách dự án làm | Vì sao chấp nhận |
|---|---|---|---|
| Cửa sổ tần số | Thang **mel** (bao màng tai người) | Chia đều 256 bin thành 13 dải | Không cần "tai người", cần ổn định trên chip |
| Sin/cos rời rạc | Có bước **DCT** rời rạc (13 giá trị cuối) | Không có DCT | Ít phép tính hơn rất nhiều, đủ phân biệt "giọng mình / người khác" |
| Chuẩn hóa | RMS-normalize hoặc log energy | Chia hết cho `max_val` | Cùng chuẩn hóa mọi khung bằng 1 giá trị, khớp với Python ở buổi 8 |

Cho nên tên chính xác của đặc trưng ta tính là "log-band energy", nhưng **script training Python (buổi 8) cũng tính đúng như vậy**. Đó là quy tắc vàng: **cách trích đặc trưng lúc train PHẢI GIỐNG 100% lúc chạy trên chip** — khác 1 hệ số là model đọc "tab hiệu" sai, đưa ra sai số lớn.

## 6.4. Test chỗ này trước cuộc AI

Vì `compute_features()` tách hẳn ra — bạn có thể test **không cần AI, không cần model**:

```cpp
// Test nhỏ: gọi trong app_main()
#include "audio_features.h"
extern "C" void app_main(void)
{
    features_init();

    int16_t* buf = (int16_t*)heap_caps_malloc(
        SAMPLE_RATE * sizeof(int16_t), MALLOC_CAP_SPIRAM);   // 16000 mẫu = 1 giây
    audio_capture_record(buf, SAMPLE_RATE);                  // thu 1 giây (buổi 4)

    float feats[FEATURE_COUNT];
    bool ok = compute_features(buf, SAMPLE_RATE, feats);
    if (!ok) { printf("features FAIL\n"); return; }

    // In ra tổng hợp: trung bình từng dải
    for (int b = 0; b < NUM_BANDS; b++) {
        float mean = 0;
        for (int i = 0; i < NUM_FRAMES; i++) mean += feats[i * NUM_BANDS + b];
        mean /= NUM_FRAMES;
        printf("band %2d: mean_log_energy = %.4f\n", b, mean);
    }
}
```

**Cách đánh giá kết quả:**
- Nói to đồng thời full 1 giây: các **dải 0–4 (trầm)** năng lượng cao (log năng dưới -3)
- Tiếng gió hay "shhh": năng lượng dịch lên dải cao (băng 6–12)
- Thử nói "ooooo" và tìm dải có năng lượng cao nhất — đó gần bằng **f₀** (nền pitch) của chính giọng bạn

> Chú ý: mỗi dải có độ rộng tương đương khoảng 615 Hz (vì 13 dải chia đều 256 bin trên dải 0–8000 Hz). Đủ phân biệt "giọng bạn" và "giọng người khác".

## 6.5. Đối chiếu đáp án mẫu

Mở `main/voice_auth.cpp`, tìm `compute_features()` (dòng ~95). So từng phần:

| Khúc bạn viết | Khúc trong dự án | Giống / khác |
|---|---|---|
| Đặt tên `NUM_FRAMES`, `NUM_BANDS` | Dùng số cứng `32`, `13` | Chung kết quả, tên được chỉ rõ hơn để dễ đọc |
| `features_init()` PSRAM | Phần hỗ trợ `voice_auth_init()` cùng bố cục | Giống |
| Chuẩn hóa `/max_val` | Giống | **Bắt buộc giống** — quy tắc vàng |
| `bin_start = b * (256/13)` | Giống | **Bắt buộc giống** |
| `energy / (512*512)` | Giống | **Bắt buộc giống** |

## 6.6. Checklist tự kiểm

- [ ] Biết công thức Hann và giải thích vì sao cần
- [ ] Viết được `compute_features()` mà không cần xem đáp án
- [ ] Trả lời được: 1 khung ở SAMPLE_RATE 16000 dài bao nhiêu mili giây? (512/16000 = **32 ms**)
- [ ] Trả lời được: nếu thay `13` dải thành `26`, ảnh đặc trưng thành hình gì, dùng nhiều RAM hơn bao nhiêu? (32×26 = 832 float = **3.4 KB PSRAM**)
- [ ] Test được: nói 1 giây, in `mean_log_energy` cho từng dải, các dải 0–4 cao hơn dải 10–12

**Lỗi hay gặp** khi tự code:
1. Quên `dsps_fft2r_init_fc32()` → FFT trả về rác (số hoang), model train không bao giờ tốt
2. Quên memset trong vòng 32 lượt → khung sau "cộng dồn" khung trước
3. Nhân cửa sổ **sau** FFT → công thức ứng dụng sai; Hann luôn nhân trước khi FFT
4. Quên `+ 1e-6f` → năng lượng 0 làm `logf(-inf)` → đặc trưng = `-inf`, AI dính NaN
5. Đổi số `13` trên Python mà không đổi trên C++ (hoặc ngược lại) — lỗi "quy tắc vàng" kinh điển, sẽ được giải thích tường minh ở buổi 8

