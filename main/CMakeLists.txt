idf_component_register(
    SRCS 
        "main.cpp" 
        "face_recognition.cpp"
        "audio_capture.cpp" 
        "voice_auth.cpp"
        "model_data.cc"
    INCLUDE_DIRS "."
    REQUIRES 
        esp_psram 
        esp_wifi 
        esp_event 
        nvs_flash 
        esp_http_server 
        esp_http_client 
        esp32-camera 
        led_strip 
        driver 
        esp_timer 
        spiffs 
        esp-tls 
        mbedtls 
        esp-tflite-micro   # Thêm cho nhận diện giọng nói TFLite
        esp-dsp            # Thêm thư viện DSP để tính toán MFCC/FFT
)

# Disable format warnings for ESP-DL compatibility
target_compile_options(${COMPONENT_LIB} PRIVATE -Wno-format)