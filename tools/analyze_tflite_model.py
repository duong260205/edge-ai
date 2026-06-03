"""
Analyze TFLite model: show operator graph and tensor details.
Usage: python tools/analyze_tflite_model.py [path/to/model.tflite]
"""
import sys
import numpy as np
import tensorflow as tf

path = sys.argv[1] if len(sys.argv) > 1 else "voice_auth.tflite"

# 1. Load TFLite model and show graph
print("=== TFLITE MODEL GRAPH ===")
print("Model file:", path)

interpreter = tf.lite.Interpreter(model_path=path)
interpreter.allocate_tensors()

# Get op details
op_details = interpreter._get_ops_details()

print("\nTotal operators:", len(op_details))
for op in op_details:
    print("  [%2d] %s  inputs=%s  outputs=%s" % (
        op['index'], op['op_name'].ljust(25), op['inputs'], op['outputs']))

# 2. Input/Output details
print("\n=== INPUT/OUTPUT TENSORS ===")
for i, inp in enumerate(interpreter.get_input_details()):
    print("  INPUT [%d]: name=%s  shape=%s  dtype=%s  scale=%s  zp=%s" % (
        i, inp['name'], inp['shape'], inp['dtype'],
        inp.get('quantization', (0,))[0],
        inp.get('quantization', (0, 0))[1] if len(inp.get('quantization', (0,))) > 1 else 0))

for i, out in enumerate(interpreter.get_output_details()):
    print("  OUTPUT [%d]: name=%s  shape=%s  dtype=%s  scale=%s  zp=%s" % (
        i, out['name'], out['shape'], out['dtype'],
        out.get('quantization', (0,))[0],
        out.get('quantization', (0, 0))[1] if len(out.get('quantization', (0,))) > 1 else 0))

# 3. Mapping explanation
print("\n=== KERAS LAYER -> TFLITE OP MAPPING ===")
mapping = [
    ("Input(32,13,1)",              "--- (no op) ---",      "Chi dinh shape dau vao"),
    ("Conv2D(8,3,'relu','same')",   "CONV_2D",              "Tich chap 2D + ReLU fused"),
    ("MaxPooling2D(2)",             "MAX_POOL_2D",           "Pooling 2x2"),
    ("Conv2D(16,3,'relu','same')",  "CONV_2D",              "Tich chap 2D + ReLU fused"),
    ("MaxPooling2D(2)",             "MAX_POOL_2D",           "Pooling 2x2"),
    ("Flatten()",                   "RESHAPE + SHAPE + STRIDED_SLICE + PACK",
                                                              "Flatten -> RESHAPE.\n     3 op con lai do converter them de xu ly dynamic shape khi INT8 quant"),
    ("Dense(32,'relu')",            "FULLY_CONNECTED",       "FC + ReLU fused"),
    ("Dense(1,'sigmoid')",          "FULLY_CONNECTED + LOGISTIC",
                                                              "FC logits + Sigmoid tach roi"),
]
print("%-40s %-35s %s" % ("Keras Layer", "TFLite Op(s)", "Ghi chu"))
print("-" * 100)
for layer, op, note in mapping:
    print("%-40s %-35s %s" % (layer, op, note))

print("\n=== GIAI THICH OPS 'LA' (SHAPE, STRIDED_SLICE, PACK) ===")
print()
print("  3 op nay la optimization noi bo cua TFLite converter khi gap")
print("  Flatten + full INT8 quantization. Chung tao ra graph:")
print()
print("    SHAPE -> STRIDED_SLICE -> PACK -> RESHAPE")
print()
print("  Muc dich: converter can tinh toan lai kich thuoc tensor sau Flatten")
print("  bang cach doc shape runtime, cat lay batch dimension, dong goi lai")
print("  bang PACK, roi dua vao RESHAPE. Day la hanh vi binh thuong,")
print("  KHONG phai loi hay op dac biet.")
print()
print("  Tat ca 8 op da duoc dang ky trong MicroMutableOpResolver<8>.")
