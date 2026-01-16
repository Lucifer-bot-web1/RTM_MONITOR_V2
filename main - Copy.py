import sys
import threading
import time
import webview
from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
from datetime import datetime, timedelta  # Added for expiry fix

from config import Config
from core.database import db, User
from network.pinger import PingWorker
from web_ui.routes import bp as main_bp


def create_app():
    app = Flask(__name__)
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

        # --- FIX: ROBUST ADMIN CREATION ---
        if not User.query.filter_by(username='admin').first():
            print(">>> [SYSTEM] Creating Default Admin (100 Year License)...")
            # Set expiry to 100 years from now to prevent immediate lockout
            expiry = datetime.utcnow() + timedelta(days=36500)

            admin = User(username='admin', role='ADMIN', active=True, expires_at=expiry)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print(">>> [SYSTEM] Admin Created. Login: admin / admin123")

    pinger = PingWorker(app, socketio)
    pinger.start()


    def run_server():
        # Using a new port to avoid any cached conflicts
        socketio.run(app, port=5050, debug=False, use_reloader=False)


    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    time.sleep(1)

    webview.create_window(
        title="RTM Monitor Pro",
        url="http://127.0.0.1:5050",  # Port matched above
        width=1280,
        height=800,
        background_color='#0f172a'
    )

    webview.start()
    pinger.stop_event.set()
    sys.exit()