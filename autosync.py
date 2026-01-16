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
        self.smart_sync()

    def on_created(self, event):
        if ".git" in event.src_path: return
        print(f"\n[DETECTED] Created: {event.src_path}")
        self.smart_sync()

    def run_command(self, command):
        """Run shell command and return output/error code"""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                return False, result.stderr
            return True, result.stdout
        except Exception as e:
            return False, str(e)

    def remove_lock_file(self):
        """Fixes '.git/index.lock' error if git crashed previously"""
        lock_file = os.path.join(REPO_PATH, ".git", "index.lock")
        if os.path.exists(lock_file):
            print("⚠️ Lock file found! Removing it to fix Git...")
            try:
                os.remove(lock_file)
                print("✅ Lock file removed.")
            except:
                print("❌ Could not remove lock file.")

    def smart_sync(self):
        print("🔄 Starting Smart Sync...")

        # 1. First, fix any lock files
        self.remove_lock_file()

        # 2. Add all changes
        self.run_command("git add .")

        # 3. Commit (Ignore if nothing to commit)
        success, output = self.run_command('git commit -m "Auto Update: J.A.R.V.I.S Sync"')
        if "nothing to commit" in output:
            print("ℹ️ Nothing new to commit.")

        # 4. Try Pushing
        print("🚀 Attempting to Push...")
        success, error = self.run_command(f"git push origin {BRANCH_NAME}")

        if success:
            print("✅ Push Successful!")
        else:
            # 5. AUTO CORRECT LOGIC (If Push Fails)
            print("⚠️ Push Failed! (Likely Remote Changes). Attempting Auto-Fix...")
            print(f"Error details: {error}")

            # Step A: Pull changes from GitHub (Rebase to keep history clean)
            print("⬇️ Pulling latest changes from GitHub...")
            pull_success, pull_err = self.run_command(f"git pull origin {BRANCH_NAME} --rebase")

            if pull_success:
                print("✅ Pull Successful. Retrying Push...")
                # Step B: Push again after Pull
                retry_success, retry_err = self.run_command(f"git push origin {BRANCH_NAME}")
                if retry_success:
                    print("✅ Auto-Fix Successful! Synced with GitHub.")
                else:
                    print(f"❌ Auto-Fix Failed during retry push: {retry_err}")
            else:
                # If Pull fails, it might be a conflict or stash needed
                print(f"❌ Auto-Fix Pull Failed: {pull_err}")
                print("Trying Force Push (Last Resort)...")
                # Optional: Uncomment below line if you want to FORCE overwrite GitHub (Dangerous)
                # self.run_command(f"git push origin {BRANCH_NAME} --force")


if __name__ == "__main__":
    path = REPO_PATH
    event_handler = AutoGitHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)

    print(f"🤖 J.A.R.V.I.S Auto-Sync Module Active on: {os.path.abspath(path)}")
    print("---------------------------------------------------------")
    print("Monitors file changes & Auto-corrects Git errors.")
    print("Press Ctrl+C to stop.")

    observer.start()
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()