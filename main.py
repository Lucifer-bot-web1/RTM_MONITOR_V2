import sys
import threading
import time
import webview
import subprocess
import platform
import json
from flask import Flask
from flask_socketio import SocketIO, emit
from config import Config
from core.database import db, User
from core.security import SecurityManager
from network.pinger import PingWorker
from web_ui.routes import bp as main_bp


def create_app():
    app = Flask(__name__, static_folder='web_ui/static', static_url_path='/static')
    app.config.from_object(Config)
    db.init_app(app)

    # Login Manager Setup
    from flask_login import LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    @login_manager.user_loader
    def load_user(uid):
        return User.query.get(int(uid))

    app.register_blueprint(main_bp)
    return app


app = create_app()
socketio = SocketIO(app, async_mode="threading")

# --- REAL PING ENGINE ---
ping_process = None
ping_stop_event = threading.Event()


def run_real_ping(target_ip):
    global ping_process
    # Windows uses -t, Linux uses -i 1 (continuous) but here we adhere to continuous logic
    param = '-t' if platform.system().lower() == 'windows' else '-i 1'
    # Linux ping loop might need just simple 'ping ip'
    cmd_list = ['ping', target_ip, param] if platform.system().lower() == 'windows' else ['ping', target_ip]

    try:
        ping_process = subprocess.Popen(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in iter(ping_process.stdout.readline, ''):
            if ping_stop_event.is_set():
                break
            if line:
                socketio.emit('ping_output', {'line': line.strip()})
    except Exception as e:
        socketio.emit('ping_output', {'line': f"Error: {str(e)}"})
    finally:
        if ping_process:
            ping_process.terminate()
            ping_process = None


@socketio.on('start_ping')
def handle_start_ping(data):
    global ping_stop_event
    target = data.get('ip')
    ping_stop_event.clear()
    t = threading.Thread(target=run_real_ping, args=(target,))
    t.daemon = True
    t.start()


@socketio.on('stop_ping')
def handle_stop_ping():
    global ping_stop_event
    ping_stop_event.set()
    if ping_process:
        ping_process.terminate()
    emit('ping_output', {'line': '>>> PROCESS TERMINATED BY USER'})


if __name__ == '__main__':
    # Initialize DB
    with app.app_context():
        db.create_all()
        # Ensure Superadmin exists
        # (Your existing logic for creating admin/license can go here if needed)

    # Start Background Monitor
    pinger = PingWorker(app, socketio)
    pinger.start()


    # Run Server
    def run_server():
        print(">>> 🌐 RTM SERVER LIVE on http://0.0.0.0:5050")
        socketio.run(app, host='0.0.0.0', port=5050, debug=False, use_reloader=False)


    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    time.sleep(1)

    # Launch UI
    webview.create_window(
        title="RTM Enterprise Server",
        url="http://127.0.0.1:5050",
        width=1280, height=800, background_color='#0b0c0e'
    )
    webview.start()
    pinger.stop_event.set()
    sys.exit()