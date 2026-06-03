import os
import librosa
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
import sys

SAMPLE_RATE = 16000
DURATION = 1.0
N_MFCC = 13
HOP_LENGTH = 512
DATASET_DIR = "dataset"

# Tự động tạo dữ liệu mẫu nếu thư mục trống
if not os.path.exists(os.path.join(DATASET_DIR, "target")) or len(os.listdir(os.path.join(DATASET_DIR, "target"))) == 0:
    print("LỖI: Chưa có file âm thanh nào! Đang tự động tạo dữ liệu ảo (dummy data) để test...")
    import scipy.io.wavfile as wav
    os.makedirs(os.path.join(DATASET_DIR, "target"), exist_ok=True)
    os.makedirs(os.path.join(DATASET_DIR, "noise"), exist_ok=True)
    for i in range(20):
        t = np.linspace(0, 1., SAMPLE_RATE)
        wav.write(os.path.join(DATASET_DIR, "target", f"dummy_{i}.wav"), SAMPLE_RATE, (np.sin(2 * np.pi * 440 * t) * 10000).astype('int16'))
        wav.write(os.path.join(DATASET_DIR, "noise", f"dummy_{i}.wav"), SAMPLE_RATE, np.random.randint(-10000, 10000, SAMPLE_RATE, dtype='int16'))
    print("Đã tạo dummy data. Để có model thật, vui lòng chạy 'collect_data.py' để ghi âm thực tế!\n")

# 1. Load Data and Extract MFCC
def extract_mfcc(file_path):
    audio, sr = librosa.load(file_path, sr=SAMPLE_RATE)
    if len(audio) < SAMPLE_RATE:
        audio = np.pad(audio, (0, SAMPLE_RATE - len(audio)), 'constant')
    else:
        audio = audio[:SAMPLE_RATE]
        
    # --- ĐỒNG BỘ CHUẨN HOÁ ÂM LƯỢNG VỚI C++ ---
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val
    
    # --- ĐỒNG BỘ THUẬT TOÁN ESP-DSP FFT VỚI C++ ---
    frames = 32
    hop = 512
    fft_size = 512
    features = np.zeros((frames, 13), dtype=np.float32)
    
    window = 0.5 * (1.0 - np.cos(2.0 * np.pi * np.arange(fft_size) / fft_size))
    
    for i in range(frames):
        start_idx = i * hop
        segment = audio[start_idx : start_idx + fft_size]
        if len(segment) < fft_size:
            segment = np.pad(segment, (0, fft_size - len(segment)), 'constant')
            
        windowed = segment * window
        fft_result = np.fft.rfft(windowed)
        
        for b in range(13):
            bin_start = b * 19 # 256 / 13 = 19
            bin_end = (b + 1) * 19
            energy = np.sum(np.abs(fft_result[bin_start:bin_end])**2)
            features[i, b] = np.log(energy / (512.0 * 512.0) + 1e-6)
            
    return features # Shape: (32, 13)

X, y = [], []
# Expecting two folders: 'target' (your voice) and 'noise' (others/background)
for label, class_name in enumerate(["noise", "target"]):
    class_dir = os.path.join(DATASET_DIR, class_name)
    if not os.path.exists(class_dir): continue
    for file in os.listdir(class_dir):
        if file.endswith('.wav'):
            mfcc = extract_mfcc(os.path.join(class_dir, file))
            X.append(mfcc)
            y.append(label)

if len(X) == 0:
    print("LỖI: Không đọc được dữ liệu. Hãy kiểm tra lại thư mục dataset!")
    sys.exit(1)

X = np.array(X)[..., np.newaxis] # Add channel dimension -> (N, Time, 13, 1)
y = np.array(y)

# 2. Build Lightweight CNN
model = models.Sequential([
    layers.Input(shape=X.shape[1:]),
    layers.Conv2D(8, 3, activation='relu', padding='same'),
    layers.MaxPooling2D(2),
    layers.Conv2D(16, 3, activation='relu', padding='same'),
    layers.MaxPooling2D(2),
    layers.Flatten(),
    layers.Dense(32, activation='relu'),
    layers.Dense(1, activation='sigmoid') # Binary Output
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
print("Training Model...")
model.fit(X, y, epochs=15, batch_size=16, validation_split=0.2)

# 3. INT8 Quantization
def representative_data_gen():
    for input_value in tf.data.Dataset.from_tensor_slices(X).batch(1).take(100):
        yield [tf.cast(input_value, tf.float32)]

converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_data_gen
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8
tflite_model = converter.convert()

with open("voice_auth.tflite", "wb") as f:
    f.write(tflite_model)

# 4. Export to C/C++ Header
def export_to_c(tflite_bytes, output_cc, output_h):
    array_name = "g_voice_auth_model_data"
    
    # Create .h
    with open(output_h, "w") as f:
        f.write("#ifndef MODEL_DATA_H\n#define MODEL_DATA_H\n\n")
        f.write("#ifdef __cplusplus\nextern \"C\" {\n#endif\n\n")
        f.write(f"extern const unsigned char {array_name}[];\n")
        f.write(f"extern const int {array_name}_len;\n\n")
        f.write("#ifdef __cplusplus\n}\n#endif\n\n")
        f.write("#endif // MODEL_DATA_H\n")
        
    # Create .cc
    with open(output_cc, "w") as f:
        f.write("#include \"model_data.h\"\n\n")
        f.write("#ifdef __cplusplus\nextern \"C\" {\n#endif\n\n")
        f.write(f"const unsigned char {array_name}[] = {{\n  ")
        for i, val in enumerate(tflite_bytes):
            f.write(f"0x{val:02x}, ")
            if (i + 1) % 12 == 0:
                f.write("\n  ")
        f.write(f"\n}};\n")
        f.write(f"const int {array_name}_len = {len(tflite_bytes)};\n")
        f.write("\n#ifdef __cplusplus\n}\n#endif\n")

export_to_c(tflite_model, "model_data.cc", "model_data.h")
print("Exported to model_data.cc and .h successfully!")
