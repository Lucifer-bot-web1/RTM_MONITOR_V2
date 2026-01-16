from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
import bcrypt

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), default="ADMIN")
    expires_at = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True)
    contact_info = db.Column(db.Text)

    def set_password(self, pw):
        self.password_hash = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, pw):
        try:
            return bcrypt.checkpw(pw.encode('utf-8'), self.password_hash.encode('utf-8'))
        except:
            return False

    def is_expired(self):
        if not self.expires_at: return False
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

# ... (Include Device, Audit, Setting classes as before)
class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    device_type = db.Column(db.String(16))
    state = db.Column(db.String(16), default="UNKNOWN")
    is_paused = db.Column(db.Boolean, default=False)
    is_stopped = db.Column(db.Boolean, default=False)