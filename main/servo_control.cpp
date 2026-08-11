#include "servo_control.h"
#include "esp_log.h"
#include "driver/ledc.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "SERVO";

// Door positions
#define SERVO_ANGLE_CLOSED      0
#define SERVO_ANGLE_OPEN        90

esp_err_t servo_init(void)
{
    ESP_LOGI(TAG, "Initializing servo on GPIO %d", SERVO_PIN);

    // Configure LEDC timer
    ledc_timer_config_t ledc_timer = {
        .speed_mode       = LEDC_LOW_SPEED_MODE,
        .duty_resolution  = SERVO_PWM_RESOLUTION,
        .timer_num        = SERVO_LEDC_TIMER,
        .freq_hz          = SERVO_PWM_FREQ_HZ,
        .clk_cfg          = LEDC_AUTO_CLK
    };
    esp_err_t ret = ledc_timer_config(&ledc_timer);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "LEDC timer config failed: %s", esp_err_to_name(ret));
        return ret;
    }

    // Configure LEDC channel
    ledc_channel_config_t ledc_channel = {
        .gpio_num       = SERVO_PIN,
        .speed_mode     = LEDC_LOW_SPEED_MODE,
        .channel        = SERVO_LEDC_CHANNEL,
        .intr_type      = LEDC_INTR_DISABLE,
        .timer_sel      = SERVO_LEDC_TIMER,
        .duty           = 0,  // Start at 0 (closed)
        .hpoint         = 0
    };
    ret = ledc_channel_config(&ledc_channel);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "LEDC channel config failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ESP_LOGI(TAG, "Servo initialized successfully");
    return ESP_OK;
}

/**
 * @brief Convert angle (0-180) to LEDC duty value
 * 
 * PWM period = 1/50Hz = 20,000 µs
 * With 13-bit resolution (8192 steps):
 *   Duty = (pulse_us / 20000.0) * 8191
 */
static uint32_t angle_to_duty(int angle)
{
    // Clamp angle to 0-180
    if (angle < 0)   angle = 0;
    if (angle > 180) angle = 180;

    // Linear interpolation of pulse width
    uint32_t pulse_us = SERVO_PULSE_MIN_US + 
                        (uint32_t)((float)(SERVO_PULSE_MAX_US - SERVO_PULSE_MIN_US) * angle / 180.0f);

    // Convert pulse width to LEDC duty (13-bit)
    uint32_t duty = (uint32_t)((float)pulse_us / 20000.0f * 8191.0f);
    return duty;
}

void servo_set_angle(int angle)
{
    uint32_t duty = angle_to_duty(angle);
    esp_err_t ret = ledc_set_duty(LEDC_LOW_SPEED_MODE, SERVO_LEDC_CHANNEL, duty);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to set duty: %s", esp_err_to_name(ret));
        return;
    }
    ret = ledc_update_duty(LEDC_LOW_SPEED_MODE, SERVO_LEDC_CHANNEL);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to update duty: %s", esp_err_to_name(ret));
        return;
    }
    ESP_LOGD(TAG, "Servo angle=%d°, duty=%lu", angle, (unsigned long)duty);
}

void servo_open_door(void)
{
    ESP_LOGI(TAG, "Opening door (servo → %d°)", SERVO_ANGLE_OPEN);
    servo_set_angle(SERVO_ANGLE_OPEN);
}

void servo_close_door(void)
{
    ESP_LOGI(TAG, "Closing door (servo → %d°)", SERVO_ANGLE_CLOSED);
    servo_set_angle(SERVO_ANGLE_CLOSED);
}

void servo_deinit(void)
{
    ledc_stop(LEDC_LOW_SPEED_MODE, SERVO_LEDC_CHANNEL, 0);
    ESP_LOGI(TAG, "Servo deinitialized");
}
