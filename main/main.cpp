#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <algorithm>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "esp_camera.h"
#include "esp_http_server.h"
#include "camera_pins.h"
#include "driver/gpio.h"
#include "face_recognition.h"
#include "audio_capture.h"
#include "voice_auth.h"
#include "esp_heap_caps.h"
#include "esp_task_wdt.h"
#include "servo_control.h"
#include "led_control.h"

#ifndef MIN
#define MIN(a, b) ((a) < (b) ? (a) : (b))
#endif

#ifndef MAX
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#endif

// ============================================================
// STATE MACHINE DEFINITIONS
// ============================================================
typedef enum {
    STATE_STANDBY = 0,          // VoiceID listening, FaceID OFF, LED OFF
    STATE_VOICE_TRIGGERED,      // VoiceID matched, FaceID activated, LED GREEN solid
    STATE_FACE_AUTH,            // Waiting for FaceID result
    STATE_DOOR_OPEN             // FaceID matched, door opening/closing
} system_state_t;

static system_state_t g_system_state = STATE_STANDBY;
static SemaphoreHandle_t g_state_mutex = NULL;

// Event group for signaling between tasks
static EventGroupHandle_t g_auth_events = NULL;
#define VOICE_AUTH_OK_EVENT     (1 << 0)
#define VOICE_AUTH_FAIL_EVENT   (1 << 1)
#define FACE_AUTH_OK_EVENT      (1 << 2)
#define FACE_AUTH_FAIL_EVENT    (1 << 3)

// FaceID enable/disable flag (gated by state machine)
static bool g_face_recognition_active = false;

// ============================================================

static const char *TAG = "camera_http_server";

// WiFi credentials - CHANGE THESE
#define WIFI_SSID "P404"
#define WIFI_PASS "12344321"

#define PART_BOUNDARY "123456789000000000000987654321"
static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* _STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

httpd_handle_t stream_httpd = NULL;
static SemaphoreHandle_t camera_mutex = NULL;
char name[MAX_NAME_LENGTH] = "Unknown";
static SemaphoreHandle_t name_mutex = NULL;
static bool voice_auth_ready = false;

// Binary semaphore to wake up face_recognition_task immediately when activated
static SemaphoreHandle_t g_face_trigger_sem = NULL;

static void free_psram(void *ptr)
{
    if (ptr != nullptr) {
        heap_caps_free(ptr);
    }
}

#define MAX_ENROLL_UPLOAD_BYTES (512 * 1024)

// Forward declarations
void face_recognition_task(void *param);

// HTML page for face enrollment
static const char* index_html = "<!DOCTYPE html>"
"<html>"
"<head>"
"<meta name='viewport' content='width=device-width, initial-scale=1'>"
"<title>Face Recognition Camera</title>"
"<style>"
"body { font-family: Arial; margin: 20px; background: #f0f0f0; }"
".container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }"
"h1 { color: #333; }"
".video-container { position: relative; margin: 20px 0; background: #000; min-height: 400px; display: flex; align-items: center; justify-content: center; }"
"#snapshot { max-width: 100%; border-radius: 5px; }"
".placeholder { color: #666; font-size: 18px; }"
".controls { margin: 20px 0; }"
"input[type='text'] { padding: 10px; width: 200px; font-size: 16px; border: 2px solid #ddd; border-radius: 5px; margin-right: 10px; }"
"button { padding: 10px 20px; margin: 5px; font-size: 16px; cursor: pointer; border: none; border-radius: 5px; }"
".btn-capture { background: #2196F3; color: white; }"
".btn-capture:hover { background: #0b7dda; }"
".btn-enroll { background: #4CAF50; color: white; }"
".btn-enroll:hover { background: #45a049; }"
".btn-enroll:disabled { background: #ccc; cursor: not-allowed; }"
".btn-delete { background: #f44336; color: white; }"
".btn-delete:hover { background: #da190b; }"
".btn-reset { background: #ff9800; color: white; }"
".btn-reset:hover { background: #e68900; }"
".status { padding: 10px; margin: 10px 0; border-radius: 5px; }"
".success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }"
".error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }"
".face-list { margin: 20px 0; }"
".face-item { padding: 10px; background: #f9f9f9; margin: 5px 0; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; }"
"</style>"
"</head>"
"<body>"
"<div class='container'>"
"<h1>Face Recognition Camera</h1>"
"<p><a href='/recognition' target='_blank' style='color: #2196F3; text-decoration: none;'>Open Live Recognition Stream</a></p>"
"<div class='video-container'>"
"<img id='snapshot' style='display:none'>"
"<div id='placeholder' class='placeholder'>Click 'Capture Photo' to take a snapshot</div>"
"</div>"
"<div class='controls'>"
"<button class='btn-capture' onclick='capturePhoto()'>Capture Photo</button>"
"<br><br>"
"<h3>Enroll Face</h3>"
"<input type='text' id='name-input' placeholder='Enter name...'>"
"<button class='btn-enroll' id='enroll-btn' onclick='enrollFace()' disabled>Enroll Face</button>"
"<br><br>"
"<h3>Database Management</h3>"
"<button class='btn-delete' onclick='deleteAllFaces()'>Delete All Faces</button>"
"<button class='btn-reset' onclick='resetDatabase()'>Reset Database</button>"
"</div>"
"<div id='status'></div>"
"<div class='face-list'>"
"<h3>Enrolled Faces: <span id='face-count'>0</span></h3>"
"<div id='face-items'></div>"
"</div>"
"</div>"
"<script>"
"console.log('JavaScript loaded successfully');"
"let currentImageData = null;"
"function showStatus(msg, success) {"
"  const status = document.getElementById('status');"
"  status.className = 'status ' + (success ? 'success' : 'error');"
"  status.textContent = msg;"
"  setTimeout(() => status.textContent = '', 3000);"
"}"
"function capturePhoto() {"
"  console.log('Capturing photo...');"
"  showStatus('Capturing...', true);"
"  fetch('/capture')"
"    .then(r => r.blob())"
"    .then(blob => {"
"      const url = URL.createObjectURL(blob);"
"      const img = document.getElementById('snapshot');"
"      const placeholder = document.getElementById('placeholder');"
"      img.src = url;"
"      img.style.display = 'block';"
"      placeholder.style.display = 'none';"
"      document.getElementById('enroll-btn').disabled = false;"
"      currentImageData = blob;"
"      showStatus('Photo captured! Enter name and click Enroll', true);"
"    })"
"    .catch(e => {"
"      console.error('Capture error:', e);"
"      showStatus('Capture failed: ' + e.message, false);"
"    });"
"}"
"function enrollFace() {"
"  const name = document.getElementById('name-input').value;"
"  if (!name) { showStatus('Please enter a name', false); return; }"
"  if (!currentImageData) { showStatus('Please capture a photo first', false); return; }"
"  console.log('Enrolling:', name);"
"  showStatus('Enrolling...', true);"
"  const formData = new FormData();"
"  formData.append('image', currentImageData, 'snapshot.jpg');"
"  formData.append('name', name);"
"  fetch('/enroll', {"
"    method: 'POST',"
"    body: formData"
"  })"
"    .then(r => {"
"      console.log('Response status:', r.status);"
"      return r.text();"
"    })"
"    .then(text => {"
"      console.log('Response text:', text);"
"      const d = JSON.parse(text);"
"      if (d.success) {"
"        showStatus('Face enrolled: ' + name, true);"
"        document.getElementById('name-input').value = '';"
"        loadFaces();"
"      } else {"
"        showStatus('Enrollment failed: ' + (d.message || 'Unknown error'), false);"
"      }"
"    })"
"    .catch(e => {"
"      console.error('Error:', e);"
"      showStatus('Error: ' + e.message, false);"
"    });"
"}"
"function deleteAllFaces() {"
"  if (!confirm('Delete all enrolled faces?')) return;"
"  fetch('/delete_all')"
"    .then(r => r.json())"
"    .then(d => {"
"      showStatus('All faces deleted', true);"
"      loadFaces();"
"    })"
"    .catch(e => showStatus('Error: ' + e, false));"
"}"
"function resetDatabase() {"
"  if (!confirm('Reset database and metadata? This will remove all face data and fix corruption issues. This action cannot be undone.')) return;"
"  showStatus('Resetting database...', true);"
"  fetch('/reset_database')"
"    .then(r => r.json())"
"    .then(d => {"
"      if (d.success) {"
"        showStatus('Database reset successfully', true);"
"        loadFaces();"
"      } else {"
"        showStatus('Reset failed: ' + (d.message || 'Unknown error'), false);"
"      }"
"    })"
"    .catch(e => showStatus('Error: ' + e.message, false));"
"}"
"function loadFaces() {"
"  fetch('/faces')"
"    .then(r => r.json())"
"    .then(d => {"
"      document.getElementById('face-count').textContent = d.count;"
"      const items = document.getElementById('face-items');"
"      items.innerHTML = '';"
"      d.faces.forEach(f => {"
"        const div = document.createElement('div');"
"        div.className = 'face-item';"
"        div.innerHTML = '<span>' + f.name + ' (ID: ' + f.id + ')</span>';"
"        items.appendChild(div);"
"      });"
"    });"
"}"
"loadFaces();"
"</script>"
"</body>"
"</html>";

// WiFi event handler
static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                                int32_t event_id, void* event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGI(TAG, "Disconnected from AP, retrying...");
        esp_wifi_connect();
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
    }
}

// Initialize WiFi
void wifi_init_sta(void)
{
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);

    esp_event_handler_instance_register(WIFI_EVENT,
                                        ESP_EVENT_ANY_ID,
                                        &wifi_event_handler,
                                        NULL,
                                        NULL);
    esp_event_handler_instance_register(IP_EVENT,
                                        IP_EVENT_STA_GOT_IP,
                                        &wifi_event_handler,
                                        NULL,
                                        NULL);

    wifi_config_t wifi_config = {};
    strcpy((char*)wifi_config.sta.ssid, WIFI_SSID);
    strcpy((char*)wifi_config.sta.password, WIFI_PASS);
    
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
    esp_wifi_start();
}

// Camera initialization
esp_err_t init_camera(void)
{
    camera_config_t config = {
        .pin_pwdn = CAM_PIN_PWDN,
        .pin_reset = CAM_PIN_RESET,
        .pin_xclk = CAM_PIN_XCLK,
        .pin_sccb_sda = CAM_PIN_SIOD,
        .pin_sccb_scl = CAM_PIN_SIOC,

        .pin_d7 = CAM_PIN_D9,
        .pin_d6 = CAM_PIN_D8,
        .pin_d5 = CAM_PIN_D7,
        .pin_d4 = CAM_PIN_D6,
        .pin_d3 = CAM_PIN_D5,
        .pin_d2 = CAM_PIN_D4,
        .pin_d1 = CAM_PIN_D3,
        .pin_d0 = CAM_PIN_D2,
        .pin_vsync = CAM_PIN_VSYNC,
        .pin_href = CAM_PIN_HREF,
        .pin_pclk = CAM_PIN_PCLK,

        .xclk_freq_hz = 20000000,
        .ledc_timer = LEDC_TIMER_0,
        .ledc_channel = LEDC_CHANNEL_0,

        .pixel_format = PIXFORMAT_JPEG,
        .frame_size = FRAMESIZE_VGA,    // 640x480
        .jpeg_quality = 15,
        .fb_count = 2,
        .fb_location = CAMERA_FB_IN_PSRAM,
        .grab_mode = CAMERA_GRAB_LATEST,
    };

    // Initialize camera
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Camera init failed with error 0x%x", err);
        return err;
    }

    // Get sensor to adjust settings
    sensor_t *s = esp_camera_sensor_get();
    if (s != NULL) {
        // Flip image upside down
        s->set_vflip(s, 1);          // Vertical flip
        s->set_hmirror(s, 1);        // Horizontal mirror
        // Adjust settings for better quality
        s->set_brightness(s, 0);     // -2 to 2
        s->set_contrast(s, 0);       // -2 to 2
        s->set_saturation(s, 0);     // -2 to 2
    }

    ESP_LOGI(TAG, "Camera initialized successfully");
    return ESP_OK;
}

// HTTP stream handler
static esp_err_t stream_handler(httpd_req_t *req)
{
    camera_fb_t *fb = NULL;
    esp_err_t res = ESP_OK;
    size_t _jpg_buf_len = 0;
    uint8_t *_jpg_buf = NULL;
    char part_buf[64];

    // Buffer PSRAM reusable trong suot 1 phien stream
    // Cap phat 1 lan (hoac mo rong neu can), giai phong khi session ket thuc
    // Tranh malloc/free moi frame gay phan manh PSRAM
    uint8_t *reuse_buf = NULL;
    size_t reuse_buf_size = 0;

    res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
    if (res != ESP_OK) {
        return res;
    }

    ESP_LOGI(TAG, "Stream started");

    while (true) {
        if (xSemaphoreTake(camera_mutex, pdMS_TO_TICKS(100)) != pdTRUE) {
            vTaskDelay(pdMS_TO_TICKS(50));
            continue;
        }

        fb = esp_camera_fb_get();
        if (!fb) {
            xSemaphoreGive(camera_mutex);
            ESP_LOGE(TAG, "Camera capture failed");
            res = ESP_FAIL;
            break;
        }

        // Copy frame ra reusable buffer (mo rong neu can), roi release camera_mutex NGAY
        _jpg_buf_len = fb->len;
        if (_jpg_buf_len > reuse_buf_size) {
            // Mo rong buffer an toan: cap phat moi truoc, giai phong cu sau
            uint8_t *new_buf = (uint8_t*)heap_caps_malloc(_jpg_buf_len + 256, MALLOC_CAP_SPIRAM);
            if (new_buf) {
                if (reuse_buf) heap_caps_free(reuse_buf);
                reuse_buf = new_buf;
                reuse_buf_size = _jpg_buf_len + 256;
            } else {
                ESP_LOGW(TAG, "Cannot grow stream buffer (%zu > %zu)", _jpg_buf_len, reuse_buf_size);
                // Giu lai buffer cu neu ko the mo rong — skip frame nay
                esp_camera_fb_return(fb);
                xSemaphoreGive(camera_mutex);
                continue;
            }
        }
        _jpg_buf = reuse_buf;
        if (_jpg_buf) {
            memcpy(_jpg_buf, fb->buf, _jpg_buf_len);
        }
        esp_camera_fb_return(fb);
        fb = NULL;
        xSemaphoreGive(camera_mutex);

        // Gui HTTP chi luc da khong giu camera_mutex
        if (res == ESP_OK) {
            size_t hlen = snprintf(part_buf, 64, _STREAM_PART, _jpg_buf_len);
            res = httpd_resp_send_chunk(req, part_buf, hlen);
        }
        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
        }
        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
        }

        if (res != ESP_OK) {
            break;
        }
        vTaskDelay(1);
    }

    ESP_LOGI(TAG, "Stream ended");
    if (reuse_buf) heap_caps_free(reuse_buf);
    return res;
}

// Root handler - serve HTML page
static esp_err_t index_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, index_html, strlen(index_html));
}

// Enroll face handler
static esp_err_t enroll_handler(httpd_req_t *req)
{
    char name[MAX_NAME_LENGTH] = {0};
    uint8_t *image_buf = NULL;
    size_t image_len = 0;
    
    // Add CORS headers
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    
    ESP_LOGI(TAG, "Enroll handler called");
    
    // Check if it's a POST request with multipart data
    if (req->method == HTTP_POST) {
        char buf[512];
        size_t buf_len;
        int remaining = req->content_len;
        
        ESP_LOGI(TAG, "POST request, content length: %d", remaining);

        if (remaining <= 0 || remaining > MAX_ENROLL_UPLOAD_BYTES) {
            httpd_resp_set_type(req, "application/json");
            httpd_resp_sendstr(req, "{\"success\":false,\"message\":\"Upload too large\"}");
            return ESP_OK;
        }
        
        // Allocate buffer for the image
        image_buf = (uint8_t*)heap_caps_malloc((size_t)remaining, MALLOC_CAP_SPIRAM);
        if (!image_buf) {
            ESP_LOGE(TAG, "Failed to allocate image buffer");
            httpd_resp_set_type(req, "application/json");
            httpd_resp_sendstr(req, "{\"success\":false,\"message\":\"Memory allocation failed\"}");
            return ESP_OK;
        }
        
        // Read the entire POST body
        size_t received = 0;
        int recv_timeouts = 0;
        while (remaining > 0) {
            buf_len = MIN(remaining, sizeof(buf));
            int ret = httpd_req_recv(req, buf, buf_len);
            if (ret <= 0) {
                if (ret == HTTPD_SOCK_ERR_TIMEOUT) {
                    if (++recv_timeouts > 20) {
                        free_psram(image_buf);
                        httpd_resp_send_500(req);
                        return ESP_FAIL;
                    }
                    continue;
                }
                free_psram(image_buf);
                httpd_resp_send_500(req);
                return ESP_FAIL;
            }
            recv_timeouts = 0;
            memcpy(image_buf + received, buf, ret);
            received += ret;
            remaining -= ret;
        }
        
        ESP_LOGI(TAG, "Received %d bytes", received);
        
        // Parse multipart form data
        // Format: boundary + image part + boundary + name part + boundary
        // The image comes first (name="image"), then the name field (name="name")
        
        // Find JPEG image data (starts with FF D8 FF)
        uint8_t *jpeg_start = NULL;
        for (size_t i = 0; i < received - 3; i++) {
            if (image_buf[i] == 0xFF && image_buf[i+1] == 0xD8 && image_buf[i+2] == 0xFF) {
                jpeg_start = &image_buf[i];
                ESP_LOGI(TAG, "Found JPEG start at offset %d", i);
                break;
            }
        }
        
        if (!jpeg_start) {
            ESP_LOGE(TAG, "Failed to find JPEG start marker");
            free_psram(image_buf);
            httpd_resp_set_type(req, "application/json");
            httpd_resp_sendstr(req, "{\"success\":false,\"message\":\"No JPEG data found\"}");
            return ESP_OK;
        }
        
        // Find JPEG end (FF D9) - search from JPEG start position
        uint8_t *jpeg_end = NULL;
        size_t start_offset = jpeg_start - image_buf;
        for (size_t i = start_offset; i < received - 1; i++) {
            if (image_buf[i] == 0xFF && image_buf[i+1] == 0xD9) {
                jpeg_end = &image_buf[i + 2];  // Include the end marker
                ESP_LOGI(TAG, "Found JPEG end at offset %d", i + 2);
                break;
            }
        }
        
        if (!jpeg_end) {
            ESP_LOGE(TAG, "Failed to find JPEG end marker");
            free_psram(image_buf);
            httpd_resp_set_type(req, "application/json");
            httpd_resp_sendstr(req, "{\"success\":false,\"message\":\"Invalid JPEG data\"}");
            return ESP_OK;
        }
        
        image_len = jpeg_end - jpeg_start;
        ESP_LOGI(TAG, "JPEG size: %d bytes", image_len);
        
        // Now search for the name field AFTER the JPEG data
        // Look for the boundary after the JPEG
        char *name_field = NULL;
        
        // First, try to find "name=\"name\"" pattern
        for (size_t i = (jpeg_end - image_buf); i < received - 20; i++) {
            if (strncmp((char*)&image_buf[i], "name=\"name\"", 11) == 0) {
                name_field = (char*)&image_buf[i];
                ESP_LOGI(TAG, "Found name field at offset %d", i);
                break;
            }
        }
        
        if (name_field) {
            // Find the content after the headers (after \r\n\r\n)
            char *name_start = strstr(name_field, "\r\n\r\n");
            if (name_start) {
                name_start += 4;  // Skip the \r\n\r\n
                // Find the end (either \r\n or --)
                char *name_end = strstr(name_start, "\r\n");
                if (!name_end) {
                    name_end = strstr(name_start, "--");
                }
                if (name_end) {
                    size_t name_len = MIN(name_end - name_start, MAX_NAME_LENGTH - 1);
                    memcpy(name, name_start, name_len);
                    name[name_len] = '\0';
                    ESP_LOGI(TAG, "Extracted name: '%s' (length: %d)", name, name_len);
                } else {
                    ESP_LOGW(TAG, "Could not find name end");
                }
            } else {
                ESP_LOGW(TAG, "Could not find name content start");
            }
        } else {
            ESP_LOGW(TAG, "Could not find name field in multipart data");
            
            // Debug: print the data after JPEG to see what's there
            ESP_LOGI(TAG, "Data after JPEG (100 bytes):");
            size_t debug_start = (jpeg_end - image_buf);
            size_t debug_len = MIN(100, received - debug_start);
            ESP_LOG_BUFFER_HEXDUMP(TAG, jpeg_end, debug_len, ESP_LOG_INFO);
        }
        
        if (strlen(name) == 0) {
            ESP_LOGE(TAG, "Name not extracted");
            free_psram(image_buf);
            httpd_resp_set_type(req, "application/json");
            httpd_resp_sendstr(req, "{\"success\":false,\"message\":\"Name not found in form data\"}");
            return ESP_OK;
        }
        ESP_LOGI(TAG, "Found JPEG: %d bytes, enrolling as: %s", image_len, name);
        
        // Create a fake camera frame buffer from the uploaded image
        camera_fb_t fb;
        fb.buf = jpeg_start;
        fb.len = image_len;
        fb.width = 640;  // Assuming VGA
        fb.height = 480;
        fb.format = PIXFORMAT_JPEG;
        
        // Enroll the face (keep image_buf alive during enrollment)
        int id = face_recognition_enroll(&fb, name);
        
        free_psram(image_buf);
        
        char json[128];
        if (id >= 0) {
            snprintf(json, sizeof(json), "{\"success\":true,\"id\":%d,\"name\":\"%s\"}", id, name);
            ESP_LOGI(TAG, "Enrollment successful, ID: %d", id);
        } else {
            snprintf(json, sizeof(json), "{\"success\":false,\"message\":\"Face detection failed\"}");
            ESP_LOGE(TAG, "Enrollment failed");
        }
        
        httpd_resp_set_type(req, "application/json");
        return httpd_resp_sendstr(req, json);
    }
    
    // Fallback: GET request (old behavior for compatibility)
    char query[128];
    if (httpd_req_get_url_query_str(req, query, sizeof(query)) == ESP_OK) {
        ESP_LOGI(TAG, "Query string: %s", query);
        if (httpd_query_key_value(query, "name", name, sizeof(name)) == ESP_OK) {
            ESP_LOGI(TAG, "Enrolling face with name: %s", name);
            
            if (xSemaphoreTake(camera_mutex, pdMS_TO_TICKS(2000)) != pdTRUE) {
                ESP_LOGE(TAG, "Camera busy, timeout");
                httpd_resp_set_type(req, "application/json");
                httpd_resp_sendstr(req, "{\"success\":false,\"message\":\"Camera busy\"}");
                return ESP_OK;
            }
            
            camera_fb_t *fb = esp_camera_fb_get();
            if (!fb) {
                xSemaphoreGive(camera_mutex);
                ESP_LOGE(TAG, "Camera capture failed");
                httpd_resp_set_type(req, "application/json");
                httpd_resp_sendstr(req, "{\"success\":false,\"message\":\"Camera capture failed\"}");
                return ESP_OK;
            }
            
            ESP_LOGI(TAG, "Frame captured, size: %d bytes", fb->len);
            
            int id = face_recognition_enroll(fb, name);
            esp_camera_fb_return(fb);
            xSemaphoreGive(camera_mutex);
            
            char json[128];
            if (id >= 0) {
                ESP_LOGI(TAG, "Enrollment successful, ID: %d", id);
                snprintf(json, sizeof(json), "{\"success\":true,\"id\":%d,\"name\":\"%s\"}", id, name);
            } else {
                ESP_LOGE(TAG, "Enrollment failed");
                snprintf(json, sizeof(json), "{\"success\":false,\"message\":\"No face detected or enrollment failed\"}");
            }
            
            httpd_resp_set_type(req, "application/json");
            return httpd_resp_sendstr(req, json);
        } else {
            ESP_LOGE(TAG, "Failed to parse name parameter");
        }
    } else {
        ESP_LOGE(TAG, "No query string found");
    }
    
    httpd_resp_set_type(req, "application/json");
    return httpd_resp_sendstr(req, "{\"success\":false,\"message\":\"Missing name parameter\"}");
}

// List enrolled faces handler
static esp_err_t faces_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG, "Faces handler called");
    
    char json[2048];
    int count = face_recognition_get_enrolled_count();
    int off = snprintf(json, sizeof(json), "{\"count\":%d,\"faces\":[", count);
    bool first = true;
    
    ESP_LOGI(TAG, "Enrolled count: %d", count);
    
    for (int i = 0; i < MAX_FACE_ID_COUNT; i++) {
        face_id_t info;
        if (face_recognition_get_info(i, &info) != ESP_OK || !info.enrolled) {
            continue;
        }
        int n = snprintf(json + off, sizeof(json) - off,
                         "%s{\"id\":%d,\"name\":\"%.31s\"}",
                         first ? "" : ",", info.id, info.name);
        if (n < 0 || (size_t)n >= sizeof(json) - off) {
            break;
        }
        off += n;
        first = false;
    }
    snprintf(json + off, sizeof(json) - off, "]}");
    
    httpd_resp_set_type(req, "application/json");
    return httpd_resp_sendstr(req, json);
}

// Delete all faces handler
static esp_err_t delete_all_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG, "Delete all handler called");
    
    esp_err_t err = face_recognition_delete_all();
    
    httpd_resp_set_type(req, "application/json");
    if (err == ESP_OK) {
        return httpd_resp_sendstr(req, "{\"success\":true}");
    } else {
        return httpd_resp_sendstr(req, "{\"success\":false}");
    }
}

// Reset database handler - removes database and metadata files
static esp_err_t reset_database_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG, "Reset database handler called");
    
    esp_err_t err = face_recognition_reset_database();
    
    httpd_resp_set_type(req, "application/json");
    if (err == ESP_OK) {
        return httpd_resp_sendstr(req, "{\"success\":true,\"message\":\"Database reset successfully\"}");
    } else {
        return httpd_resp_sendstr(req, "{\"success\":false,\"message\":\"Failed to reset database\"}");
    }
}
// Ping test handler
static esp_err_t ping_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG, "Ping handler called");
    httpd_resp_set_type(req, "application/json");
    return httpd_resp_sendstr(req, "{\"status\":\"ok\",\"message\":\"pong\"}");
}

// Capture single image handler
static esp_err_t capture_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG, "Capture handler called");
    
    camera_fb_t *fb = NULL;
    esp_err_t res = ESP_OK;
    
    if (xSemaphoreTake(camera_mutex, pdMS_TO_TICKS(2000)) != pdTRUE) {
        ESP_LOGE(TAG, "Camera busy");
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }
    
    fb = esp_camera_fb_get();
    if (!fb) {
        xSemaphoreGive(camera_mutex);
        ESP_LOGE(TAG, "Camera capture failed");
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }
    
    ESP_LOGI(TAG, "Captured image, size: %d bytes", fb->len);
    
    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
    
    res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    xSemaphoreGive(camera_mutex);
    
    return res;
}

// HTML page for recognition view with overlay
static const char* recognition_html = "<!DOCTYPE html>"
"<html>"
"<head>"
"<meta name='viewport' content='width=device-width, initial-scale=1'>"
"<title>Live Face Recognition</title>"
"<style>"
"body { margin: 0; padding: 0; background: #000; font-family: Arial; }"
".container { position: relative; width: 100vw; height: 100vh; display: flex; align-items: center; justify-content: center; overflow: hidden; }"
"#canvas { max-width: 100%; max-height: 100%; }"
".overlay { position: absolute; bottom: 20px; left: 20px; background: rgba(0,0,0,0.8); color: white; padding: 15px 25px; border-radius: 10px; font-size: 28px; font-weight: bold; min-width: 200px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }"
".name { color: #4CAF50; }"
".unknown { color: #ff9800; }"
"</style>"
"</head>"
"<body>"
"<div class='container'>"
"<canvas id='canvas'></canvas>"
"<div class='overlay' id='overlay'>"
"<span id='name' class='unknown'>Scanning...</span>"
"</div>"
"</div>"
"<script>"
"const canvas = document.getElementById('canvas');"
"const ctx = canvas.getContext('2d');"
"const nameEl = document.getElementById('name');"
"const streamUrl = '/recognition_stream';"
"let img = new Image();"
"let currentName = 'Scanning...';"
"async function fetchStream() {"
"  try {"
"    const response = await fetch(streamUrl);"
"    const reader = response.body.getReader();"
"    let buffer = new Uint8Array(0);"
"    const boundary = new TextEncoder().encode('--123456789000000000000987654321');"
"    while (true) {"
"      const {done, value} = await reader.read();"
"      if (done) break;"
"      const temp = new Uint8Array(buffer.length + value.length);"
"      temp.set(buffer);"
"      temp.set(value, buffer.length);"
"      buffer = temp;"
"      let searchStart = 0;"
"      while (true) {"
"        const boundaryPos = findBoundary(buffer, boundary, searchStart);"
"        if (boundaryPos === -1) break;"
"        const nextBoundaryPos = findBoundary(buffer, boundary, boundaryPos + boundary.length);"
"        if (nextBoundaryPos === -1) break;"
"        const chunk = buffer.slice(boundaryPos, nextBoundaryPos);"
"        processChunk(chunk);"
"        buffer = buffer.slice(nextBoundaryPos);"
"        searchStart = 0;"
"      }"
"    }"
"  } catch (e) {"
"    console.error('Stream error:', e);"
"    setTimeout(fetchStream, 1000);"
"  }"
"}"
"function findBoundary(buffer, boundary, start) {"
"  for (let i = start; i <= buffer.length - boundary.length; i++) {"
"    let match = true;"
"    for (let j = 0; j < boundary.length; j++) {"
"      if (buffer[i + j] !== boundary[j]) {"
"        match = false;"
"        break;"
"      }"
"    }"
"    if (match) return i;"
"  }"
"  return -1;"
"}"
"function processChunk(chunk) {"
"  const text = new TextDecoder().decode(chunk);"
"  const headerEnd = text.indexOf('\\r\\n\\r\\n');"
"  if (headerEnd === -1) return;"
"  const headers = text.substring(0, headerEnd);"
"  const nameMatch = headers.match(/X-Face-Name: ([^\\r\\n]+)/);"
"  if (nameMatch) {"
"    const name = nameMatch[1].trim();"
"    if (name !== currentName) {"
"      currentName = name;"
"      if (name !== 'Unknown' && name !== '') {"
"        nameEl.textContent = name;"
"        nameEl.className = 'name';"
"      } else {"
"        nameEl.textContent = 'No face detected';"
"        nameEl.className = 'unknown';"
"      }"
"    }"
"  }"
"  const jpegStart = headerEnd + 4;"
"  const jpegData = chunk.slice(jpegStart);"
"  const blob = new Blob([jpegData], {type: 'image/jpeg'});"
"  const url = URL.createObjectURL(blob);"
"  img.onload = () => {"
"    canvas.width = img.width;"
"    canvas.height = img.height;"
"    ctx.drawImage(img, 0, 0);"
"    URL.revokeObjectURL(url);"
"  };"
"  img.src = url;"
"}"
"fetchStream();"
"</script>"
"</body>"
"</html>";

// Recognition page handler - serves HTML with overlay
static esp_err_t recognition_page_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_send(req, recognition_html, strlen(recognition_html));
}

// Recognition stream handler - stream with face detection
static esp_err_t recognition_stream_handler(httpd_req_t *req)
{
    camera_fb_t *fb = NULL;
    esp_err_t res = ESP_OK;
    size_t _jpg_buf_len = 0;
    uint8_t *_jpg_buf = NULL;
    char part_buf[128];
    char current_name[MAX_NAME_LENGTH];

    // Buffer PSRAM reusable trong suot phien stream, tranh phan manh heap
    uint8_t *reuse_buf = NULL;
    size_t reuse_buf_size = 0;

    res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
    if (res != ESP_OK) {
        return res;
    }

    ESP_LOGI(TAG, "Recognition stream started");

    while (true) {
        if (xSemaphoreTake(camera_mutex, pdMS_TO_TICKS(100)) != pdTRUE) {
            vTaskDelay(pdMS_TO_TICKS(50));
            continue;
        }

        fb = esp_camera_fb_get();
        if (!fb) {
            xSemaphoreGive(camera_mutex);
            ESP_LOGE(TAG, "Camera capture failed");
            res = ESP_FAIL;
            break;
        }

        // Doc ten nguoi duoc nhan dien (name_mutex doc lap voi camera_mutex)
        if (xSemaphoreTake(name_mutex, pdMS_TO_TICKS(10)) == pdTRUE) {
            strncpy(current_name, name, MAX_NAME_LENGTH - 1);
            current_name[MAX_NAME_LENGTH - 1] = '\0';
            xSemaphoreGive(name_mutex);
        } else {
            strcpy(current_name, "Unknown");
        }

        // Copy frame ra reusable buffer (mo rong neu can), release camera_mutex NGAY
        _jpg_buf_len = fb->len;
        if (_jpg_buf_len > reuse_buf_size) {
            // Mo rong buffer an toan: cap phat moi truoc, giai phong cu sau
            uint8_t *new_buf = (uint8_t*)heap_caps_malloc(_jpg_buf_len + 256, MALLOC_CAP_SPIRAM);
            if (new_buf) {
                if (reuse_buf) heap_caps_free(reuse_buf);
                reuse_buf = new_buf;
                reuse_buf_size = _jpg_buf_len + 256;
            } else {
                ESP_LOGW(TAG, "Cannot grow recognition stream buffer (%zu > %zu)", _jpg_buf_len, reuse_buf_size);
                // Giu lai buffer cu neu ko the mo rong — skip frame nay
                esp_camera_fb_return(fb);
                xSemaphoreGive(camera_mutex);
                continue;
            }
        }
        _jpg_buf = reuse_buf;
        if (_jpg_buf) {
            memcpy(_jpg_buf, fb->buf, _jpg_buf_len);
        }
        esp_camera_fb_return(fb);
        fb = NULL;
        xSemaphoreGive(camera_mutex);

        // Gui HTTP chi khi da khong giu camera_mutex
        if (res == ESP_OK) {
            size_t hlen = snprintf(part_buf, sizeof(part_buf), 
                "Content-Type: image/jpeg\r\n"
                "Content-Length: %u\r\n"
                "X-Face-Name: %s\r\n\r\n", 
                _jpg_buf_len, current_name);
            res = httpd_resp_send_chunk(req, part_buf, hlen);
        }
        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
        }
        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
        }

        if (res != ESP_OK) {
            break;
        }
        vTaskDelay(1);
    }

    ESP_LOGI(TAG, "Recognition stream ended");
    if (reuse_buf) heap_caps_free(reuse_buf);
    return res;
}

static esp_err_t recognized_name_handler(httpd_req_t *req)
{
    char current_name[MAX_NAME_LENGTH];
    
    // Get current name with mutex protection
    if (xSemaphoreTake(name_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        strcpy(current_name, name);
        xSemaphoreGive(name_mutex);
    } else {
        strcpy(current_name, "Unknown");
    }
    
    httpd_resp_set_type(req, "application/json");
    char json[128];
    snprintf(json, sizeof(json), "{\"name\":\"%s\"}", current_name);
    return httpd_resp_sendstr(req, json);
}

// Start HTTP server
void start_camera_server(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 80;
    config.ctrl_port = 32768;
    config.max_uri_handlers = 16;

    httpd_uri_t index_uri = {
        .uri = "/",
        .method = HTTP_GET,
        .handler = index_handler,
        .user_ctx = NULL
    };

    httpd_uri_t stream_uri = {
        .uri = "/stream",
        .method = HTTP_GET,
        .handler = stream_handler,
        .user_ctx = NULL
    };

    httpd_uri_t enroll_uri_get = {
        .uri = "/enroll",
        .method = HTTP_GET,
        .handler = enroll_handler,
        .user_ctx = NULL
    };
    
    httpd_uri_t enroll_uri_post = {
        .uri = "/enroll",
        .method = HTTP_POST,
        .handler = enroll_handler,
        .user_ctx = NULL
    };

    httpd_uri_t faces_uri = {
        .uri = "/faces",
        .method = HTTP_GET,
        .handler = faces_handler,
        .user_ctx = NULL
    };

    httpd_uri_t delete_all_uri = {
        .uri = "/delete_all",
        .method = HTTP_GET,
        .handler = delete_all_handler,
        .user_ctx = NULL
    };

    httpd_uri_t reset_database_uri = {
        .uri = "/reset_database",
        .method = HTTP_GET,
        .handler = reset_database_handler,
        .user_ctx = NULL
    };

    httpd_uri_t ping_uri = {
        .uri = "/ping",
        .method = HTTP_GET,
        .handler = ping_handler,
        .user_ctx = NULL
    };

    httpd_uri_t capture_uri = {
        .uri = "/capture",
        .method = HTTP_GET,
        .handler = capture_handler,
        .user_ctx = NULL
    };

    httpd_uri_t recognition_stream_uri = {
        .uri = "/recognition",
        .method = HTTP_GET,
        .handler = recognition_page_handler,
        .user_ctx = NULL
    };

    httpd_uri_t recognized_name_uri = {
        .uri = "/recognized_name",
        .method = HTTP_GET,
        .handler = recognized_name_handler,
        .user_ctx = NULL
    };
    
    httpd_uri_t recognition_stream_data_uri = {
        .uri = "/recognition_stream",
        .method = HTTP_GET,
        .handler = recognition_stream_handler,
        .user_ctx = NULL
    };

    ESP_LOGI(TAG, "Starting web server on port: '%d'", config.server_port);
    if (httpd_start(&stream_httpd, &config) == ESP_OK) {
        ESP_LOGI(TAG, "Registering URI handlers...");
        httpd_register_uri_handler(stream_httpd, &index_uri);
        ESP_LOGI(TAG, "Registered: /");
        httpd_register_uri_handler(stream_httpd, &stream_uri);
        ESP_LOGI(TAG, "Registered: /stream");
        httpd_register_uri_handler(stream_httpd, &enroll_uri_get);
        httpd_register_uri_handler(stream_httpd, &enroll_uri_post);
        ESP_LOGI(TAG, "Registered: /enroll (GET and POST)");
        httpd_register_uri_handler(stream_httpd, &faces_uri);
        ESP_LOGI(TAG, "Registered: /faces");
        httpd_register_uri_handler(stream_httpd, &delete_all_uri);
        ESP_LOGI(TAG, "Registered: /delete_all");
        httpd_register_uri_handler(stream_httpd, &reset_database_uri);
        ESP_LOGI(TAG, "Registered: /reset_database");
        httpd_register_uri_handler(stream_httpd, &ping_uri);
        ESP_LOGI(TAG, "Registered: /ping");
        httpd_register_uri_handler(stream_httpd, &capture_uri);
        ESP_LOGI(TAG, "Registered: /capture");
        httpd_register_uri_handler(stream_httpd, &recognized_name_uri);
        ESP_LOGI(TAG, "Registered: /recognized_name");
        
        esp_err_t rec_reg = httpd_register_uri_handler(stream_httpd, &recognition_stream_uri);
        ESP_LOGI(TAG, "Registered: /recognition (result: %d)", rec_reg);
        
        esp_err_t rec_stream_reg = httpd_register_uri_handler(stream_httpd, &recognition_stream_data_uri);
        ESP_LOGI(TAG, "Registered: /recognition_stream (result: %d)", rec_stream_reg);
        esp_netif_ip_info_t ip_info;
        esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
        if (netif != NULL && esp_netif_get_ip_info(netif, &ip_info) == ESP_OK) {
            ESP_LOGI(TAG, "Web interface started at http://" IPSTR, IP2STR(&ip_info.ip));
        } else {
            ESP_LOGI(TAG, "Web interface started at http://[YOUR_IP]");
        }
    } else {
        ESP_LOGE(TAG, "Failed to start stream server");
    }
}


// Background task to continuously perform face recognition
// Only runs when g_face_recognition_active is true (gated by state machine)
void face_recognition_task(void *param)
{
    ESP_LOGI(TAG, "Face recognition background task started");
    char local_name[MAX_NAME_LENGTH];
    
    while (true) {
        // Check if face recognition is currently active (STATE_VOICE_TRIGGERED or STATE_FACE_AUTH)
        bool should_run = false;
        if (xSemaphoreTake(g_state_mutex, pdMS_TO_TICKS(10)) == pdTRUE) {
            should_run = g_face_recognition_active;
            xSemaphoreGive(g_state_mutex);
        }

        if (!should_run) {
            // In STANDBY: don't do face recognition, block on semaphore
            // Wait indefinitely until the state machine signals activation
            if (g_face_trigger_sem != NULL) {
                xSemaphoreTake(g_face_trigger_sem, portMAX_DELAY);
            } else {
                vTaskDelay(pdMS_TO_TICKS(500));
            }
            continue;
        }

        // Face recognition is active — capture and process a frame
        if (xSemaphoreTake(camera_mutex, pdMS_TO_TICKS(100)) != pdTRUE) {
            vTaskDelay(pdMS_TO_TICKS(50));
            continue;
        }
        
        camera_fb_t *fb = esp_camera_fb_get();
        if (!fb) {
            xSemaphoreGive(camera_mutex);
            continue;
        }

        int result = face_recognition_recognize(fb, local_name, NULL);
        esp_camera_fb_return(fb);
        xSemaphoreGive(camera_mutex);

        if (result >= 0) {
            ESP_LOGI(TAG, "Face recognized: %s", local_name);
            if (xSemaphoreTake(name_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
                strcpy(name, local_name);
                xSemaphoreGive(name_mutex);
            }
            // Signal state machine: FaceID OK
            if (g_auth_events != NULL) {
                xEventGroupSetBits(g_auth_events, FACE_AUTH_OK_EVENT);
            }
        } else {
            // No face or unknown face in this frame — just continue
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }   
}

// State machine controller: runs as a task to manage transitions
static void state_machine_task(void* arg)
{
    (void)arg;
    ESP_LOGI(TAG, "State machine task started");

    EventBits_t bits;
    const TickType_t FACE_AUTH_TIMEOUT = pdMS_TO_TICKS(10000); // 10s timeout for FaceID
    const TickType_t DOOR_OPEN_DURATION = pdMS_TO_TICKS(5000);  // Door stays open for 5s

    while (true) {
        // Wait for events from voice auth or face auth tasks
        bits = xEventGroupWaitBits(
            g_auth_events,
            VOICE_AUTH_OK_EVENT | VOICE_AUTH_FAIL_EVENT |
            FACE_AUTH_OK_EVENT | FACE_AUTH_FAIL_EVENT,
            pdTRUE,  // Clear bits on exit
            pdFALSE, // Wait for any bit
            portMAX_DELAY
        );

        if (bits & VOICE_AUTH_OK_EVENT) {
            ESP_LOGI(TAG, "[STATE] VoiceID OK → VOICE_TRIGGERED, activating FaceID");
            
            // LED: solid GREEN
            led_set_color(0, 255, 0);

            // Enable face recognition
            if (xSemaphoreTake(g_state_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
                g_system_state = STATE_VOICE_TRIGGERED;
                g_face_recognition_active = true;
                xSemaphoreGive(g_state_mutex);
            }
            // Wake up the face_recognition_task immediately (was blocked on semaphore)
            if (g_face_trigger_sem != NULL) {
                xSemaphoreGive(g_face_trigger_sem);
            }

            // Wait for FaceID result with timeout
            bits = xEventGroupWaitBits(
                g_auth_events,
                FACE_AUTH_OK_EVENT | FACE_AUTH_FAIL_EVENT,
                pdTRUE, pdFALSE,
                FACE_AUTH_TIMEOUT
            );

            // Disable face recognition immediately (save power)
            if (xSemaphoreTake(g_state_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
                g_face_recognition_active = false;
                g_system_state = STATE_FACE_AUTH;
                xSemaphoreGive(g_state_mutex);
            }

            if (bits & FACE_AUTH_OK_EVENT) {
                ESP_LOGI(TAG, "[STATE] FaceID OK → DOOR_OPEN");

                // LED: blink GREEN 3 times
                led_blink_green_success();

                // Open the door
                if (xSemaphoreTake(g_state_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
                    g_system_state = STATE_DOOR_OPEN;
                    xSemaphoreGive(g_state_mutex);
                }
                servo_open_door();

                // Wait for door open duration
                vTaskDelay(DOOR_OPEN_DURATION);

                // Close the door
                servo_close_door();
                vTaskDelay(pdMS_TO_TICKS(500)); // Allow servo to settle

                ESP_LOGI(TAG, "[STATE] Door closed → STANDBY");
            } else {
                // FaceID timeout or failure
                ESP_LOGW(TAG, "[STATE] FaceID timeout/fail → STANDBY");
            }

            // Return to STANDBY
            led_off();
            if (xSemaphoreTake(g_state_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
                g_system_state = STATE_STANDBY;
                xSemaphoreGive(g_state_mutex);
            }

        } else if (bits & VOICE_AUTH_FAIL_EVENT) {
            ESP_LOGW(TAG, "[STATE] VoiceID FAIL → blink RED, return to STANDBY");

            // LED: blink RED 3 times
            led_blink_red_fail();

            // Ensure back to STANDBY (LED stays off)
            led_off();

        // Note: FACE_AUTH_OK_EVENT and FACE_AUTH_FAIL_EVENT are handled
        // within the VOICE_AUTH_OK branch above (inside the nested xEventGroupWaitBits).
        // They should not fire here because all event bits are cleared on exit.
    }
}
}

static void voice_auth_task(void* arg) {
    // Cap phat bo nho thu am vao PSRAM thay vi RAM noi (giai phong 32KB)
    int16_t *audio_buf = (int16_t *)heap_caps_malloc(TOTAL_SAMPLES * sizeof(int16_t), MALLOC_CAP_SPIRAM);
    if (audio_buf == NULL) {
        ESP_LOGE("MAIN", "Khong du PSRAM de cap phat bo nho thu am!");
        vTaskDelete(NULL);
        return;
    }

    // Dang ky task voi WDT de co the reset WDT dinh ky
    if (esp_task_wdt_add(NULL) != ESP_OK) {
        ESP_LOGW("MAIN", "Failed to add voice_auth_task to Task WDT");
    }

    while (true) {
        esp_task_wdt_reset();

        // Only listen for voice in STANDBY state (or if state machine is idle)
        // This ensures we don't re-trigger while already processing
        system_state_t current_state;
        if (xSemaphoreTake(g_state_mutex, pdMS_TO_TICKS(10)) == pdTRUE) {
            current_state = g_system_state;
            xSemaphoreGive(g_state_mutex);
        } else {
            current_state = STATE_STANDBY;
        }

        if (current_state != STATE_STANDBY) {
            // If we're in the middle of face auth or door open, skip recording
            vTaskDelay(pdMS_TO_TICKS(200));
            continue;
        }

        if (!audio_capture_record(audio_buf, TOTAL_SAMPLES)) {
            vTaskDelay(pdMS_TO_TICKS(1000));
            continue;
        }

        float score = 0.0f;
        if (voice_auth_verify(audio_buf, TOTAL_SAMPLES, &score)) {
            ESP_LOGI("VOICE", "============> VOICE MATCHED! Score=%.2f", score);

            // Signal state machine: Voice OK
            if (g_auth_events != NULL) {
                xEventGroupSetBits(g_auth_events, VOICE_AUTH_OK_EVENT);
            }

            // Wait a short period before next recording (avoid re-trigger)
            // The state machine handles the rest, so just wait
            vTaskDelay(pdMS_TO_TICKS(1000));
        } else {
            if (score >= 0.0f) {
                ESP_LOGW("VOICE", "Voice NOT matched! Score=%.2f", score);

                // Signal state machine: Voice FAIL (blink RED)
                if (g_auth_events != NULL) {
                    xEventGroupSetBits(g_auth_events, VOICE_AUTH_FAIL_EVENT);
                }
            }
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }
}
// --------------------------------------
extern "C" void app_main(void)
{   
    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // Create camera mutex
    camera_mutex = xSemaphoreCreateMutex();
    if (camera_mutex == NULL) {
        ESP_LOGE(TAG, "Failed to create camera mutex");
        return;
    }

    // Create name mutex
    name_mutex = xSemaphoreCreateMutex();
    if (name_mutex == NULL) {
        ESP_LOGE(TAG, "Failed to create name mutex");
        return;
    }

    // Create state machine mutex
    g_state_mutex = xSemaphoreCreateMutex();
    if (g_state_mutex == NULL) {
        ESP_LOGE(TAG, "Failed to create state mutex");
        return;
    }

    // Create event group for auth signaling
    g_auth_events = xEventGroupCreate();
    if (g_auth_events == NULL) {
        ESP_LOGE(TAG, "Failed to create event group");
        return;
    }

    // Create binary semaphore for face recognition wakeup
    g_face_trigger_sem = xSemaphoreCreateBinary();
    if (g_face_trigger_sem == NULL) {
        ESP_LOGE(TAG, "Failed to create face trigger semaphore");
        return;
    }

    // --- NO UART/STM32: removed completely ---
    // Servo and LED are now controlled directly by ESP32-S3

    ESP_LOGI(TAG, "Initializing WiFi...");
    wifi_init_sta();

    ESP_LOGI(TAG, "Waiting for WiFi connection...");
    esp_netif_ip_info_t ip_info = {};
    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    int retry = 0;
    while ((netif == NULL || esp_netif_get_ip_info(netif, &ip_info) != ESP_OK || ip_info.ip.addr == 0) && retry < 40) {
        vTaskDelay(pdMS_TO_TICKS(500));
        retry++;
        netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    }

    ESP_LOGI(TAG, "Initializing camera...");
    if (init_camera() != ESP_OK) {
        ESP_LOGE(TAG, "Camera init failed");
        return;
    }

    ESP_LOGI(TAG, "Initializing face recognition...");
    face_recognition_init();

    ESP_LOGI(TAG, "Initializing WS2812 LED...");
    led_init();

    ESP_LOGI(TAG, "Initializing Servo (GPIO %d)...", SERVO_PIN);
    servo_init();
    // Ensure servo
    servo_close_door(); // Start with door closed

    // Start the background tasks
    xTaskCreate(face_recognition_task, "face_rec_task", 8192, NULL, 5, NULL);
    xTaskCreate(state_machine_task, "state_machine", 4096, NULL, 6, NULL);
    
    // Start voice auth task only if audio is ready
    if (audio_capture_init() && voice_auth_init()) {
        voice_auth_ready = true;
        xTaskCreate(voice_auth_task, "voice_auth_task", 10240, NULL, 5, NULL);
    }

    start_camera_server();
}