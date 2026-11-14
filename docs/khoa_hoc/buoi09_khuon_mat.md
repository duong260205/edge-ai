# Buổi 9 — Tự code nhận diện khuôn mặt (Camera + ESP-DL)

## 9.0. Mục tiêu buổi học

Cho tới buổi 8, chip "nhận ra giọng". Bây giờ chip cần "nhận ra mặt". Buổi 9 viết `face_recognition.cpp` để:
- Chụp khung hình từ camera **OV2640**
- **Tìm** khuôn mặt trong khung (detector)
- **So sánh** khuôn mặt đó với mặt đã lưu (recognizer → embedding + cosine)
- Trả ID + tên + điểm tương đồng

Đây là **hệ lớn nhất trong dự án** (496 dòng) — nhưng có quy trình rõ ràng. Bạn sẽ tự viết một bản **đơn giản 3 bước** trước, rồi mở rộng lên thành bản của dự án.

## 9.1. Quy trình hình chữ L — hình dung trước khi code

```
Khung hình từ camera (JPEG)
      │
      ▼
[1] Giải mã JPEG → RGB888   (dl::image::sw_decode_jpeg)
      │
      ▼
[2] Tìm khuôn mặt           (face_detector->run → returns boxes + score)
      │ Có ≥ 1 khuôn mặt?
      ▼
[3] Nhận diện khuôn mặt     (face_recognizer->recognize → embedding → cosine)
      │ similarity ≥ ngưỡng?
      ▼
Tìm tên tương ứng trong "cơ sở dữ liệu khuôn mặt" (face_database)
```

2 khối dùng AI thật của ESP-DL:
- **Detector:** MSRMNP — mạng nhỏ xác định "hộp chữ nhật + 5 điểm mốc (mắt, mũi, miệng)" quanh khuôn mặt
- **Recognizer:** HumanFaceRecognizer — chạy **MobileFaceNet** lấy "mảnh mã hoá gương mặt" (embedding) rồi TÍNH COSINE với embedding đã lưu

> Đây chính là thiết kế như buổi 7 — model AI chỉ trả "mảnh mã hoá" rồi ta tự chấm cosine; khác duy nhất: model không có sigmoid, ta tự dùng ngưỡng `similarity ≥ 0.5`.

## 9.2. Các bước tự code — bản 3 bước dùng được ngay

Full code 80 dòng, tự viết từng khối. Giả sử camera đã init sẵn (`camera_init()` — buổi 10 sẽ chi tiết, trong mục này ta chuẩn bị sẵn).

### Bước 1 — Điều kiện môi trường (CMakeLists)

Bổ sung 1 tùy chọn trong `idf_component.yml` và kiểm `CMakeLists.txt` đã có:

```yaml
# main/idf_component.yml
dependencies:
  espressif/esp-dl: "^3.0.0"     # thư mục AI của Espressif
  espressif/esp32-camera: "^2.0.0"
```


### Bước 2 — Tự viết 3 hàm lõi

Viết file `mycourse/face_auth.cpp`:

```cpp
#include "dl_image_jpeg.hpp"
#include "human_face_detect.hpp"
#include "human_face_recognition.hpp"

static human_face_detect::MSRMNP *face_detector = nullptr;
static HumanFaceRecognizer *face_recognizer = nullptr;

bool face_auth_init()
{
    // 1) Tạo detector (mạng tìm khuôn mặt)
    face_detector = new human_face_detect::MSRMNP();
    if (face_detector == nullptr) return false;

    // 2) Tạo recognizer (mạng so sánh khuôn mặt: MobileFaceNet + cosine)
    face_recognizer = new HumanFaceRecognizer();
    if (face_recognizer == nullptr) return false;

    return true;
}

// Đăng ký 1 khuôn mặt mới: chụp 1 khung + tên
bool face_auth_enroll(camera_fb_t* fb, const char* name)
{
    // 2.1) Giải mã JPEG → RGB888 — ESP-DL cần "ảnh RGB" không phải JPEG nén
    dl::image::jpeg_img_t jpeg_img = {
        .data     = (void*)fb->buf,
        .data_len = (size_t)fb->len,
    };
    auto img = dl::image::sw_decode_jpeg(jpeg_img,
                                         dl::image::DL_IMAGE_PIX_TYPE_RGB888);
    if (img.data == nullptr) return false;

    // 2.2) Tìm khuôn mặt trong ảnh
    auto faces = face_detector->run(img);
    if (faces.size() == 0) {           // không thấy mặt → nạp thất bại
        heap_caps_free(img.data);
        return false;
    }
    if (faces.size() > 1) {            // thấy ≥ 2 mặt → dùng mặt đầu (cảnh báo)
        printf("W: nhieu hon 1 mat, dung mat dau tien\n");
    }

    // 2.3) Ghi nhớ embedding của mặt này vào recognizer (bộ nhớ trong ESP-DL)
    bool ok = (face_recognizer->enroll(img, faces) == ESP_OK);
    heap_caps_free(img.data);
    return ok;
}

// Nhận diện: chụp 1 khung → trả về ID người khớp nhất (hoặc -1)
int face_auth_recognize(camera_fb_t* fb, char* name_out, float* sim_out)
{
    dl::image::jpeg_img_t jpeg_img = {
        .data     = (void*)fb->buf,
        .data_len = (size_t)fb->len,
    };
    auto img = dl::image::sw_decode_jpeg(jpeg_img,
                                         dl::image::DL_IMAGE_PIX_TYPE_RGB888);
    if (img.data == nullptr) return -1;

    // Tìm mặt trước (không có mặt → bỏ, không chạy recognizer)
    auto faces = face_detector->run(img);
    if (faces.size() == 0) {
        heap_caps_free(img.data);
        return -1;
    }

    // So sánh với tất cả mặt đã enroll → trả về kết quả tốt nhất
    auto results = face_recognizer->recognize(img, faces);
    heap_caps_free(img.data);
    if (results.size() == 0) return -1;

    auto best = results.front();          // embedding tương đồng nhất
    if (best.similarity < 0.5f) {         // ngưỡng — giống AUTH_THRESHOLD của giọng
        return -1;                        // dưới ngưỡng: coi như "người lạ"
    }
    *sim_out = best.similarity;
    return best.id;                       // điền tên bằng bảng riêng (bước 3)
}
```

**Giải thích những chỗ dễ ngỡ:**

| Dòng | Ý nghĩa |
|---|---|
| `sw_decode_jpeg(...)` | Camera trả về **JPEG nén**; mạng AI cần ảnh RGB thô. Giải mã "software" (chậm nhưng không cần chip giải mã cứng) |
| `face_detector->run(img)` | Trả **danh sách** khuôn mặt (một khung có thể nhiều người). Mỗi mặt có `score` (độ chắc chắn là mặt) + `box` (toạ độ) + 5 `keypoint` |
| `face_recognizer->enroll(img, faces)` | Ghi **embedding** của mặt vào bộ nhớ recognizer — "não" của ESP-DL tự lưu. So với dự án: ta tách ra lưu ID ↔ tên bằng bảng riêng |
| `recognize(img, faces)` | So embedding ảnh hiện tại với TẤT CẢ embedding đã enroll, trả `best.similarity` (cosine) + `best.id` |
| `best.similarity < 0.5f` | Giống `AUTH_THRESHOLD` của giọng: trên 0.5 là "người quen", dưới là "người lạ" |

### Bước 3 — Bảng tên riêng (kết hợp với recognizer)

Recognizer ESP-DL chỉ trả `id` (số), không nhớ tên. Ta cần bảng:

```cpp
#define MAX_FACES 10
struct FaceInfo {
    int  id;
    char name[32];
    bool active;
};
static FaceInfo face_names[MAX_FACES] = {};
static int next_free_id = 0;

// enroll đầy đủ: ESP-DL ghi embedding + ta ghi tên
bool face_enroll_and_name(camera_fb_t* fb, const char* name)
{
    if (!face_auth_enroll(fb, name)) {
        return false;                 // không thấy mặt
    }
    int id = next_free_id++;
    face_names[id].id = id;
    face_names[id].active = true;
    strncpy(face_names[id].name, name, 31);
    face_names[id].name[31] = '\0';
    return true;
}

// Nhận diện đầy đủ: từ id → tìm tên
int face_full_recognize(camera_fb_t* fb, char* name_out, float* sim_out)
{
    int id = face_auth_recognize(fb, name_out, sim_out);
    if (id >= 0) {
        strcpy(name_out, face_names[id].name);
    }
    return id;
}
```

## 9.3. Đối chiếu đáp án mẫu — `main/face_recognition.cpp`

| Phần bạn viết | Trong dự án (dòng) | Giống / khác |
|---|---|---|
| `new human_face_detect::MSRMNP()` + `new HumanFaceRecognizer()` | 82–85 | Giống |
| Decode JPEG → RGB | 251–262 (enroll), 249–270 (recognize) | Giống |
| `face_detector->run` + lọc theo `s_detect_threshold` | 266–284 | **Dự án thêm ngưỡng detect 0.3** — lọc luôn mặt mờ, chúng ta lược bỏ cho đơn giản |
| `recognize + best.similarity < 0.5` | 286–305 | Giống — ngưỡng được lưu trong NVS cho chỉnh qua web (buổi 10) |
| Bảng tên riêng | `face_database[MAX_FACE_ID_COUNT]`, 87–88 | **Dự án dùng nền SPIFFS `/spiflash/face.db`** — Persistence: tắt điện vẫn nhớ tên — nâng hơn bản của chúng ta (RAM, tắt mất). Buổi 10 sẽ dùng API chỉnh, bạn có khả năng copy code phần SPIFFS dự án |
| Quét ID trống khi enroll | 360–390 | Dự án dùng vòng `for` tìm slot trống; bản của ta dùng `next_free_id++` — "tốn số" khi xóa một mặt giữa danh sách. Bài tập nâng cao: tự sửa lại theo cách quét của dự án |


## 9.4. Ghép với máy trạng thái của buổi 5

Face task chạy song song voice task — kết quả gửi qua event group (`FACE_OK_EVENT`):

```cpp
static void face_task(void* arg)
{
    while (true) {
        camera_fb_t* fb = esp_camera_fb_get();     // chụp 1 khung
        char name[32]; float sim;
        int id = face_full_recognize(fb, name, &sim);

        if (id >= 0) {
            printf("Nhan dien: %s (sim=%.3f)\n", name, sim);
            xEventGroupSetBits(g_auth_events, FACE_OK_EVENT);   // báo cho máy trạng thái
        }
        esp_camera_fb_return(fb);   // TRẢ buffer về camera — quên là camera treo!
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
```

> Cảnh báo cực kỳ hay gặp: **quên `esp_camera_fb_return(fb)`** — không trả buffer về kho của camera, sau vài lần chụp camera từ chối chụp tiếp (`fb_get() = nullptr`). Đây là lỗi "cạn tài nguyên" — đột nhiên hết ảnh, tưởng camera bị hỏng.

## 9.5. Checklist tự kiểm

- [ ] Giải thích được sự khác nhau `detector` (tìm mặt) và `recognizer` (so mặt)
- [ ] Viết được `face_auth_init + enroll + recognize` mà không cần xem đáp án
- [ ] Giải thích được: "embedding" là gì — 1 mảng số đại diện gương mặt, so bằng cosine (như buổi 7)
- [ ] `face_full_recognize` trả cả tên (không chỉ ID)
- [ ] Ghép vào face_task: chụp → nhận diện → set bit event group, **biết trả buffer khung**

**Lỗi hay gặp:**
1. Quên `esp_camera_fb_return(fb)` — camera treo sau vài lần chụp
2. Nhầm `human_face_detect.hpp` (detector) với `human_face_recognition.hpp` (recognizer) — nhớ là 2 file khác nhau
3. Không lọc theo `s_detect_threshold` → mặt mờ bị đưa vào so → sai ID
4. Không giải mã JPEG → recognizer nhận ảnh nén, kết quả ngẫu nhiên — luôn qua `sw_decode_jpeg`
5. Chỉ lưu tên trong RAM — tắt điện mất (dự án lưu vào SPIFFS; xem phần `save_face_metadata` trong `main/face_recognition.cpp` để copy)

