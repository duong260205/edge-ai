# Buổi 8 — Thu âm dataset & huấn luyện model (2 con đường)

## 8.0. Mục tiêu buổi học

Tính đến buổi 7, chạy được AI nhưng dùng **model mẫu của dự án** — model đó "không biết" giọng bạn. Buổi 8 này bạn làm 2 việc:

1. **Thu data giọng của chính mình** — script `collect_data.py` (làm phần cứng chip thu âm, lưu .wav lên máy tính)
2. **Train model riêng của bạn** theo 2 con đường — chọn 1:
   - **Con đường A (tự viết):** chạy `train_quantize_export.py` — dùng TensorFlow/Keras, tự thực thi trên máy tính
   - **Con đường B (nhanh):** dùng **Edge Impulse** — web no-code/low-code, đủ cho các dự án tương tự, không cần code Python

Kết quả con đường A → `model_data.cc` + `.h` chèn vào firmware → model biết giọng bạn.

## 8.1. Thu dataset giọng của bạn — tự code `collect_data.py`

### Nguyên lý

Chip thu âm (buổi 4) truyền dữ liệu qua UART/USB lên PC, PC lưu thành `.wav`. Dataset gồm 2 lớp (2 thư mục):

```
dataset/
├── target/    ← 40 file .wav: giọng BẠN nói cùng 1 câu (VD: "mở cửa ra")
└── noise/     ← 40 file .wav: giọng người khác nói / tiếng nền
```

### Script Python — tự viết từng phần (đáp án là `main/collect_data.py`, chỉ 36 dòng)

```python
import serial        # pip install pyserial
import wave
import numpy as np

PORT = "COM5"        # đổi theo port của bạn (xem Device Manager)
SAMPLE_RATE = 16000
CHUNK = 256

# CẤU HÌNH: tên lớp và số file muốn thu
CLASSES = ["target", "noise"]
FILES_PER_CLASS = 40

ser = serial.Serial(PORT, 115200, timeout=1)

for cls in CLASSES:
    for i in range(FILES_PER_CLASS):
        # 1) Bảo chip: thu 1 giây và gửi lên
        ser.write(f"rec:{cls}\n".encode())
        # 2) Đọc đủ 16000 mẫu * 2 byte = 32000 byte
        raw = ser.read(32000)
        samples = np.frombuffer(raw, dtype=np.int16)
        # 3) Lưu thành .wav
        with wave.open(f"dataset/{cls}/sample_{i:03d}.wav", "w") as f:
            f.setnchannels(1)            # mono
            f.setsampwidth(2)            # 16-bit
            f.setframerate(SAMPLE_RATE)
            f.writeframes(samples.tobytes())
    print(f"Đã thu xong lớp '{cls}'")
```

**Giải thích từng dòng:**

| Dòng | Ý nghĩa |
|---|---|
| `serial.Serial(PORT, 115200)` | Mở cổng USB mà chip đang cắm |
| `ser.write(f"rec:{cls}\n")` | Nhắn cho firmware: "thu 1 giây, gửi lên ngay" (lệnh này bạn phải **tự thêm vào firmware** — xem mục 8.2 "lệnh thu âm") |
| `np.frombuffer(raw, dtype=np.int16)` | 2 byte = 1 số int16, ghép thành mảng 16000 |
| `f.writeframes(...)` | Vào file .wav; PC nghe được là 16-bit PCM mono 16 kHz |

### Gợi ý môi trường thu

- Giọng to vừa (cách microphone ~20 cm), không quá khẽ và không quá to
- **Lớp target:** thu ở nhiều giờ khác nhau trên ngày, có màn mở normalmente (không kẹp văn chì) — để model học "giọng bạn mọi lúc trong ngày"
- **Lớp noise:** mời người khác nói câu, hoặc mở tiếng nền (TV / nhạc / tiếng gõ) — quan trọng là **giọng BẠN không được nằm trong noise**

## 8.2. Thêm "lệnh thu âm" vào firmware

Script phía PC gửi lệnh `rec:\n` qua UART — firmware phải **chờ lệnh, thu 1 giây, đẩy dữ liệu trả về**. Tự viết:

```cpp
// mycourse/data_collection_task.cpp
#include "audio_capture.h"
#include "driver/uart.h"

#define UART_NUM   UART_NUM_0
#define BUF_SIZE   1024

void data_collection_task(void* arg)
{
    uart_driver_install(UART_NUM, BUF_SIZE*2, 0, 0, nullptr, 0);
    uart_param_config(UART_NUM, &(uart_config_t){
        .baud_rate = 115200, .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE, .stop_bits = UART_STOP_BITS_1,
    });

    int16_t* buf = (int16_t*)heap_caps_malloc(
        SAMPLE_RATE * sizeof(int16_t), MALLOC_CAP_SPIRAM);

    uint8_t cmd[16];
    while (true) {
        int len = uart_read_bytes(UART_NUM, cmd, 5, pdMS_TO_TICKS(500));
        if (len == 5 && memcmp(cmd, "rec:\n", 5) == 0) {
            audio_capture_record(buf, SAMPLE_RATE);  // thu 1 giây (buổi 4)
            // Đẩy 32000 byte nguyên mảng int16 xuống PC
            uart_write_bytes(UART_NUM, buf, SAMPLE_RATE * sizeof(int16_t));
        }
    }
}
```

Chạy 2 bên: PC gõ `python collect_data.py` → tự động 80 file .wav thu được sau ~2 phút.

## 8.3. Con đường A — hiểu từng bước `train_quantize_export.py` (142 dòng)

Đây là đáp án của dự án: `main/train_quantize_export.py`. Đọc từng khối:

### Khối 1 — Chuẩn hóa âm lượng + trích MFCC **KHỚP 100% C++**

```python
max_val = np.max(np.abs(audio))
if max_val > 0:
    audio = audio / max_val               # khớp với C++: chia /max_val (buổi 6)

frames, hop, fft_size = 32, 512, 512      # khớp: 32 khung, 512
window = 0.5 * (1.0 - np.cos(2.0 * np.pi * np.arange(fft_size) / fft_size))
        # khớp công thức Hann (buổi 6)

for i in range(frames):
    segment = audio[i*hop : i*hop + fft_size]
    if len(segment) < fft_size:
        segment = np.pad(segment, (0, fft_size - len(segment)), 'constant')

    fft_result = np.fft.rfft(segment * window)
    for b in range(13):
        bin_start = b * 19                # 256/13 = 19 (chia lấy nguyên!)
        energy = np.sum(np.abs(fft_result[bin_start:(b+1)*19])**2)
        features[i, b] = np.log(energy / (512.0*512.0) + 1e-6)
```

> **Quy tắc vàng (lặp lần 2):** 4 con số `16000 / 512 / 512 / 13` phải GIỐNG NHAU tuyệt đối C++ và Python. Nếu ở giờ muộn bạn muốn đổi (VD: n_mels 13 → 20), phải đổi cả 2. `main/training_config.json` là nơi ghi các con số này — script chính nó cũng đọc.

**Vì sao phải khớp?** Model train trên ảnh 32×13 có miền giá trị do dữ liệu train sinh ra (ví dụ log-energy ~ [-18, -3]). Chip cũng tính 32×13 cùng công thức → giá trị nằm cùng miền. Nếu chip tính khác 1 chút (khác cửa sổ, khác chuẩn hóa), ảnh vào model ở "miền khác" — model trả kết quả sai mà không thông báo — score chạy lung tung.

### Khối 2 — Model CNN nhỏ

```python
model = models.Sequential([
    layers.Input(shape=(32, 13, 1)),        # ảnh 32 × 13 × 1 kênh
    layers.Conv2D(8, 3, activation='relu', padding='same'),   # học 8 "bộ lọc" (pattern)
    layers.MaxPooling2D(2),                 # co 1 lần: 32×13 → 16×7
    layers.Conv2D(16, 3, activation='relu', padding='same'),  # học 16 pattern phức tạp hơn
    layers.MaxPooling2D(2),                 # → 8×4
    layers.Flatten(),                       # duỗi thành 256 số (8*4*16)
    layers.Dense(32, activation='relu'),
    layers.Dense(1, activation='sigmoid'),  # 1 số từ 0 đến 1 → khớp chip (buổi 7)
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
model.fit(X, y, epochs=15, batch_size=16, validation_split=0.2)
```

**Hình dung “Conv2D là gì”?** Ảnh đặc trưng 32×13 như 1 tấm ảnh xám; Conv2D dùng “kính lúp” 3×3 trượt qua ảnh, mỗi lần trượt trả về “có pattern này không” (số to = pattern rõ). 8 kính lúp đầu đó → 8 “bản đồ phát hiện”. Mạng càng sâu càng học pattern tổng hợp: nhận diện “dáng giọng của đúng một người”. 

### Khối 3 — Lượng hóa INT8: đóng bản model vào MCU-friendly

```python
def representative_data_gen():            # lấy 100 mẫu đại diện X
    for input_value in tf.data.Dataset.from_tensor_slices(X).batch(1).take(100):
        yield [tf.cast(input_value, tf.float32)]

converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]           # bật lượng hóa
converter.representative_dataset = representative_data_gen     # dữ liệu mẫu để đo scale
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type  = tf.int8                      # đầu vào/ra đều INT8
converter.inference_output_type = tf.int8

tflite_model = converter.convert()
with open("voice_auth.tflite", "wb") as f:
    f.write(tflite_model)
```

Chuyện gì xảy ra lúc này?
- TensorFlow **đo** hành vi 100 ảnh đặc trưng (representative) → tự tìm `scale` + `zero_point` **cho từng tensor** trong model. Đó chính là tại sao code C++ đọc được `input_tensor->params.scale` — TF mang số đó trọn vẹn trong file `voice_auth.tflite`.
- Mỗi weight float 4 byte → INT8 1 byte: model từ ~600 KB float → ~150 KB INT8 → **dung lượng flash nhẹ hơn 4 lần**.

### Khối 4 — Xuất sang C (`export_to_c`): model thành 1 mảng byte

```python
def export_to_c(tflite_bytes, output_cc, output_h):
    array_name = "g_voice_auth_model_data"

    with open(output_h, "w") as f:
        f.write("extern const unsigned char g_voice_auth_model_data[];\n")
        f.write("extern const int g_voice_auth_model_data_len;\n")

    with open(output_cc, "w") as f:
        f.write("const unsigned char g_voice_auth_model_data[] = {\n  ")
        for i, val in enumerate(tflite_bytes):
            f.write(f"0x{val:02x}, ")
            if (i + 1) % 12 == 0: f.write("\n  ")
        f.write(f"\n}};\nconst int g_voice_auth_model_data_len = {len(tflite_bytes)};\n")

export_to_c(tflite_model, "model_data.cc", "model_data.h")
```

2 file mới sinh: copy vào `main/` và **build + nạp lại firmware** — chip dùng model của bạn ngay từ lần boot sau.


## 8.4. Con đường B — Edge Impulse (nhanh, ít code)

> Con đường B dùng khi: bạn ở giai đoạn "làm demo nhanh", hoặc muốn so sánh chất lượng model thương mại vs tự viết. Toàn bộ flow là kéo–thả trên web, không cần viết Python.

Bốn bước chính trong Edge Impulse (bản miễn phí đủ dùng):

1. **Tạo project** → chọn "Audio" project type, tạo 2 nhãn: `target` và `noise`
2. **Upload data** — kéo-thả 80 file .wav dataset vừa thu ở mục 8.1
3. **Cấu hình Impulse** (cần khớp với C++ của dự án, không dùng tùy chọn mặc định của EI!):
   - **Window size = 1000 ms** (1 giây — đúng như chip thu 1 giây)
   - **Window increase = 500 ms** (trượt 50% giữa các cửa sổ để có nhiều mẫu hơn)
   - Processing block: **MFCC**, giữ số dải/mel khớp với 13 dải của dự án
   - Learning block: **D CNN (Keras)**, số layer dựa theo giải đáp sau
4. **Train → Export** — dùng nút "Deployment" chọn **C++ library, INT8 quantized**, tải `.zip` chứa model — bên tương tự khối 3–4 con đường A

**So sánh nhanh 2 con đường:**

| Tiêu chí | Con đường A (tự viết Python) | Con đường B (Edge Impulse) |
|---|---|---|
| Thời gian | 30 phút chạy + 15 phút train | 10 phút trên web |
| Kiểm soát | 100% — đổi chủ động MFCC / model / output | Được phép đổi ít |
| High-level track | Dễ kiểm soát — **bắt buộc khớp C++ như mục 8.3** | Giải quyết tự động, CÓ THỂ khác C++ của dự án → dùng firmware riêng của EI |
| Khi nên dùng | Học tập — hiểu từng dòng | Làm dự án thực, deadline, có được model tốt hơn |
| Miễn phí? | Đã free vì chạy trên máy bạn | Plan Creator (miễn phí) đã đủ |

> **Chú ý quan trọng nếu dùng đường B:** Edge Impulse dùng bộ MFCC của riêng nó — **khác với dự án tự code C++ của bạn**. Sau khi EI train xong và xuất "Deployment → C++ library", cả phần trích đặc trưng của EI cũng đi kèm, thay cho code buổi 6 của ta. Đây là lý do dự án gốc chọn con đường A: kiểm soát từng dòng để các con số `32/512/512/13` khớp chính xác.

## 8.5. Checklist tự kiểm

- [ ] Tạo được 80 file .wav (40 target + 40 noise) bằng script tự viết
- [ ] Chạy được `train_quantize_export.py`, sinh 2 file `model_data.cc`/`.h`
- [ ] Copy vào `main/`, build + flash lại, giọng bạn cho `score > 0.7`
- [ ] Giải thích được: 4 con số vàng `16000/512/512/13` xuất hiện ở đâu (C++ buổi 6, Python khối 1, `training_config.json`)
- [ ] Biết chọn con đường B khi nào (deadline, so sánh, ít thời gian)

**Lỗi hay gặp:**
1. **Data lệch lớp** — 60 target / 5 noise: model "chọn luôn target với mọi giọng" → FAR (chấp nhận giọng lạ) cao đáng sợ. Cân bằng 1:1.
2. **Quy tắc vàng bị vi phạm** — sửa Python 32→24 khung, quên sửa C++ → score nhảy loạn. Bảng đối chiếu ở mục 6.5 và 7.5.
3. **Quên đồng bộ `main/training_config.json`** — file này là nơi đối soát số, ít dùng nhưng nên cập nhật khi đổi hằng số.
4. **Edge Impulse train chưa đủ epochs** → model chất lượng kém — bật "Custom epochs" ≥ 30.

