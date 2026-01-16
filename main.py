import sys
import threading
import time
import webview  # pip install pywebview
from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO

# Import Custom Modules
from config import Config
from core.database import db, User
from network.pinger import PingWorker
from web_ui.routes import bp as main_bp


# --- APP FACTORY ---
def create_app():
    """
    Initializes the Flask Application, Database, and Login Manager.
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Plugins
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    @login_manager.user_loader
    def load_user(uid):
        return User.query.get(int(uid))

    # Register Blueprint (The UI Routes)
    app.register_blueprint(main_bp)

    return app


# --- MAIN EXECUTION ---
if __name__ == '__main__':
    # 1. Create App Instance
    app = create_app()
    socketio = SocketIO(app, async_mode="threading")

    # 2. Database & Default Admin Setup
    with app.app_context():
        try:
            db.create_all()  # Create tables if they don't exist

            # --- AUTO-CREATE DEFAULT ADMIN ---
            # Checks if an admin exists. If not, creates one.
            if not User.query.filter_by(username='admin').first():
                print(">>> [SYSTEM] Initializing Default Admin Account...")
                default_admin = User(
                    username='admin',
                    role='ADMIN',
                    active=True,
                    contact_info='{"name": "System Admin", "phone": "0000000000"}'
                )
                default_admin.set_password('admin123')
                db.session.add(default_admin)
                db.session.commit()
                print(">>> [SYSTEM] Admin Created! Login: admin / admin123")
            else:
                print(">>> [SYSTEM] Admin account found.")

        except Exception as e:
            print(f">>> [ERROR] Database Init Failed: {e}")

    # 3. Start Ping Engine (Background Worker)
    # Passing 'app' so it can access the Database context
    pinger = PingWorker(app, socketio)
    pinger.start()


    # 4. Run Flask Server in a Separate Thread
    # We use a random port (e.g., 54321) to avoid conflicts
    def run_server():
        socketio.run(app, port=54321, debug=False, use_reloader=False)


    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Wait a moment for server to spin up
    time.sleep(1)

    # 5. Launch Desktop GUI (The "Glass" Interface)
    print(">>> [SYSTEM] Launching Interface...")

    webview.create_window(
        title="RTM Monitor Pro",
        url="http://127.0.0.1:54321",
        width=1280,
        height=800,
        resizable=True,
        background_color='#0f172a',  # Matches dark theme background
        text_select=False
    )

    # This blocks until the window is closed
    webview.start()

    # 6. Cleanup on Exit
    print(">>> [SYSTEM] Shutting down...")
    pinger.stop_event.set()
    sys.exit()