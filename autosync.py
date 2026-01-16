import time
import os
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- CONFIGURATION ---
BRANCH_NAME = "main"
REPO_PATH = "."  # Current Directory


class AutoGitHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if ".git" in event.src_path: return
        print(f"\n[DETECTED] Modified: {event.src_path}")
        self.force_push_to_github()

    def on_created(self, event):
        if ".git" in event.src_path: return
        print(f"\n[DETECTED] Created: {event.src_path}")
        self.force_push_to_github()

    def on_deleted(self, event):
        if ".git" in event.src_path: return
        print(f"\n[DETECTED] Deleted: {event.src_path}")
        self.force_push_to_github()

    def force_push_to_github(self):
        print("🚀 Sending updates to GitHub...")
        try:
            # 1. Add all changes (New, Modified, Deleted)
            os.system("git add .")

            # 2. Commit
            os.system('git commit -m "Auto-Update: Local is Master"')

            # 3. FORCE PUSH (This overwrites GitHub with Local content)
            # GitHub-ல் இருந்து எதையும் எடுக்காது. Local-ல் இருப்பதை திணிக்கும்.
            result = subprocess.run(f"git push origin {BRANCH_NAME} --force", shell=True, capture_output=True,
                                    text=True)

            if result.returncode == 0:
                print("✅ Uploaded to GitHub Successfully!")
            else:
                print(f"⚠️ Push Error: {result.stderr}")

        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    path = REPO_PATH
    event_handler = AutoGitHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)

    print(f"🤖 J.A.R.V.I.S One-Way Sync Active (Local -> GitHub)")
    print("---------------------------------------------------------")
    print("⚠️  WARNING: This will OVERWRITE GitHub with your Local files.")
    print("NO files will be downloaded from GitHub.")
    print("Press Ctrl+C to stop.")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()