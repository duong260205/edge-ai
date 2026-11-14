# Buổi 7 — Tự code khối AI trên chip: TFLite Micro + lượng hóa INT8

## 7.0. Mục tiêu buổi học

Buổi 6 bạn biến 1 giây âm thành "ảnh" 416 số (32×13). Buổi 7 bạn viết code đưa ảnh đó qua **màn AI thật trên chip**: nạp model INT8 (dùng buổi 8 nhưng phiên bản mẫu đã có sẵn), chạy suy luận với **TensorFlow Lite Micro** (viết tắt: TFLM), lấy ra điểm số `score` từ 0 → 1.

Sau buổi này, bạn tự viết được:
- Hàm `voice_ai_init()` — nạp model, chuẩn bị "vùng làm việc" (tensor arena), khai báo các phép tính (op resolver)
- Hàm `voice_ai_run(features, &score)` — đưa đặc trưng vào model, gọi `Invoke()`, đọc kết quả INT8 → float

> Không cần đợi buổi 8: model dùng để test ngay sẽ được cấp sẵn là file `model_data.cc` đã nén sẵn (phiên bản mẫu để học, chúng ta thay bằng model của chính bạn tại buổi 8).

## 7.1. Tại sao lại dùng TFLite Micro (không dùng PyTorch / TensorFlow thường)?

Ba lý do, từ đó hình dung được "TFLM là gì":

1. **Model phải hiểu INT8 không phải float để tiết kiệm bộ nhớ & phép tính.** Python (buổi 8) đóng gói MCU-friendly model dạng INT8 (từ lượng hóa). Trên PC dùng float 4 bytes; trên chip dùng INT8 1 byte — RAM FFT cộng dồn cho trời.
2. **TFLM chỉ có "phần chạy suy luận" (runtime) không có huấn luyện.** Trên PC dùng `tf.keras.fit()`, trên chip chỉ `Invoke()` — chạy model với dữ liệu vào, trả dữ liệu ra (không chỉnh trọng số).
3. **Chỉ cần chỉ rõ nó làm phép tính gì.** 8 loại op trong `MicroMutableOpResolver<8>` — model dùng đúng 8 phép tính, ta chỉ khai báo đủ 8.

## 7.2. Khái niệm cốt lõi — tensor arena là gì?

`tensor_arena` là **bộ nhớ tạm để model chạy**: chứa weight đã nạp, dữ liệu đầu vào, các lớp giữa, và dữ liệu ra. Ví dụ model có lớp Conv2D nhận ảnh 32×13, nó sẽ tạo 1 "bàn làm việc" trong arena để thử: mỗi lớp tính xong ghi kết quả vào `tensor_arena`, lớp sau đọc lên.

- Arena **cố định** — cấp phát một lần lúc `init()` (dùng `heap_caps_malloc(..., MALLOC_CAP_SPIRAM)`), không cấp phát lại mỗi lần chạy — vì RAM heap trên chip rất hạn chế, và cấp phát nhiều lần chậm
- Arena **quá nhỏ → `AllocateTensors()` fail**; quá lớn → lãng phí RAM (được dùng bởi camera & web stream ở các buổi sau)

Đây cũng là lý do dự án cấp `40 KB` (mã `kTensorArenaSize = 40 * 1024`).


## 7.3. Các bước tự code

Viết `mycourse/voice_ai.h` + `mycourse/voice_ai.cpp`:

```cpp
// voice_ai.h
#pragma once
#include <stdint.h>
#include <stddef.h>

bool voice_ai_init();                              // nạp model 1 lần lúc bật máy
bool voice_ai_run(const float* features, float* score_out);   // 1 lần suy luận
```

### Bước 1 — Nạp model và chuẩn bị arena

```cpp
// voice_ai.cpp
#include "voice_ai.h"
#include "esp_log.h"
#include "esp_heap_caps.h"

#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "model_data.h"      // sinh bởi train_quantize_export.py (buổi 8)

static const char* TAG = "VOICE_AI";

namespace {
    const tflite::Model* model = nullptr;
    tflite::MicroInterpreter* interpreter = nullptr;
    TfLiteTensor* input  = nullptr;
    TfLiteTensor* output = nullptr;

    constexpr int kTensorArenaSize = 40 * 1024;
    constexpr int FEATURE_COUNT    = 32 * 13;   // 416 (khớp buổi 6)

    uint8_t* tensor_arena = nullptr;
}

bool voice_ai_init()
{
    // 1) Trỏ model: mảng byte đã chèn sẵn trong firmware
    model = tflite::GetModel(g_voice_auth_model_data);
    if (model == nullptr) {
        ESP_LOGE(TAG, "GetModel() = null");
        return false;
    }

    // 2) Cấp arena trong PSRAM
    tensor_arena = (uint8_t*)heap_caps_malloc(kTensorArenaSize, MALLOC_CAP_SPIRAM);
    if (tensor_arena == nullptr) {
        ESP_LOGE(TAG, "PSRAM alloc failed (arena %d B)", kTensorArenaSize);
        return false;
    }

    // 3) Khai báo 8 loại phép tính model dùng
    static tflite::MicroMutableOpResolver<8> resolver;
    resolver.AddConv2D();
    resolver.AddMaxPool2D();
    resolver.AddReshape();
    resolver.AddFullyConnected();
    resolver.AddLogistic();
    resolver.AddShape();
    resolver.AddStridedSlice();
    resolver.AddPack();

    // 4) Tạo interpreter + phân bổ tensor bên trong arena
    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena, kTensorArenaSize);
    interpreter = &static_interpreter;

    if (interpreter->AllocateTensors() != kTfLiteOk) {
        ESP_LOGE(TAG, "AllocateTensors() failed — arena quá nhỏ?");
        return false;
    }

    // 5) Lấy con trỏ tensor vào/ra để viết dữ liệu nhanh
    input  = interpreter->input(0);
    output = interpreter->output(0);
    ESP_LOGI(TAG, "TFLM ready (arena=%d KB, input scale=%.4f zp=%d)",
             kTensorArenaSize / 1024, (double)input->params.scale,
             input->params.zero_point);
    return true;
}
```

**Giải thích các dòng "quen mặt mới" của TFLM:**

| Đoạn | Ý nghĩa |
|---|---|
| `GetModel(g_voice_auth_model_data)` | Biến mảng byte C → cấu trúc `Model` mà runtime TFLM đọc được |
| `MicroMutableOpResolver<8>` | "Menu các phép tính được phép" — `8` là số tối đa |
| `AddConv2D()` … `AddPack()` | Liệt kê từng phép tính mà model cần |
| `MicroInterpreter(...)` | Đối tượng điều hành ngay: nạp weight vào arena, tính tuần tự từng op |
| `AllocateTensors()` | Chia `tensor_arena` thành các ô cho từng tensor (input, giữa, output) |
| `interpreter->input(0)` | Chỉ tensor đầu vào của model (tensor số 0 là duy nhất) |


### Bước 2 — Lượng hóa ngược: 416 số float → 416 số INT8

Model được luyện để **đầu vào là INT8**. Đặc trưng của mình là float → phải "ép" qua phép lượng hóa:

```cpp
static void quantize_features(const float* features, TfLiteTensor* input_tensor)
{
    float scale     = input_tensor->params.scale;       // bước nhảy
    int   zero_point = input_tensor->params.zero_point;  // số 0 biểu diễn thành INT8 nào
    if (scale == 0.0f) scale = 0.1f;                     // dự phòng khi model thiếu tham số

    for (int i = 0; i < FEATURE_COUNT; ++i) {
        // công thức: q = round(f / scale) + zero_point, kẹp trong [-128, 127]
        float q = roundf(features[i] / scale) + (float)zero_point;
        if (q < -128.0f) q = -128.0f;
        if (q >  127.0f) q = 127.0f;
        input_tensor->data.int8[i] = (int8_t)q;
    }
}
```

**Hình dung "lượng hóa":**

- Giá trị float thật: `f`
- Trên chip lưu dạng INT8 với công thức: `f ≈ scale * (q - zero_point)`
- Vì vậy đưa dữ liệu vào chỉ việc làm ngược: `q = round(f / scale) + zero_point`
- Cả 2 số này (`scale`, `zero_point`) do chính **model tự mang theo** trong tham số `input_tensor->params`

### Bước 3 — Chạy `Invoke()` và đọc kết quả

```cpp
bool voice_ai_run(const float* features, float* score_out)
{
    if (!interpreter || !features || !score_out) return false;

    // 1) Lượng hóa: 416 float → INT8 và ghi trực tiếp vào tensor đầu vào
    quantize_features(features, input);

    // 2) Chạy toàn bộ mạng nơ-ron (tính từ input → output)
    if (interpreter->Invoke() != kTfLiteOk) {
        ESP_LOGE(TAG, "Invoke() failed");
        return false;
    }

    // 3) Ngược lượng hóa: 1 số INT8 ra → float [0, 1]
    int8_t q = output->data.int8[0];                          // model trả 1 chữ số
    float pred = ((float)q - output->params.zero_point)
                 * output->params.scale;

    *score_out = pred;
    ESP_LOGI(TAG, "score=%.3f (raw q=%d)", pred, q);
    return true;
}
```

> Chú ý: model ta dùng có **hàm sigmoid với output 1 giá trị** (xác suất "đây là giọng thành viên"). Nếu model của bạn có 2 giá trị output (softmax `[giọng lạ, giọng đúng]`), bạn đổi cách đọc điểm: lấy 2 giá trị, ngược lượng hóa cả hai rồi chọn nhãn có điểm cao hơn. Chi tiết train 2 kiểu này ở **buổi 8**.

## 7.4. Chấm điểm gộp: model + so sánh "khuôn mẫu giọng"

Model chỉ cho một điểm (prediction). Dự án của ta đi xa hơn 1 bước: **lưu 1 bản ghi đặc trưng mẫu (profile) của giọng đúng, và chấm "độ tương đồng cosine"** so với bản hiện tại. Điểm cuối:

```
final_score = 0.35 * model_score + 0.65 * cosine_score
```

Tại sao lại dùng 2 cách chấm? Chúng bù lỗi cho nhau:
- Model (CNN) **phát hiện "dáng phổ của giọng người quen"**, mạnh với nhiễu
- Cosine so trực tiếp ảnh 416-số, **phát hiện "giọng này rất giống lúc enroll"**, mạnh với giọng chưa từng nghe
- Khi model này "làm việc tốt" trên nhiều giây audio, cosine làm ổn định điểm đối chiếu profile đầu vào

**Cosine 1 dòng để hình dung:** nếu ảnh 416 số là 1 mũi tên trong không gian 416 chiều, cosine = "hai mũi tên đứng cùng hướng" — 1.0 là cùng hướng, 0 là hai mũi tên vuông góc (khác hẳn), -1 là ngược (chẳng liên quan).

### Mã tự viết giải thích (cosine gộp trong verify)

```cpp
bool voice_ai_verify(const float* features, float* score_out)
{
    // 1) Chạy model — mục 7.3
    float model_score;
    if (!voice_ai_run(features, &model_score)) return false;

    // 2) Nếu không có profile → tin model thôi
    if (!voice_profile_loaded()) {
        *score_out = model_score;
        return true;
    }

    // 3) Đủ cos: so sánh với profile (mảng 416 số lưu sẵn)
    float prof[FEATURE_COUNT];
    voice_profile_read(prof);            // hàm của buổi 6, đọc NVS

    float dot = 0, norm_a = 0, norm_b = 0;
    float mean_a = 0, mean_b = 0;
    for (int i = 0; i < FEATURE_COUNT; ++i) {
        mean_a += features[i];
        mean_b += prof[i];
    }
    mean_a /= FEATURE_COUNT;
    mean_b /= FEATURE_COUNT;

    for (int i = 0; i < FEATURE_COUNT; ++i) {
        float a = features[i] - mean_a;   // trừ trung bình - cosine vẫn cần "giọng to"
        float b = prof[i] - mean_b;       // nhỏ cũng được chấm như giọng to
        dot   += a * b;
        norm_a += a * a;
        norm_b += b * b;
    }
    float cosine = (norm_a > 0 && norm_b > 0)
                 ? dot / sqrtf(norm_a * norm_b)
                 : -1.0f;

    // 4) Gộp theo công thức dự án
    float final_score = 0.35f * model_score + 0.65f * ((cosine + 1.0f) * 0.5f);
    *score_out = final_score;
    return true;
}
```


## 7.5. Đối chiếu đáp án mẫu — `main/voice_auth.cpp`

| Phần bạn viết | Trong dự án | Giống / khác |
|---|---|---|
| `kTensorArenaSize 40*1024`, PSRAM | Giống (dòng 21) | Giống |
| `MicroMutableOpResolver<8>` với 8 op | Giống (dòng 196–206) | Giống |
| `quantize_features` (công thức lượng hóa) | `compute_mfcc_like_features` (dòng 140–148) | CÙNG công thức — chỉ khác tên |
| Đọc output INT8 → float | Giống (dòng 297–299) | Giống |
| Chấm cosine gộp `0.35 / 0.65` | Giống (dòng 301–322) | Giống |
| Ngưỡng `0.70` dùng để chốt đúng/sai | `AUTH_THRESHOLD 0.7f` trong `voice_auth.h` | **Bắt buộc giống** |

**Ba chỗ dự án làm mà bạn phải ghi nhớ:**

1. **Lọc tiếng ồn bằng RMS trước khi chạy** — trong `voice_auth_verify` dòng 280–290: tính RMS của mảng âm thanh, **nếu RMS < 30 thì coi là im lặng, không chạy model**, trả `-1.0`. Trường này tiết kiệm CPU (model Invoke hết ~90ms trên chip), tránh hàng đợi "AI dọa".
2. **Chấm điểm nhiều lần** — `voice_auth_verify_multi` (dòng 345–374) chạy model trên 3 lần thu âm (3 giây) và **trung bình điểm**, thêm điều kiện **tối thiểu 2 lượt hợp lệ**. Bản chất giống chấm bài thi nhiều vòng: một lượt đo lỗi thì bỏ, không phá kết quả tổng.
3. **Chỉ có 1 profile trong firmware** — dự án giữ profile giọng **thành viên duy nhất** (cửa nhà bạn dùng dành chỗ riêng). Muốn nhiều người -> mở rộng sau trong buổi 11.

## 7.6. Test ngay với model mẫu

Ghép 3 buổi liền nhau — thu âm → MFCC → AI:

```cpp
extern "C" void app_main(void)
{
    features_init();                // buổi 6
    voice_ai_init();                // buổi 7

    int16_t* buf = (int16_t*)heap_caps_malloc(
        SAMPLE_RATE * sizeof(int16_t), MALLOC_CAP_SPIRAM);

    while (true) {
        audio_capture_record(buf, SAMPLE_RATE);          // buổi 4: thu 1 giây

        float feats[FEATURE_COUNT];
        if (!compute_features(buf, SAMPLE_RATE, feats)) { // buổi 6
            printf("qua nho/am lanh\n");
            continue;
        }

        float score;
        if (voice_ai_verify(feats, &score)) {             // buổi 7
            printf("score=%.3f  → GIỌNG ĐÚNG\n", score);
        } else {
            printf("score=%.3f  → GIỌNG LẠ/IM LẶNG\n", score);
        }
    }
}
```

Mong đợi để chạy được ngay là model mẫu trong dự án chưa nghiêng ("giọng ai đó" trong dataset cài sẵn). Chạy trả hết số kiểu `score=0.3~0.6` là bình thường — **model đã đúng để gọi chạy; muốn nó "biết giọng bạn", sang buổi 8 train model riêng**.

## 7.7. Checklist tự kiểm

- [ ] Giải thích được **tensor arena** và vì sao cấp 1 lần
- [ ] Giải thích được **quy trình lượng hóa**: `f → q = round(f/scale) + zero_point`, và ngược lại khi đọc output
- [ ] Nói được 8 op trong `MicroMutableOpResolver<8>` này dùng cho thông thường: Conv2D, MaxPool2D, Reshape, FullyConnected, Logistic, Shape, StridedSlice, Pack
- [ ] Giải thích được công thức điểm cuối `0.35 * model + 0.65 * cosine` (mục 7.4)
- [ ] Ghép được vòng chạy: thu âm → MFCC → AI, in `score`

**Lỗi hay gặp:**
1. **Quên `resolver.Add...()`** cho một op mà model cần → `AllocateTensors()` fail với thông báo tối nghĩa; hãy đọc cấu trúc model bằng tool có sẵn của dự án `tools/analyze_tflite_model.py` để biết model dùng đúng op nào
2. **Ghi trực tiếp float vào `input_tensor->data.int8`** — chip hiểu nhầm bởi kiểu dữ liệu sai, model sẽ ra kết quả ngẫu nhiên — luôn đi qua `quantize_features()`
3. **So sánh output với `0.5` nhưng quên ngược lượng hóa** — INT8 là số nguyên tâm đã lệch zero_point, không phải float 0→1
4. **`kTensorArenaSize` lớn dính RAM heap** — nếu PSRAM bị camera / web dùng mất, cái này phải giảm, hoặc chọn chỗ khác cấp phát

