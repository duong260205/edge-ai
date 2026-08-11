#ifndef LED_CONTROL_H
#define LED_CONTROL_H

#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

// WS2812 LED GPIO pin (on ESP32-S3-DevKitC v1.0 this is typically GPIO 48)
#define LED_WS2812_PIN      48

/**
 * @brief Initialize the WS2812 RGB LED using the RMT led_strip driver
 */
esp_err_t led_init(void);

/**
 * @brief Set RGB LED color (each channel 0-255)
 */
void led_set_color(uint8_t r, uint8_t g, uint8_t b);

/**
 * @brief Set LED to OFF (all channels 0)
 */
void led_off(void);

/**
 * @brief Blink LED a number of times with given color and delay
 * 
 * @param r         Red component
 * @param g         Green component
 * @param b         Blue component
 * @param times     Number of blinks
 * @param delay_ms  On/off delay in milliseconds
 */
void led_blink(uint8_t r, uint8_t g, uint8_t b, int times, int delay_ms);

/**
 * @brief Shortcut: blink RED 3 times (for VoiceID failure)
 */
void led_blink_red_fail(void);

/**
 * @brief Shortcut: blink GREEN 3 times (for FaceID success)
 */
void led_blink_green_success(void);

#ifdef __cplusplus
}
#endif

#endif // LED_CONTROL_H
