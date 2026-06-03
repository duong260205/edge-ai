#!/usr/bin/env python3
"""
Filter ESC-50 dataset to select categories relevant for voice authentication.
Copies only 'human' impostor sounds (speech, cough, laugh) 
and 'environment' noise (fan, rain, wind) into a target folder.

Usage:
  python select_esc50.py C:/esc50/ESC-50-master ./esc50_selected --copy
  python main/collect_data.py import ./esc50_selected --label noise --recursive
"""

import os
import sys
import shutil
import csv
import glob

# Categories relevant for voice impostor / background noise
SELECTED_CATEGORIES = {
    # Human sounds (impostor speech-like)
    "coughing", "sneezing", "breathing", "laughing",
    "crying_baby", "snoring", "dog_bark", "cat", "rooster",
    "insects", "frog", "pig", "cow", "sheep", "chirping_birds",
    "crow", "crickets",
    # Environment noise (background)
    "washing_machine", "vacuum_cleaner", "fan", "air_conditioner",
    "hair_dryer", "door_wood_knock", "door_wood_creaks",
    "car_horn", "siren", "engine", "train", "airplane",
    "helicopter", "rain", "sea_waves", "crackling_fire",
    "pouring_water", "toilet_flush", "clock_tick",
    "thunderstorm", "wind", "hand_saw", "drilling",
    "chainsaw", "glass_breaking", "keys_jangling",
    "brushing_teeth", "clapping"
}

def main():
    if len(sys.argv) < 3:
        print("Usage: python select_esc50.py <esc50_root> <output_dir> [--copy]")
        print("  --copy : actually copy files (dry-run by default)")
        sys.exit(1)

    esc50_root = sys.argv[1]
    output_dir = sys.argv[2]
    do_copy = "--copy" in sys.argv

    # Find metadata CSV
    csv_path = os.path.join(esc50_root, "meta", "esc50.csv")
    if not os.path.exists(csv_path):
        # try alternative location
        for f in glob.glob(os.path.join(esc50_root, "**", "esc50.csv"), recursive=True):
            csv_path = f
            break

    if not os.path.exists(csv_path):
        print(f"[X] Cannot find esc50.csv in {esc50_root}")
        sys.exit(1)

    audio_dir = os.path.join(esc50_root, "audio")
    if not os.path.isdir(audio_dir):
        # try parent of csv
        audio_dir = os.path.dirname(csv_path)
        alt_audio = os.path.join(os.path.dirname(csv_path), "audio")
        if os.path.isdir(alt_audio):
            audio_dir = alt_audio

    os.makedirs(output_dir, exist_ok=True)

    # Read CSV and filter
    selected = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            category = row["category"].strip().lower()
            if category in SELECTED_CATEGORIES:
                selected.append((row["filename"], category))

    print(f"Found {len(selected)} matching files out of {sum(1 for _ in open(csv_path)) - 1} total")
    print(f"\nCategories included ({len(SELECTED_CATEGORIES)}):")
    cats = sorted(SELECTED_CATEGORIES)
    for i in range(0, len(cats), 5):
        print(f"  {', '.join(cats[i:i+5])}")

    # Count by category
    from collections import Counter
    counts = Counter(cat for _, cat in selected)
    print(f"\nFiles per category:")
    for cat, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {cnt} files")

    if do_copy:
        actual_copied = 0
        missing_count = 0
        
        for filename, category in selected:
            src = os.path.join(audio_dir, filename)
            if os.path.exists(src):
                dst_name = f"{category}_{filename}"
                dst = os.path.join(output_dir, dst_name)
                shutil.copy2(src, dst)
                actual_copied += 1
            else:
                if missing_count == 0:
                    print(f"\n[!] LỖI: Không tìm thấy file nguồn tại: {audio_dir}")
                missing_count += 1
                
        if missing_count > 0:
            print(f"[X] Bỏ qua {missing_count} files vì không tìm thấy file nguồn!")
            
        print(f"\nThực tế đã copy thành công {actual_copied} files vào {output_dir}")
    else:
        print(f"\nDry-run complete. Re-run with --copy to actually copy files.")

if __name__ == "__main__":
    main()
