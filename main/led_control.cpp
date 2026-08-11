#include "led_control.h"
#include "esp_log.h"
#include "led_strip.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "LED";

static led_strip_handle_t led_strip = NULL;

esp_err_t led_init(void)
{
    /* LED strip initialization with the GPIO and pixels number */
    led_strip_config_t strip_config = {};
    strip_config.strip_gpio_num = LED_WS2812_PIN;
    strip_config.max_leds = 1;
    strip_config.led_model = LED_MODEL_WS2812;
    strip_config.color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_RGB;
    strip_config.flags.invert_out = false;

    /* RMT backend configuration */
    led_strip_rmt_config_t rmt_config = {};
    rmt_config.clk_src = RMT_CLK_SRC_DEFAULT;
    rmt_config.resolution_hz = 10 * 1000 * 1000; // 10MHz
    rmt_config.flags.with_dma = false;

    esp_err_t err = led_strip_new_rmt_device(&strip_config, &rmt_config, &led_strip);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "Failed to initialize WS2812 LED on GPIO %d: %s (may conflict with JTAG)",
                 LED_WS2812_PIN, esp_err_to_name(err));
        ESP_LOGW(TAG, "LED will be disabled. This is normal if using JTAG debugging.");
        led_strip = NULL;
        return err;
    }

    ESP_LOGI(TAG, "WS2812 LED initialized on GPIO %d", LED_WS2812_PIN);
    return ESP_OK;
}

void led_set_color(uint8_t r, uint8_t g, uint8_t b)
{
    if (led_strip == NULL) {
        return;
    }

    esp_err_t err = led_strip_set_pixel(led_strip, 0, r, g, b);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to set LED pixel: %s", esp_err_to_name(err));
        return;
    }

    err = led_strip_refresh(led_strip);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to refresh LED: %s", esp_err_to_name(err));
    }
}

void led_off(void)
{
    led_set_color(0, 0, 0);
}

void led_blink(uint8_t r, uint8_t g, uint8_t b, int times, int delay_ms)
{
    for (int i = 0; i < times; i++) {
        led_set_color(r, g, b);
        vTaskDelay(pdMS_TO_TICKS(delay_ms));
        led_off();
        if (i < times - 1) {
            vTaskDelay(pdMS_TO_TICKS(delay_ms));
        }
    }
}

void led_blink_red_fail(void)
{
    led_blink(255, 0, 0, 3, 200);
}

void led_blink_green_success(void)
{
    led_blink(0, 255, 0, 3, 150);
}
