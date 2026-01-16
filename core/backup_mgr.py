import os
import zipfile
from datetime import datetime
from config import Config

class BackupManager:
    """Handles automatic and manual backups."""

    @staticmethod
    def create_backup(reason="manual"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{reason}_{timestamp}.zip"
        filepath = os.path.join(Config.BACKUP_DIR, filename)

        try:
            with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
                if os.path.exists(Config.DB_FILE):
                    zf.write(Config.DB_FILE, arcname="db.sqlite3")
            return True, filename
        except Exception as e:
            return False, str(e)