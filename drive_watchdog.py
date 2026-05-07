import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- CONFIGURATION ---
WATCH_PATH = r"G:\My Drive"
BATCH_FILE_PATH = r"D:\11 MY APP\18 Auto_Meeting_Notes_Compile\main..bat"
COOLDOWN_SECONDS = 2

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
        subprocess.Popen([BATCH_FILE_PATH], shell=True)

    def on_created(self, event):
        if not event.is_directory:
            self.launch_automation("New file", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
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
