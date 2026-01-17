import sys
import threading
import time
import webview
from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
from datetime import datetime, timedelta

from config import Config
from core.database import db, User
from core.security import SecurityManager
from network.pinger import PingWorker
from web_ui.routes import bp as main_bp


def create_app():
    app = Flask(__name__, static_folder='web_ui/static', static_url_path='/static')
    app.config.from_object(Config)
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    @login_manager.user_loader
    def load_user(uid):
        return User.query.get(int(uid))

    app.register_blueprint(main_bp)
    return app


if __name__ == '__main__':
    app = create_app()
    socketio = SocketIO(app, async_mode="threading")

    with app.app_context():
        db.create_all()

        # --- SUBSCRIPTION ACTIVATION LOGIC ---
        # Check if 'superadmin' exists. If not, this is a NEW INSTALL.
        admin = User.query.filter_by(username='superadmin').first()

        if not admin:
            print("\n>>> 🟢 NEW SUBSCRIPTION DETECTED. ACTIVATING...")

            # 1. Lock to THIS Computer
            hw_id = SecurityManager.get_system_id()
            print(f">>> 🔒 Hardware Fingerprint: {hw_id}")

            # 2. Set Expiry (e.g., 30 Days Trial or 1 Year)
            expiry_date = datetime.now() + timedelta(days=365)

            # 3. Generate Tamper-Proof Seal
            seal = SecurityManager.generate_license_hash(expiry_date.strftime('%Y-%m-%d'), hw_id)

            # 4. Create Master User
            new_admin = User(
                username='superadmin',
                role='ADMIN',
                expires_at=expiry_date,
                license_hash=seal
            )
            new_admin.set_password('Tech@admin')  # Default Master Password

            db.session.add(new_admin)
            db.session.commit()
            print(f">>> ✅ LICENSE ACTIVATED for 'superadmin'. Valid until {expiry_date.strftime('%Y-%m-%d')}")
        else:
            print(">>> 🔵 SYSTEM LOADED: Valid Subscription Found.")

    # Start Ping Engine
    pinger = PingWorker(app, socketio)
    pinger.start()


    # Run Server (LAN Mode)
    def run_server():
        # Using 0.0.0.0 allows LAN access (Web Connect)
        print(">>> 🌐 RTM SERVER STARTED on PORT 5050")
        socketio.run(app, host='0.0.0.0', port=5050, debug=False, use_reloader=False)


    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    time.sleep(1)

    # Open App Window (Server Side)
    webview.create_window(
        title="RTM Enterprise Server",
        url="http://127.0.0.1:5050",
        width=1280,
        height=800,
        background_color='#0b0c0e'
    )

    webview.start()
    pinger.stop_event.set()
    sys.exit()