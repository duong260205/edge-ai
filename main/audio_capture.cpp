#include "audio_capture.h"
#include "driver/i2s_std.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <algorithm>
static const char* TAG = "AUDIO";
static i2s_chan_handle_t rx_handle = nullptr;

bool audio_capture_init() {
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(
        I2S_NUM_AUTO, I2S_ROLE_MASTER
    );
    esp_err_t ret = i2s_new_channel(&chan_cfg, nullptr, &rx_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2S channel create failed: %s", esp_err_to_name(ret));
        rx_handle = nullptr;
        return false;
    }

    i2s_std_config_t std_cfg = {
        .clk_cfg  = I2S_STD_CLK_DEFAULT_CONFIG(SAMPLE_RATE),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(
                        I2S_DATA_BIT_WIDTH_32BIT,
                        I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = (gpio_num_t)I2S_BCLK_PIN,
            .ws   = (gpio_num_t)I2S_WS_PIN,
            .dout = I2S_GPIO_UNUSED,
            .din  = (gpio_num_t)I2S_DATA_PIN,
            .invert_flags = { .mclk_inv=false, .bclk_inv=false, .ws_inv=false }
        }
    };

    ret = i2s_channel_init_std_mode(rx_handle, &std_cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2S init failed: %s", esp_err_to_name(ret));
        i2s_del_channel(rx_handle);
        rx_handle = nullptr;
        return false;
    }
    i2s_channel_enable(rx_handle);
    ESP_LOGI(TAG, "I2S microphone initialized");
    return true;
}

bool audio_capture_record(int16_t* buffer, size_t num_samples) {
    if (rx_handle == nullptr) {
        return false;
    }

    size_t samples_read = 0;
    const size_t CHUNK_SAMPLES = 256;
    int32_t chunk_buf[CHUNK_SAMPLES];

    while (samples_read < num_samples) {
        size_t to_read = std::min(CHUNK_SAMPLES, num_samples - samples_read);
        size_t bytes_read = 0;
        esp_err_t ret = i2s_channel_read(
            rx_handle, chunk_buf, to_read * sizeof(int32_t), &bytes_read, pdMS_TO_TICKS(1000)
        );

        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "I2S read error: %s", esp_err_to_name(ret));
            return false;
        }

        size_t valid_samples = bytes_read / sizeof(int32_t);
        for (size_t i = 0; i < valid_samples; i++) {
            // INMP441 trả về dữ liệu 24-bit left-justified trong 32-bit slot.
            // Dịch phải 14 bit để lấy 16-bit MSB và khuếch đại (gain x4)
            int32_t sample = chunk_buf[i] >> 14; 
            
            // Chống tràn số học (clipping) để không bị nổ tiếng
            if (sample > 32767) sample = 32767;
            else if (sample < -32768) sample = -32768;
            
            buffer[samples_read++] = (int16_t)sample;
        }
    }
    return true;
}
