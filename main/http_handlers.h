#ifndef HTTP_HANDLERS_H
#define HTTP_HANDLERS_H

#include <stdint.h>
#include <stdbool.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_http_server.h"
#include "face_recognition.h"

#ifdef __cplusplus
extern "C" {
#endif

// System initialization status tracking
typedef struct {
    bool wifi_connected;
    bool camera_ok;
    bool face_recognition_ok;
    bool neopixel_ok;
    bool web_spiffs_mounted;
    bool server_started;
    bool audio_ready;
    bool voice_auth_ready;
    char ip_address[16];
} system_status_t;

// Shared variables (defined in main.cpp)
extern char name[MAX_NAME_LENGTH];
extern httpd_handle_t stream_httpd;
extern system_status_t sys_status;
extern SemaphoreHandle_t camera_mutex;
extern SemaphoreHandle_t name_mutex;

// Start the HTTP server (defined in http_handlers.cpp)
void start_camera_server(void);

// Register voice authentication HTTP handlers onto an existing server
void register_voice_httpd_handlers(httpd_handle_t server);

#ifdef __cplusplus
}
#endif

#endif // HTTP_HANDLERS_H
