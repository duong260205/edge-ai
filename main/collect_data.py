
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import os
import time

SAMPLE_RATE = 16000
DURATION = 1.0  # seconds
DATASET_DIR = "dataset"
CLASS_NAME = "noise" # Đổi thành "noise" để thu tiếng ồn/giọng người khác
NUM_SAMPLES = 20      # Thu giới hạn 20 mẫu cho đỡ bị treo

os.makedirs(os.path.join(DATASET_DIR, CLASS_NAME), exist_ok=True)

print(f"=== BẮT ĐẦU THU ÂM CHO NHÃN: {CLASS_NAME} ===")
print(f"Sẽ thu {NUM_SAMPLES} mẫu, mỗi mẫu dài {DURATION} giây.")
print("Chuẩn bị nói vào micro trong 3 giây...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)

try:
    for count in range(NUM_SAMPLES):
        print(f"Đang ghi âm mẫu {count + 1}/{NUM_SAMPLES}... (HÃY NÓI!)")
        audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='int16')
        sd.wait()
        filename = os.path.join(DATASET_DIR, CLASS_NAME, f"sample_{count}.wav")
        wav.write(filename, SAMPLE_RATE, audio)
        print(f" -> Đã lưu {filename}")
        time.sleep(0.5)
        
    print("\n=== THU ÂM HOÀN TẤT! ===")
except KeyboardInterrupt:
    print("\nĐã dừng thu âm sớm.")
