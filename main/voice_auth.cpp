#include "voice_auth.h"
#include "esp_log.h"
#include "esp_dsp.h"
#include "esp_heap_caps.h"
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

    uint8_t* tensor_arena = nullptr;
    float* fft_work_buf = nullptr;
    float* hann_window = nullptr;

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

static void compute_mfcc_like_features(const int16_t* audio, int num_samples, TfLiteTensor* input_tensor, int max_val)
{
    const int frames = 32;
    const int hop = 512;

    // TỰ ĐỘNG ĐỌC THÔNG SỐ QUANTIZATION TỪ MODEL TFLITE THAY VÌ HARDCODE
    float scale = input_tensor->params.scale;
    int zero_point = input_tensor->params.zero_point;
    if (scale == 0.0f) scale = 0.1f; // Giá trị dự phòng an toàn

    for (int i = 0; i < frames; i++) {
        memset(fft_work_buf, 0, kFftBufFloats * sizeof(float));
        int start_idx = i * hop;

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

            // Đồng bộ chuẩn hoá năng lượng với training: energy / (512*512)
            float energy_norm = energy / (512.0f * 512.0f);
            float val = logf(energy_norm + 1e-6f);
            int8_t quantized = (int8_t)std::max(-128.0f, std::min(127.0f, roundf(val / scale) + zero_point));
            input_tensor->data.int8[i * 13 + b] = quantized;
        }
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
    (void)user_id;
    (void)audio;
    (void)num_samples;
    ESP_LOGW(TAG, "Enrollment is done on PC via Python; skipping device NVS write.");
    return true;
}

bool voice_auth_enroll_multi(const char* user_id, const int16_t* audio_samples,
                             int sample_count, int samples_per_recording)
{
    (void)user_id;
    (void)audio_samples;
    (void)sample_count;
    (void)samples_per_recording;
    ESP_LOGW(TAG, "Enrollment is done on PC via Python; skipping device NVS write.");
    return true;
}

bool voice_auth_verify(const int16_t* audio, int num_samples, float* score_out)
{
    if (!interpreter || !input || !output || !fft_work_buf || !hann_window) {
        return false;
    }

    float energy = 0.0f;
    int max_val = 0;
    for (int i = 0; i < num_samples; i++) {
        energy += ((float)audio[i] * (float)audio[i]);
        int a = abs(audio[i]);
        if (a > max_val) {
            max_val = a;
        }
    }
    float rms = sqrtf(energy / num_samples);
    if (rms < 30.0f || max_val < 100) {
        *score_out = -1.0f;
        return false;
    }
    ESP_LOGI(TAG, "Voice activity: RMS=%.1f, peak=%d", rms, max_val);

    compute_mfcc_like_features(audio, num_samples, input, max_val);

    if (interpreter->Invoke() != kTfLiteOk) {
        ESP_LOGE(TAG, "Invoke failed");
        return false;
    }

    float prediction = (output->data.int8[0] - output->params.zero_point) * output->params.scale;
    *score_out = prediction;
    ESP_LOGI(TAG, "Voice score: %.3f (threshold %.2f)", prediction, AUTH_THRESHOLD);

    return (*score_out >= AUTH_THRESHOLD);
}
