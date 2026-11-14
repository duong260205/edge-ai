# Buổi 10 — Tự code Web server: stream camera + REST API quản trị

## 10.0. Mục tiêu buổi học

Buổi 9 chip nhận ra mặt nhưng để **enroll/đổi ngưỡng/xóa mặt phải cắm cable** — không tiện. Buổi 10 bạn tự code web server chạy ngay trên chip:
- Trang web HTML (lưu trong firmware) với nút "Enroll", "Xóa tất cả"
- **Video stream** từ camera trực tiếp trên trình duyệt (MJPEG)
- **REST API JSON** để app bên ngoài gọi (vd: `/api/status`, `/api/enroll`)

Thư viện — `esp_http_server` có sẵn của ESP-IDF không cần cài thêm.

## 10.1. Khởi động server — 3 dòng cốt lõi

```cpp
#include "esp_http_server.h"

static httpd_handle_t server = nullptr;

bool web_server_start()
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.max_uri_handlers = 16;        // dự án dùng 11 — tăng lên để dư chỗ

    if (httpd_start(&server, &config) != ESP_OK) {
        ESP_LOGE(TAG, "httpd_start failed");
        return false;
    }

    // Đăng ký từng "URL → hàm xử lý" (xem mục 10.3)
    httpd_uri_t stream_uri = {
        .uri      = "/stream",
        .method   = HTTP_GET,
        .handler  = stream_handler,
        .user_ctx = nullptr,
    };
    httpd_register_uri_handler(server, &stream_uri);
    return true;
}
```

**Hình dung `httpd_uri_t`:** là 1 dòng bảng ghi "khi trình duyệt gõ `/stream` → gọi hàm `stream_handler`". Bạn đăng ký bao nhiêu URL thì web đợi bấy nhiêu. Siêu dễ.

## 10.2. Stream video MJPEG — camera đưa hình cho trình duyệt xem trực tiếp

Nguyên lý: trình duyệt nhận 1 luồng HTTP **không kết thúc**, mỗi khung ảnh JPEG được gói trong một phần riêng (mỗi phần có "Content-Length" + JPEG bytes). Định dạng chung gọi là **multipart/x-mixed-replace**:

```cpp
static const char* TAG = "web";

typedef struct {
    const char* part;            // "--dddd\r\nContent-Type: image/jpeg\r\n..."
    size_t len;
} jpg_frame_out_t;

static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=123456789000000000000987654321";
static const char* _STREAM_BOUNDARY     = "\r\n--123456789000000000000987654321\r\n";

esp_err_t stream_handler(httpd_req_t* req)
{
    httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);   // báo cả luồng là multipart

    while (true) {
        camera_fb_t* fb = esp_camera_fb_get();         // chụp 1 khung
        if (fb == nullptr) {
            ESP_LOGE(TAG, "fb_get null");
            break;
        }

        // Gửi header của phần + dữ liệu JPEG + ranh giới
        char part_buf[64];
        size_t hlen = snprintf(part_buf, sizeof(part_buf),
            "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", fb->len);

        if (httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY)) != ESP_OK ||
            httpd_resp_send_chunk(req, part_buf, hlen) != ESP_OK ||
            httpd_resp_send_chunk(req, (const char*)fb->buf, fb->len) != ESP_OK) {
            // Trình duyệt đã đóng (người dùng đổi tab) → thoát vòng lặp
            esp_camera_fb_return(fb);
            break;
        }

        esp_camera_fb_return(fb);   // trả buffer — như buổi 9 đã nhấn
    }
    return ESP_OK;
}
```

**Hình dung **"multipart/x-mixed-replace"**: mỗi chunk = 1 gói tin tự mô tả "đây là ảnh JPEG có chiều dài N" → trình duyệt **thay hình cài trên trang** không cần tải lại. Đây là cách camera IP phổ thông đưa hình lên web — video không cần websocket hay video server ngoài.

> **Vì sao dùng MJPEG mà không dùng H.264?** H.264 phải nén/phát video riêng; MJPEG chỉ cần gửi ảnh JPEG liên tục — nhẹ, đơn giản, trễ ~200 ms. WiFi đủ cho ~10 fps (640×480 ~ 100 KB/khung).

## 10.3. REST API — bảng URL hàm xử lý

Dự án đăng ký 11 URL. Bảng đầy đủ để **tự viết từng handler**:

| URL | Method | Làm gì | Handler dự án (main.cpp dòng) |
|---|---|---|---|
| `/` | GET | Trang HTML cài sẵn | `index_handler` (503) |
| `/stream` | GET | MJPEG stream | `stream_handler` (419) |
| `/enroll` | GET + POST | Đăng ký mặt từ ảnh (POST: có file JPEG trong body) | `enroll_handler` (510) |
| `/faces` | GET | Danh sách mặt đã đăng ký (JSON) | trong main.cpp |
| `/delete_all` | POST | Xóa tất cả mặt | — |
| `/capture` | GET | Chụp 1 ảnh gửi về trình duyệt | — |
| `/ping` | GET | Trả `{"status":"ok"}` kiểm tra server còn sống | — |
| `/recognized_name` | GET | Tên người vừa nhận diện gần nhất (JSON) | — |
| `/recognition_stream` | GET | Stream kèm khung có vẽ khung mặt xanh đỏ | — |

Ví dụ 1 handler JSON đơn giản tự viết — `/ping`:

```cpp
esp_err_t ping_handler(httpd_req_t* req)
{
    httpd_resp_set_type(req, "application/json");
    return httpd_resp_sendstr(req, "{\"status\":\"ok\"}");
}
```

Ví dụ 1 handler đọc dữ liệu POST — `/enroll`:

```cpp
esp_err_t enroll_handler(httpd_req_t* req)
{
    // 1) Đọc tất cả body từ POST (JPEG + tên người trong multipart form)
    int total_len = req->content_len;
    if (total_len > 200000) {           // hơn 200 KB → từ chối
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Body too large");
        return ESP_FAIL;
    }

    char* buf = (char*)heap_caps_malloc(total_len + 1, MALLOC_CAP_SPIRAM);
    int received = 0;
    while (received < total_len) {
        int ret = httpd_req_recv(req, buf + received, total_len - received);
        if (ret <= 0) { heap_caps_free(buf); httpd_resp_send_500(req); return ESP_FAIL; }
        received += ret;
    }
    buf[received] = '\0';

    // 2) Tìm JPEG trong body (bắt đầu "FF D8 FF") — camera chụp bám ngay sau đó
    //    Tìm tên trong form (name=...)
    //    ... (xem dự án main.cpp 540–680 cho xử lý chi tiết)

    // 3) Gọi face_auth_enroll với ảnh + tên — dùng hàm của buổi 9
    // 4) Trả JSON kết quả
    httpd_resp_set_type(req, "application/json");
    httpd_resp_sendstr(req, "{\"success\":true,\"message\":\"Enrolled\"}");
    heap_caps_free(buf);
    return ESP_OK;
}
```

> Phần **phân tích body POST từng phần** (multipart boundary) được lược để dạy cho gọn — dự án làm đầy đủ; khi cần áp dụng thực tế hãy đọc `main/main.cpp` dòng 510–720.


## 10.4. Trang HTML nhúng — web chạy ngay trong firmware

Mảng `index_html` (chuỗi rất dài, trong `main.cpp` dòng 150–250) chứa cả trang điều khiển. Cách nhúng: dùng khai báo chuỗi C thô (raw string literal) để gồm cả dấu nháy:

```cpp
static const char index_html[] =
R"rawliteral(
<!DOCTYPE html>
<html>
<head><title>Khoa cua AI</title></head>
<body>
  <h1>Khoa cua ai - Ban dieu khien</h1>
  <img src="/stream">                    <!-- Video MJPEG stream -->
  <button onclick="enroll()">Enroll</button>
  <button onclick="fetch('/delete_all', {method:'POST'})
                 .then(r => r.json()).then(d => alert(d.message))">Xoa tat ca</button>
  <script>
    async function enroll() {
      const res = await fetch('/enroll');
      const data = await res.json();
      alert(data.message);
    }
  </script>
</body>
</html>
)rawliteral";

static esp_err_t index_handler(httpd_req_t* req)
{
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, index_html, strlen(index_html));
}
```

**Bí quyết `R"rawliteral(...)rawliteral"`:** chuỗi thô của C++ cho phép chứa cả dấu nháy `"` và ký tự xuống dòng — một chuỗi HTML nằm nguyên văn trong code, không cần escape.

Phần CSS và bố cục trang là công sức riêng (đọc `main.cpp` dòng 150–250 để thấy bản đầy đủ) — **không cần làm đẹp ngay**; mục tiêu buổi 10 là web server trên chip chạy được.

## 10.5. Ghép server với máy trạng thái

Web chạy trong task riêng. Máy trạng thái của buổi 5 có thêm `STATE_MAINTENANCE`: chế độ web quản trị — khóa cửa tạm ngừng nhận diện để cho phép enroll mặt/giọng mới.

```
                          (người gọi POST /enroll)
Trình duyệt  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
                                          ▼
[ web server task ] ── handler → face_recognition_enroll()
        │
        ▼
 (phục vụ trang / stream MJPEG)
```

Máy trạng thái **không** trực tiếp "phát lệnh enroll" — nó chỉ đọc event group. Đây là nguyên tắc "mỗi khối một việc" (single responsibility): web làm quản trị, state machine làm điều khiển cửa, không chồng chéo.


### Bảo vệ API bằng PIN admin (như dự án)

Mọi hàm cài đặt nhạy cảm (enroll, delete, đổi ngưỡng) phải kiểm tra `X-Admin-Pin` trong header — dự án có sẵn hàm `check_admin_pin` (main.cpp dòng 91):

```cpp
static bool check_admin_pin(httpd_req_t* req)
{
    static const char* ADMIN_PIN = "1234";    // đặt trong menuconfig thực tế
    char pin[16] = {0};
    size_t len;
    if (httpd_req_get_hdr_value_len(req, "X-Admin-Pin", &len) == ESP_OK && len < sizeof(pin)) {
        httpd_req_get_hdr_value_str(req, "X-Admin-Pin", pin, sizeof(pin));
        return strcmp(pin, ADMIN_PIN) == 0;
    }
    return false;
}

// trong enroll_handler:
if (!check_admin_pin(req)) {
    httpd_resp_set_status(req, "403 Forbidden");
    httpd_resp_set_type(req, "application/json");
    return httpd_resp_sendstr(req,
        "{\"success\":false,\"message\":\"Thiếu PIN admin\"}");
}
```

> Vì sao phải bảo vệ? Ai trong mạng WiFi nhà bạn cũng có thể gọi `POST /delete_all` chỉ bằng trình duyệt — PIN là "rào chắn" đầu tiên, chưa cần HTTPS. Buổi 11 có mục mở rộng: token/session nâng cao.

## 10.6. Checklist tự kiểm

- [ ] `web_server_start()` khởi động được, trình duyệt gõ IP chip mở trang `/`
- [ ] `/stream` hiện hình ảnh MJPEG trong trình duyệt
- [ ] `/ping` trả JSON `{"status":"ok"}` — dùng `curl http://192.168.x.x/ping` thử
- [ ] Gọi `POST /enroll` với ảnh → trả `success:true` và mặt được ghi nhớ
- [ ] **Nếu quên `esp_camera_fb_return`** trong stream_handler — camera treo sau ~10 giây stream (lỗi kinh điển, đã nhấn ở 9.4)
- [ ] Biết giải thích: `multipart/x-mixed-replace` là gì (mục 10.2)

**Lỗi hay gặp:**
1. `max_uri_handlers` quá nhỏ — đăng ký quá 8 URL mà không tăng → 404 "unknown" cho URL mới
2. **Gửi JSON không set `application/json`** — trình duyệt hiện text thô, fetch().json() reject
3. **Header multipart không chạy** — boundary trong Content-Type và trong `_STREAM_BOUNDARY` phải GIỐNG chính xác chuỗi
4. **Quên kiểm PIN/403** → mọi thiết bị trong mạng gọi API tự do

