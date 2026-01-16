import threading
import time
import winsound  # Windows only


class AudioManager:
    """
    Manages audio alerts on a separate thread using Windows native sound.
    This works even if the UI is minimized or in background.
    """
    _lock = threading.Lock()
    _is_playing = False

    @staticmethod
    def play_alarm(duration_sec=5):
        if AudioManager._is_playing:
            return  # Don't overlap sounds

        def _beep_loop():
            with AudioManager._lock:
                AudioManager._is_playing = True

            end_time = time.time() + int(duration_sec)
            try:
                while time.time() < end_time:
                    # Freq: 1000Hz, Duration: 400ms
                    winsound.Beep(1000, 400)
                    time.sleep(0.1)
            except:
                pass

            with AudioManager._lock:
                AudioManager._is_playing = False

        # Run in daemon thread so it doesn't block the app
        t = threading.Thread(target=_beep_loop, daemon=True)
        t.start()