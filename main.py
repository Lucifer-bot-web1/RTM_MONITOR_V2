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
    # LAN Mode Enabled: static files from web_ui
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
        # 1. DATABASE INIT
        db.create_all()

        # 2. ADMIN & LICENSE GENERATION (First Run Logic)
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print(">>> INITIAL SETUP: Creating Master Admin & License...")

            # Step A: Set Expiry (30 Days Trial)
            expiry_date = datetime.now() + timedelta(days=30)

            # Step B: Get Hardware ID of this Server
            hw_id = SecurityManager.get_system_id()

            # Step C: Create Digital Seal
            seal = SecurityManager.generate_license_hash(expiry_date.strftime('%Y-%m-%d'), hw_id)

            new_admin = User(
                username='admin',
                role='ADMIN',
                expires_at=expiry_date,
                license_hash=seal
            )
            new_admin.set_password('admin123')

            db.session.add(new_admin)
            db.session.commit()
            print(f">>> SECURITY: System Locked to HW-ID: {hw_id}")
            print(f">>> LICENSE: Valid until {expiry_date}")
            print(">>> LOGIN: admin / admin123")

    # 3. START PING ENGINE
    pinger = PingWorker(app, socketio)
    pinger.start()


    # 4. RUN SERVER (LAN ACCESS ENABLED)
    def run_server():
        # host='0.0.0.0' allows other PCs in the network to connect
        print(">>> RTM ENTERPRISE LIVE on http://0.0.0.0:5050")
        socketio.run(app, host='0.0.0.0', port=5050, debug=False, use_reloader=False)


    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    time.sleep(1)

    # 5. LAUNCH APP WINDOW (Server Side)
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