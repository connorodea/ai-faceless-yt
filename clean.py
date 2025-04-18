import os
import glob

def clean_temp_files():
    patterns = [
        "scene_*.png",
        "music_*.mp3",
        "logs/*.log",
        "temp/*",
    ]
    for pattern in patterns:
        for path in glob.glob(pattern):
            try:
                os.remove(path)
                print(f"Removed: {path}")
            except IsADirectoryError:
                continue
            except Exception as e:
                print(f"Failed to remove {path}: {e}")

if __name__ == "__main__":
    clean_temp_files()