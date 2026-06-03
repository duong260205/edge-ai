"""
Dump all TFLite operators from a .tflite flatbuffer file.
Usage: python tools/dump_tflite_ops.py [path/to/model.tflite]
"""
import sys
import struct

def read_tflite_ops(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # TFLite uses FlatBuffers. The schema has operator codes followed by operators.
    # We'll use a simpler approach: parse the flatbuffer manually or use tflite if available.
    try:
        import tensorflow as tf
        interpreter = tf.lite.Interpreter(model_path=filepath)
        interpreter.allocate_tensors()
        
        # Get all operator details
        op_details = interpreter._get_ops_details()
        
        print(f"Model: {filepath}")
        print(f"File size: {len(data)} bytes")
        print(f"\n--- All Operators ({len(op_details)} total) ---")
        
        for op in op_details:
            print(f"  [{op['index']}] {op['op_name']}")
        
        print(f"\n--- Input Details ---")
        for inp in interpreter.get_input_details():
            print(f"  Name: {inp['name']}, Shape: {inp['shape']}, Type: {inp['dtype']}")
            print(f"  Quantization: scale={inp.get('quantization_parameters', {}).get('scales', 'N/A')}, "
                  f"zero_point={inp.get('quantization_parameters', {}).get('zero_points', 'N/A')}")
        
        print(f"\n--- Output Details ---")
        for out in interpreter.get_output_details():
            print(f"  Name: {out['name']}, Shape: {out['shape']}, Type: {out['dtype']}")
            print(f"  Quantization: scale={out.get('quantization_parameters', {}).get('scales', 'N/A')}, "
                  f"zero_point={out.get('quantization_parameters', {}).get('zero_points', 'N/A')}")
        
        return op_details
    
    except ImportError:
        print("TensorFlow not available, trying flatbuffer parsing...")
        return None

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "voice_auth.tflite"
    read_tflite_ops(path)
