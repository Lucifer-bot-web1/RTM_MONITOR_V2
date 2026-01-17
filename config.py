import os
import sys


class Config:
    """
    Central Configuration.
    Handles 'AppData' logic so database persists after updates.
    """
    APP_NAME = "RTM_ENTERPRISE_SERVER"

    # --- 1. PATH SYSTEM (Prod vs Dev) ---
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe (Install Mode)
        # Data will be stored in C:\Users\You\AppData\Roaming\RTM_ENTERPRISE_SERVER
        BASE_DIR = os.path.dirname(sys.executable)
        DATA_DIR = os.path.join(os.getenv('APPDATA'), APP_NAME)
    else:
        # Running as python script (Dev Mode)
        # Data will be stored in your project folder/data
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        DATA_DIR = os.path.join(BASE_DIR, "data")

    # --- 2. AUTO-CREATE DIRECTORIES ---
    # Database path illana adhuve create pannidum
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "backups"), exist_ok=True)

    # --- 3. FILE PATHS ---
    DB_FILE = os.path.join(DATA_DIR, "rtm_prod.sqlite3")
    BACKUP_DIR = os.path.join(DATA_DIR, "backups")

    # --- 4. FLASK & DATABASE CONFIG ---
    # Secret Key for Security Module (Updated)
    SECRET_KEY = os.environ.get("RTM_SECRET", "RTM_ENTERPRISE_J@RVIS_KEY_2026")

    # Database URI (Uses the robust DB_FILE path)
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_FILE}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- 5. APP CONSTANTS ---
    # Neenga ketta Master Password Logic inga irukku
    MASTER_PASSWORD = "Tech@admin"

    # Default Settings
    DEFAULT_PING_INTERVAL = 30
    DEFAULT_THEME = "dark_glass"