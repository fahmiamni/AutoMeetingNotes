import time
import subprocess
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- CONFIGURATION ---
WATCH_PATH = r"G:\My Drive"
PROJECT_DIR = Path(__file__).resolve().parent
MAIN_SCRIPT_PATH = PROJECT_DIR / "main.py"
COOLDOWN_SECONDS = 10
AUDIO_EXTENSIONS = ('.mp3', '.m4a', '.wav', '.ogg', '.mp4')


def is_audio_file(path: str) -> bool:
    return Path(path).suffix.lower() in AUDIO_EXTENSIONS


def get_watch_path() -> Path:
    if WATCH_PATH.is_dir():
        return WATCH_PATH

    fallback_path = BASE_DIR / "input"
    if fallback_path.is_dir() and WATCH_PATH == DEFAULT_WATCH_PATH:
        print(f"Warning: preferred watch folder does not exist: {WATCH_PATH}")
        print(f"Falling back to local input folder: {fallback_path}")
        return fallback_path

    print(f"Error: watch folder does not exist: {WATCH_PATH}")
    print("Set MEETING_NOTES_WATCH_PATH to the folder you want to monitor.")
    sys.exit(1)


def get_batch_file_path() -> Path:
    if BATCH_FILE_PATH.is_file():
        return BATCH_FILE_PATH

    print(f"Error: batch file does not exist: {BATCH_FILE_PATH}")
    print("Set MEETING_NOTES_BATCH_FILE to the batch file you want to run.")
    sys.exit(1)

class DriveChangeHandler(FileSystemEventHandler):
    def __init__(self, batch_file_path: Path):
        self.batch_file_path = batch_file_path
        self.last_run_at = 0

    def launch_automation(self, event_type, path):
        now = time.monotonic()
        if now - self.last_run_at < COOLDOWN_SECONDS:
            return

        self.last_run_at = now
        print(f"{event_type} detected: {path}")
        print("Launching automation...")
        subprocess.run([sys.executable, str(MAIN_SCRIPT_PATH)], cwd=PROJECT_DIR)

    def on_created(self, event):
        if not event.is_directory and is_audio_file(event.src_path):
            self.launch_automation("New file", event.src_path)

    def on_modified(self, event):
        if not event.is_directory and is_audio_file(event.src_path):
            self.launch_automation("File change", event.src_path)

if __name__ == "__main__":
    watch_path = get_watch_path()
    batch_file_path = get_batch_file_path()
    event_handler = DriveChangeHandler(batch_file_path)
    observer = Observer()
    observer.schedule(event_handler, str(watch_path), recursive=False)
    observer.start()
    print(f"Monitoring folder: {watch_path}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
