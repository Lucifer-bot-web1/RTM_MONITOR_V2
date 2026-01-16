import time
import os
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- CONFIGURATION / செட்டிங்ஸ் ---
BRANCH_NAME = "main"
REPO_PATH = "."  # Current Directory (இந்த Folder-ஐ கவனிக்க)


class AutoGitHandler(FileSystemEventHandler):
    def on_modified(self, event):
        # .git folder-க்குள் நடக்கும் மாற்றங்களை கண்டுகொள்ள வேண்டாம்
        if ".git" in event.src_path: return
        # Folder-ஆக இருந்தால் Ignore செய்யவும் (File மாற்றங்கள் மட்டும் போதும்)
        if event.is_directory: return

        print(f"\n[DETECTED] Modified: {event.src_path}")
        self.force_push_to_github()

    def on_created(self, event):
        if ".git" in event.src_path: return

        # --- EMPTY FOLDER FIX (முக்கிய மாற்றம்) ---
        # Git சாதாரணமாக Empty Folder-ஐ மதிக்காது.
        # அதனால், நீங்கள் Folder உருவாக்கினால் உள்ளே ஒரு '.gitkeep' ஃபைலை உருவாக்குகிறோம்.
        if event.is_directory:
            print(f"\n[DETECTED] New Folder: {event.src_path}")
            gitkeep_path = os.path.join(event.src_path, ".gitkeep")
            try:
                # Create empty .gitkeep file
                with open(gitkeep_path, 'w') as f:
                    pass
                print(f"➕ J.A.R.V.I.S: Added .gitkeep to '{event.src_path}' so GitHub can see it.")
                # .gitkeep உருவானதால், அது 'File Created' கணக்கில் வந்து கீழே உள்ள Logic-ல் Push ஆகிவிடும்.
            except Exception as e:
                print(f"❌ Error creating .gitkeep: {e}")
            return
            # ----------------------------------------

        print(f"\n[DETECTED] Created File: {event.src_path}")
        self.force_push_to_github()

    def on_deleted(self, event):
        if ".git" in event.src_path: return
        print(f"\n[DETECTED] Deleted: {event.src_path}")
        self.force_push_to_github()

    def on_moved(self, event):
        if ".git" in event.src_path: return
        print(f"\n[DETECTED] Renamed/Moved: {event.src_path}")
        self.force_push_to_github()

    def force_push_to_github(self):
        # File save ஆக சிறிது நேரம் கொடுப்போம் (1 Second)
        time.sleep(1)
        print("🚀 Sending updates to GitHub...")
        try:
            # 1. Add all changes (New, Modified, Deleted)
            os.system("git add .")

            # 2. Commit
            # (stdout=subprocess.DEVNULL போட்டால் 'nothing to commit' மெசேஜ் தொந்தரவு செய்யாது)
            subprocess.run('git commit -m "Auto-Update: Local is Master"', shell=True, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)

            # 3. FORCE PUSH (Local -> GitHub ONLY)
            # GitHub-ல் என்ன இருந்தாலும் அதை அழித்துவிட்டு, Local-ல் இருப்பதை ஏற்றும்.
            result = subprocess.run(f"git push origin {BRANCH_NAME} --force", shell=True, capture_output=True,
                                    text=True)

            if result.returncode == 0:
                print("✅ Uploaded to GitHub Successfully!")
            else:
                # 'Everything up-to-date' என்பது Error கிடையாது, அதை தவிர்ப்போம்.
                if "Everything up-to-date" in result.stderr:
                    print("✅ Already up to date.")
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
    print("✨ Features: Auto-Syncs Files + Auto-Fixes Empty Folders")
    print("⚠️  WARNING: Local Files will OVERWRITE GitHub.")
    print("Press Ctrl+C to stop.")

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()