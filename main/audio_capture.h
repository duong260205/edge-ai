#pragma once
#include <stdint.h>
#include <stddef.h>

#define SAMPLE_RATE     16000
#define FRAME_SIZE      512
#define RECORD_SECONDS  1
#define TOTAL_SAMPLES   (SAMPLE_RATE * RECORD_SECONDS)

// I2S pins - chỉnh theo board của bạn
#define I2S_BCLK_PIN    40
#define I2S_WS_PIN      41
#define I2S_DATA_PIN    42

bool audio_capture_init();
bool audio_capture_record(int16_t* buffer, size_t num_samples);
