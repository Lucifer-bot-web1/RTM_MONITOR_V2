import sys
import threading
import time
import webview
from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
from datetime import datetime, timedelta

# Import Config and DB
from config import Config
from core.database import db, User
from network.pinger import PingWorker

# Import our Routes Blueprint
from web_ui.routes import bp as main_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Database
    db.init_app(app)

    # Initialize Login Manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    @login_manager.user_loader
    def load_user(uid):
        return User.query.get(int(uid))

    # Register the Blueprint (This connects web_ui to the app)
    app.register_blueprint(main_bp)

    return app


if __name__ == '__main__':
    app = create_app()
    socketio = SocketIO(app, async_mode="threading")

    with app.app_context():
        # Create Tables
        db.create_all()

        # Create Default Admin if missing
        if not User.query.filter_by(username='admin').first():
            print(">>> [SYSTEM] Creating Default Admin (100 Year License)...")
            expiry = datetime.utcnow() + timedelta(days=36500)
            admin = User(username='admin', role='ADMIN', active=True, expires_at=expiry)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print(">>> [SYSTEM] Admin Created. Login: admin / admin123")

    # Start Ping Engine
    pinger = PingWorker(app, socketio)
    pinger.start()


    def run_server():
        # Run on port 5050 to allow webview to connect
        socketio.run(app, port=5050, debug=False, use_reloader=False)


    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    # Give server a second to start
    time.sleep(1)

    # Launch Desktop Window
    webview.create_window(
        title="RTM Monitor Pro",
        url="http://127.0.0.1:5050",
        width=1280,
        height=800,
        background_color='#0f172a'
    )

    webview.start()

    # Cleanup on close
    pinger.stop_event.set()
    sys.exit()