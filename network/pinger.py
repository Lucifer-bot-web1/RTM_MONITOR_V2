import threading
import time
from datetime import datetime
from pythonping import ping as py_ping
from core.database import db, Device, Setting
from core.audio_mgr import AudioManager
from flask_socketio import SocketIO


class PingWorker(threading.Thread):
    def __init__(self, app, socketio: SocketIO):
        super().__init__()
        self.app = app
        self.socketio = socketio
        self.daemon = True
        self.stop_event = threading.Event()

    def run(self):
        print(">>> J.A.R.V.I.S Ping Engine Started")
        while not self.stop_event.is_set():
            with self.app.app_context():
                self._cycle()
            time.sleep(2)

    def _cycle(self):
        try:
            interval = int(Setting.get("ping_timeout_sec", "30"))
        except:
            interval = 30

        devices = Device.query.filter_by(is_paused=False, is_stopped=False).all()

        for d in devices:
            ok, rtt = self._ping_device(d.ip, interval)
            new_state = "UP" if ok else "DOWN"

            if d.state != new_state:
                # State Changed
                d.state = new_state
                d.updated_at = datetime.utcnow()
                db.session.commit()

                # Trigger Actions
                if new_state == "DOWN":
                    duration = int(Setting.get("alarm_duration_sec", "5"))
                    AudioManager.play_alarm(duration)
                    self.socketio.emit('alert', {'msg': f'{d.name} is DOWN!', 'type': 'error'})

                # Update UI
                self.socketio.emit('device_update', {
                    'ip': d.ip, 'state': new_state, 'rtt': rtt
                })

    def _ping_device(self, ip, timeout):
        try:
            resp = py_ping(ip, count=1, timeout=timeout)
            return resp.success(), round(resp.rtt_avg_ms, 1) if resp.success() else 0
        except:
            return False, 0