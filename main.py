import sys
import threading
import time
import webview
import subprocess
import platform
import psutil  # SYSTEM MONITORING
import os
from flask import Flask, request, jsonify
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

    # Increase max upload size for audio files (e.g., 5MB)
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

    from flask_login import LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    @login_manager.user_loader
    def load_user(uid):
        return User.query.get(int(uid))

    app.register_blueprint(main_bp)

    # --- SOUND UPLOAD ROUTE ---
    @app.route('/upload_sound', methods=['POST'])
    def upload_sound():
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file part'})
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No selected file'})

        if file and file.filename.endswith(('.mp3', '.wav', '.ogg')):
            # Save as 'custom_alert.mp3' to overwrite old one
            save_path = os.path.join(app.static_folder, 'sounds', 'custom_alert.mp3')

            # Ensure directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            file.save(save_path)
            return jsonify({'success': True, 'message': 'Sound updated!'})
        else:
            return jsonify({'success': False, 'message': 'Invalid format. Use mp3/wav'})

    return app


app = create_app()
socketio = SocketIO(app, async_mode="threading")

# --- REAL PING ENGINE ---
ping_process = None
ping_stop_event = threading.Event()


def run_real_ping(target_ip):
    global ping_process
    param = '-t' if platform.system().lower() == 'windows' else '-i 1'
    cmd_list = ['ping', target_ip, param] if platform.system().lower() == 'windows' else ['ping', target_ip]

    try:
        ping_process = subprocess.Popen(
            cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
        for line in iter(ping_process.stdout.readline, ''):
            if ping_stop_event.is_set(): break
            if line:
                # Emit to Terminal
                socketio.emit('ping_output', {'line': line.strip()})

                # Emit to Logs (Heartbeat) - Optional: Filter only replies to reduce noise
                if "Reply" in line or "bytes=" in line:
                    socketio.emit('log_update', {'time': time.strftime("%H:%M:%S"), 'device': target_ip, 'status': 'UP',
                                                 'msg': 'Ping Response OK'})
                elif "timed out" in line or "unreachable" in line:
                    socketio.emit('log_update',
                                  {'time': time.strftime("%H:%M:%S"), 'device': target_ip, 'status': 'DOWN',
                                   'msg': 'Request Timed Out'})

    except Exception as e:
        socketio.emit('ping_output', {'line': f"Error: {str(e)}"})
    finally:
        if ping_process: ping_process.terminate(); ping_process = None


@socketio.on('start_ping')
def handle_start_ping(data):
    global ping_stop_event
    ping_stop_event.clear()
    t = threading.Thread(target=run_real_ping, args=(data.get('ip'),))
    t.daemon = True
    t.start()


@socketio.on('stop_ping')
def handle_stop_ping():
    global ping_stop_event
    ping_stop_event.set()
    if ping_process: ping_process.terminate()
    emit('ping_output', {'line': '>>> STOPPED BY USER'})


# --- REAL SYSTEM MONITOR (CPU/RAM/NET) ---
def monitor_resources():
    while True:
        # CPU & RAM
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent

        # Network Speed
        net1 = psutil.net_io_counters()
        time.sleep(1)
        net2 = psutil.net_io_counters()

        sent_mbps = round((net2.bytes_sent - net1.bytes_sent) * 8 / 1024 / 1024, 2)
        recv_mbps = round((net2.bytes_recv - net1.bytes_recv) * 8 / 1024 / 1024, 2)

        socketio.emit('system_stats', {
            'cpu': cpu, 'ram': ram,
            'tx': sent_mbps, 'rx': recv_mbps
        })


if __name__ == '__main__':
    with app.app_context(): db.create_all()

    pinger = PingWorker(app, socketio)
    pinger.start()

    sys_thread = threading.Thread(target=monitor_resources)
    sys_thread.daemon = True
    sys_thread.start()


    def run_server():
        print(">>> 🌐 RTM SERVER LIVE on http://0.0.0.0:5050")
        socketio.run(app, host='0.0.0.0', port=5050, debug=False, use_reloader=False)


    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1)

    webview.create_window(title="RTM Enterprise Server", url="http://127.0.0.1:5050", width=1280, height=800,
                          background_color='#0b0c0e')
    webview.start()
    pinger.stop_event.set()
    sys.exit()