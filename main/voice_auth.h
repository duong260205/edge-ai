#pragma once
#include <stdbool.h>
#include <cstdint>
#include <stddef.h>

#define EMBEDDING_SIZE  128   // phụ thuộc model bạn dùng
#define AUTH_THRESHOLD  0.7f
#define VOICE_ENROLL_SAMPLE_COUNT 5
#define VOICE_PROFILE_NAME_MAX 32

bool voice_auth_init();
void voice_auth_deinit();

// Enroll: lưu embedding của người dùng vào NVS
bool voice_auth_enroll(const char* user_id, const int16_t* audio, int num_samples);
bool voice_auth_enroll_multi(const char* user_id, const int16_t* audio_samples, int sample_count, int samples_per_recording);

// Verify: so sánh với embedding đã lưu
bool voice_auth_verify(const int16_t* audio, int num_samples, float* score_out);
bool voice_auth_verify_multi(const int16_t* audio_samples, int sample_count,
                             int samples_per_recording, float* score_out);

// The current firmware stores one calibrated speaker profile in NVS.
bool voice_auth_has_profile();
bool voice_auth_get_profile_name(char* name, size_t name_size);
bool voice_auth_delete_profile(const char* user_id);
