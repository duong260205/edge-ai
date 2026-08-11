#ifndef SERVO_CONTROL_H
#define SERVO_CONTROL_H

#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

// Servo GPIO pin
#define SERVO_PIN              47
#define SERVO_PWM_FREQ_HZ      50      // Standard servo frequency (50Hz = 20ms period)
#define SERVO_PWM_RESOLUTION   LEDC_TIMER_13_BIT  // 13-bit = 8192 steps

// Pulse width in microseconds for common servo angles
#define SERVO_PULSE_MIN_US     500     // 0°   (typically 500-600 µs)
#define SERVO_PULSE_MAX_US     2500    // 180° (typically 2400-2500 µs)
#define SERVO_PULSE_MID_US     1500    // 90°

// LEDC channel/timer assignments
// NOTE: Timer 0 & Channel 0 are reserved by the camera XCLK signal (see camera init)
#define SERVO_LEDC_TIMER       LEDC_TIMER_1
#define SERVO_LEDC_CHANNEL     LEDC_CHANNEL_1

/**
 * @brief Initialize the servo motor on SERVO_PIN using LEDC PWM
 * 
 * Configures LEDC timer and channel at 50Hz with 13-bit resolution.
 */
esp_err_t servo_init(void);

/**
 * @brief Set servo to a specific angle (0° ~ 180°)
 * 
 * Maps angle(0-180) to pulse width(500-2500 µs) 
 * and sets the LEDC duty cycle accordingly.
 * 
 * @param angle  Target angle in degrees (clamped 0~180)
 */
void servo_set_angle(int angle);

/**
 * @brief Open door: sweep servo to OPEN angle (e.g. 90°)
 */
void servo_open_door(void);

/**
 * @brief Close door: sweep servo back to CLOSED angle (e.g. 0°)
 */
void servo_close_door(void);

/**
 * @brief Deinitialize servo (optional, can keep GPIO low)
 */
void servo_deinit(void);

#ifdef __cplusplus
}
#endif

#endif // SERVO_CONTROL_H
