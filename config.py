import os
import sys


class Config:
    """
    Central Configuration.
    Handles 'AppData' logic so database persists after updates.
    """
    APP_NAME = "RTM_MONITOR_PRO"

    # --- PATH SYSTEM (Prod vs Dev) ---
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe
        BASE_DIR = os.path.dirname(sys.executable)
        DATA_DIR = os.path.join(os.getenv('APPDATA'), APP_NAME)
    else:
        # Running as python script
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        DATA_DIR = os.path.join(BASE_DIR, "data")

    # Create data directory if missing
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "backups"), exist_ok=True)

    # File Paths
    DB_FILE = os.path.join(DATA_DIR, "rtm_prod.sqlite3")
    BACKUP_DIR = os.path.join(DATA_DIR, "backups")

    # Flask Config
    SECRET_KEY = os.environ.get("RTM_SECRET", "change-this-secret-key-in-prod")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_FILE}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Application Constants
    MASTER_PASSWORD = "Tech@admin"
    DEFAULT_PING_INTERVAL = 30
    DEFAULT_THEME = "dark_glass"