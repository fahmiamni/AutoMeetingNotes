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
COOLDOWN_SECONDS = 2
AUDIO_EXTENSIONS = ('.mp3', '.m4a', '.wav', '.ogg', '.mp4')


def is_audio_file(path: str) -> bool:
    return Path(path).suffix.lower() in AUDIO_EXTENSIONS

class DriveChangeHandler(FileSystemEventHandler):
    def __init__(self):
        
        self.last_run_at = 0

    def launch_automation(self, event_type, path):
        now = time.monotonic()
        if now - self.last_run_at < COOLDOWN_SECONDS:
            return

        self.last_run_at = now
        print(f"{event_type} detected: {path}")
        print("Launching automation...")
        subprocess.Popen([sys.executable, str(MAIN_SCRIPT_PATH)], cwd=PROJECT_DIR)

    def on_created(self, event):
        if not event.is_directory and is_audio_file(event.src_path):
            self.launch_automation("New file", event.src_path)

    def on_modified(self, event):
        if not event.is_directory and is_audio_file(event.src_path):
            self.launch_automation("File change", event.src_path)

if __name__ == "__main__":
    event_handler = DriveChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_PATH, recursive=False)
    observer.start()
    print(f"Monitoring folder: {WATCH_PATH}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
