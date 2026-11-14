#include "voice_auth.h"
#include "esp_log.h"
#include "esp_dsp.h"
#include "esp_heap_caps.h"
#include "nvs.h"
#include <algorithm>
#include <cstring>
#include <math.h>

#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "model_data.h"

static const char* TAG = "VOICE_AUTH";

namespace {
    const tflite::Model* model = nullptr;
    tflite::MicroInterpreter* interpreter = nullptr;
    TfLiteTensor* input = nullptr;
    TfLiteTensor* output = nullptr;

    constexpr int kTensorArenaSize = 40 * 1024;
    constexpr int kFftSize = 512;
    constexpr int kFftBufFloats = 1024;
    constexpr int kFeatureCount = 32 * 13;
    constexpr uint32_t kProfileMagic = 0x564F4950;

    struct voice_profile_t {
        uint32_t magic;
        char name[VOICE_PROFILE_NAME_MAX];
        float features[kFeatureCount];
    };

    uint8_t* tensor_arena = nullptr;
    float* fft_work_buf = nullptr;
    float* hann_window = nullptr;
    voice_profile_t profile = {};
    bool profile_loaded = false;

    void free_voice_work_buffers()
    {
        if (tensor_arena != nullptr) {
            heap_caps_free(tensor_arena);
            tensor_arena = nullptr;
        }
        if (fft_work_buf != nullptr) {
            heap_caps_free(fft_work_buf);
            fft_work_buf = nullptr;
        }
        if (hann_window != nullptr) {
            heap_caps_free(hann_window);
            hann_window = nullptr;
        }
    }
}

static bool load_profile()
{
    nvs_handle_t handle;
    if (nvs_open("voice_auth", NVS_READONLY, &handle) != ESP_OK) {
        return false;
    }
    size_t size = sizeof(profile);
    esp_err_t result = nvs_get_blob(handle, "profile", &profile, &size);
    nvs_close(handle);
    profile_loaded = result == ESP_OK && size == sizeof(profile) &&
                     profile.magic == kProfileMagic && profile.name[0] != '\0';
    return profile_loaded;
}

static bool save_profile(const char* user_id, const float* features)
{
    voice_profile_t next = {};
    next.magic = kProfileMagic;
    strncpy(next.name, user_id, sizeof(next.name) - 1);
    memcpy(next.features, features, sizeof(next.features));

    nvs_handle_t handle;
    if (nvs_open("voice_auth", NVS_READWRITE, &handle) != ESP_OK) {
        return false;
    }
    esp_err_t result = nvs_set_blob(handle, "profile", &next, sizeof(next));
    if (result == ESP_OK) {
        result = nvs_commit(handle);
    }
    nvs_close(handle);
    if (result == ESP_OK) {
        profile = next;
        profile_loaded = true;
    }
    return result == ESP_OK;
}

static bool compute_features(const int16_t* audio, int num_samples, float* features)
{
    if (audio == nullptr || features == nullptr || num_samples <= 0 ||
        fft_work_buf == nullptr || hann_window == nullptr) {
        return false;
    }

    int max_val = 0;
    for (int i = 0; i < num_samples; ++i) {
        max_val = std::max(max_val, abs((int)audio[i]));
    }
    if (max_val < 100) {
        return false;
    }

    for (int i = 0; i < 32; i++) {
        memset(fft_work_buf, 0, kFftBufFloats * sizeof(float));
        int start_idx = i * 512;

        for (int j = 0; j < kFftSize && (start_idx + j) < num_samples; j++) {
            float sample_norm = (max_val > 0) ? ((float)audio[start_idx + j] / (float)max_val) : 0.0f;
            fft_work_buf[j * 2] = sample_norm * hann_window[j];
            fft_work_buf[j * 2 + 1] = 0.0f;
        }

        dsps_fft2r_fc32(fft_work_buf, kFftSize);
        dsps_bit_rev_fc32(fft_work_buf, kFftSize);

        for (int b = 0; b < 13; b++) {
            float energy = 0.0f;
            int bin_start = b * (256 / 13);
            int bin_end = (b + 1) * (256 / 13);
            for (int bin = bin_start; bin < bin_end; bin++) {
                float re = fft_work_buf[bin * 2];
                float im = fft_work_buf[bin * 2 + 1];
                energy += (re * re + im * im);
            }

            float energy_norm = energy / (512.0f * 512.0f);
            features[i * 13 + b] = logf(energy_norm + 1e-6f);
        }
    }
    return true;
}

static void compute_mfcc_like_features(const float* features, TfLiteTensor* input_tensor)
{
    float scale = input_tensor->params.scale;
    int zero_point = input_tensor->params.zero_point;
    if (scale == 0.0f) scale = 0.1f;
    for (int i = 0; i < kFeatureCount; ++i) {
        input_tensor->data.int8[i] = (int8_t)std::max(
            -128.0f, std::min(127.0f, roundf(features[i] / scale) + zero_point));
    }
}

bool voice_auth_init()
{
    ESP_LOGI(TAG, "Loading voice model from flash (embedded C array, %d bytes)",
             g_voice_auth_model_data_len);

    dsps_fft2r_init_fc32(NULL, CONFIG_DSP_MAX_FFT_SIZE);

    if (tensor_arena == nullptr) {
        tensor_arena = (uint8_t*)heap_caps_malloc(kTensorArenaSize, MALLOC_CAP_SPIRAM);
        if (tensor_arena == nullptr) {
            ESP_LOGE(TAG, "PSRAM alloc failed for TFLite tensor arena (%d bytes)", kTensorArenaSize);
            free_voice_work_buffers();
            return false;
        }
    }

    if (fft_work_buf == nullptr) {
        fft_work_buf = (float*)heap_caps_malloc(kFftBufFloats * sizeof(float), MALLOC_CAP_SPIRAM);
        if (fft_work_buf == nullptr) {
            ESP_LOGE(TAG, "PSRAM alloc failed for FFT work buffer");
            free_voice_work_buffers();
            return false;
        }
    }

    if (hann_window == nullptr) {
        hann_window = (float*)heap_caps_malloc(kFftSize * sizeof(float), MALLOC_CAP_SPIRAM);
        if (hann_window == nullptr) {
            ESP_LOGE(TAG, "PSRAM alloc failed for Hann window");
            free_voice_work_buffers();
            return false;
        }
        dsps_wind_hann_f32(hann_window, kFftSize);
    }

    model = tflite::GetModel(g_voice_auth_model_data);
    if (model == nullptr) {
        ESP_LOGE(TAG, "GetModel() returned null");
        free_voice_work_buffers();
        return false;
    }

    if (model->version() != TFLITE_SCHEMA_VERSION) {
        ESP_LOGE(TAG, "Model schema %ld != supported %d",
                 (long)model->version(), TFLITE_SCHEMA_VERSION);
        model = nullptr;
        free_voice_work_buffers();
        return false;
    }

    static tflite::MicroMutableOpResolver<8> resolver;
    resolver.AddConv2D();
    resolver.AddMaxPool2D();
    resolver.AddReshape();
    resolver.AddFullyConnected();
    resolver.AddLogistic();
    resolver.AddShape();
    resolver.AddStridedSlice();
    resolver.AddPack();

    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena, kTensorArenaSize);
    interpreter = &static_interpreter;

    if (interpreter->AllocateTensors() != kTfLiteOk) {
        ESP_LOGE(TAG, "AllocateTensors() failed");
        interpreter = nullptr;
        input = nullptr;
        output = nullptr;
        model = nullptr;
        free_voice_work_buffers();
        return false;
    }

    input = interpreter->input(0);
    output = interpreter->output(0);
    load_profile();
    ESP_LOGI(TAG, "TFLite Micro ready (arena=%d KB in PSRAM)", kTensorArenaSize / 1024);
    return true;
}

void voice_auth_deinit()
{
    interpreter = nullptr;
    input = nullptr;
    output = nullptr;
    model = nullptr;
    free_voice_work_buffers();
}

bool voice_auth_enroll(const char* user_id, const int16_t* audio, int num_samples)
{
    return voice_auth_enroll_multi(user_id, audio, 1, num_samples);
}

bool voice_auth_enroll_multi(const char* user_id, const int16_t* audio_samples,
                             int sample_count, int samples_per_recording)
{
    if (!user_id || !audio_samples || sample_count <= 0 || samples_per_recording <= 0 ||
        strlen(user_id) >= VOICE_PROFILE_NAME_MAX) {
        return false;
    }
    float average[kFeatureCount] = {};
    int valid_samples = 0;
    for (int sample = 0; sample < sample_count; ++sample) {
        float features[kFeatureCount];
        if (!compute_features(audio_samples + sample * samples_per_recording,
                              samples_per_recording, features)) {
            continue;
        }
        for (int i = 0; i < kFeatureCount; ++i) {
            average[i] += features[i];
        }
        ++valid_samples;
    }
    if (valid_samples == 0) {
        return false;
    }
    for (float& value : average) {
        value /= valid_samples;
    }
    return save_profile(user_id, average);
}

bool voice_auth_verify(const int16_t* audio, int num_samples, float* score_out)
{
    if (!interpreter || !input || !output || !fft_work_buf || !hann_window) {
        return false;
    }

    float energy = 0.0f;
    for (int i = 0; i < num_samples; i++) {
        energy += ((float)audio[i] * (float)audio[i]);
    }
    float rms = sqrtf(energy / num_samples);
    float features[kFeatureCount];
    if (rms < 30.0f || !compute_features(audio, num_samples, features)) {
        *score_out = -1.0f;
        return false;
    }

    compute_mfcc_like_features(features, input);

    if (interpreter->Invoke() != kTfLiteOk) {
        ESP_LOGE(TAG, "Invoke failed");
        return false;
    }

    float prediction = (output->data.int8[0] - output->params.zero_point) * output->params.scale;
    float similarity = prediction;
    if (profile_loaded) {
        float dot = 0.0f;
        float norm_a = 0.0f;
        float norm_b = 0.0f;
        float mean_a = 0.0f;
        float mean_b = 0.0f;
        for (int i = 0; i < kFeatureCount; ++i) {
            mean_a += features[i];
            mean_b += profile.features[i];
        }
        mean_a /= kFeatureCount;
        mean_b /= kFeatureCount;
        for (int i = 0; i < kFeatureCount; ++i) {
            float a = features[i] - mean_a;
            float b = profile.features[i] - mean_b;
            dot += a * b;
            norm_a += a * a;
            norm_b += b * b;
        }
        float cosine = (norm_a > 0.0f && norm_b > 0.0f) ?
            dot / sqrtf(norm_a * norm_b) : -1.0f;
        float template_score = (cosine + 1.0f) * 0.5f;
        similarity = 0.35f * prediction + 0.65f * template_score;
    }
    *score_out = similarity;
    ESP_LOGI(TAG, "Voice score: %.3f (model %.3f, threshold %.2f)",
             similarity, prediction, AUTH_THRESHOLD);

    return (*score_out >= AUTH_THRESHOLD);
}

bool voice_auth_verify_multi(const int16_t* audio_samples, int sample_count,
                             int samples_per_recording, float* score_out)
{
    if (!audio_samples || !score_out || sample_count <= 0 || samples_per_recording <= 0) {
        return false;
    }
    float score_sum = 0.0f;
    int valid_count = 0;
    for (int sample = 0; sample < sample_count; ++sample) {
        float score = -1.0f;
        voice_auth_verify(audio_samples + sample * samples_per_recording,
                          samples_per_recording, &score);
        if (score >= 0.0f) {
            score_sum += score;
            ++valid_count;
        }
    }
    if (valid_count == 0) {
        *score_out = -1.0f;
        return false;
    }
    *score_out = score_sum / valid_count;
    return valid_count >= 2 && *score_out >= AUTH_THRESHOLD;
}

bool voice_auth_has_profile()
{
    return profile_loaded;
}

bool voice_auth_get_profile_name(char* name, size_t name_size)
{
    if (!profile_loaded || !name || name_size == 0) {
        return false;
    }
    strncpy(name, profile.name, name_size - 1);
    name[name_size - 1] = '\0';
    return true;
}

bool voice_auth_delete_profile(const char* user_id)
{
    if (!profile_loaded || !user_id || strcmp(profile.name, user_id) != 0) {
        return false;
    }
    nvs_handle_t handle;
    if (nvs_open("voice_auth", NVS_READWRITE, &handle) != ESP_OK) {
        return false;
    }
    esp_err_t result = nvs_erase_key(handle, "profile");
    if (result == ESP_OK) {
        result = nvs_commit(handle);
    }
    nvs_close(handle);
    if (result == ESP_OK) {
        memset(&profile, 0, sizeof(profile));
        profile_loaded = false;
    }
    return result == ESP_OK;
}
