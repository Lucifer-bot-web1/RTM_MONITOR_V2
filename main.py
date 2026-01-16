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
from network.pinger import PingWorker
from web_ui.routes import bp as main_bp


def create_app():
    # --- 🔥 THE FIX IS HERE 🔥 ---
    # static_folder='web_ui/static' -> Soludhu: Files 'web_ui/static' kulla irukku.
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
        if not User.query.filter_by(username='admin').first():
            print(">>> Creating Admin...")
            expiry = datetime.utcnow() + timedelta(days=36500)
            admin = User(username='admin', role='ADMIN', expires_at=expiry)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

    pinger = PingWorker(app, socketio)
    pinger.start()


    def run_server():
        socketio.run(app, port=5050, debug=False, use_reloader=False)


    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    time.sleep(1)

    webview.create_window(
        title="RTM Monitor Pro",
        url="http://127.0.0.1:5050",
        width=1280,
        height=800,
        background_color='#0f172a'
    )

    webview.start()
    pinger.stop_event.set()
    sys.exit()