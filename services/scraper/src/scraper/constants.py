from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent.parent.parent
ATTEMPT_STEP = 8

# Directory structure for organized exports
OUTPUT_DIR = Path(ROOT_PATH, "output")
OUTPUT_DIR_MUSIC = Path(OUTPUT_DIR, "thai_lyrics")

# Per-platform subfolders
OUTPUT_DIR_MUSICATM = OUTPUT_DIR_MUSIC / "musicatm"
OUTPUT_DIR_SANOOK = OUTPUT_DIR_MUSIC / "sanookmusic"
OUTPUT_DIR_YOUTUBE = OUTPUT_DIR_MUSIC / "youtube"

# Global datetime format
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Ensure directories exist
for p in [OUTPUT_DIR, OUTPUT_DIR_MUSIC, OUTPUT_DIR_MUSICATM, OUTPUT_DIR_SANOOK, OUTPUT_DIR_YOUTUBE]:
    p.mkdir(parents=True, exist_ok=True)