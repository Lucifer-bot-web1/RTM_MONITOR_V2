from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import bcrypt

db = SQLAlchemy()


# --- SETTINGS ---
class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)

    @staticmethod
    def get(key, default=None):
        try:
            s = Setting.query.filter_by(key=key).first()
            return s.value if s else default
        except:
            return default

    @staticmethod
    def set(key, value):
        try:
            s = Setting.query.filter_by(key=key).first()
            if not s:
                s = Setting(key=key, value=str(value))
                db.session.add(s)
            else:
                s.value = str(value)
            db.session.commit()
        except:
            db.session.rollback()


# --- USER (LICENSE LOCKED) ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), default="ADMIN")

    # LICENSE DATA
    expires_at = db.Column(db.DateTime)
    license_hash = db.Column(db.String(128))

    active = db.Column(db.Boolean, default=True)

    def set_password(self, pw):
        self.password_hash = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, pw):
        try:
            return bcrypt.checkpw(pw.encode('utf-8'), self.password_hash.encode('utf-8'))
        except:
            return False


# --- DEVICES (FIXED CRASH) ---
class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    device_type = db.Column(db.String(16), default="SWITCH")
    uplink_device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=True)

    # --- RESTORED MISSING COLUMNS ---
    state = db.Column(db.String(16), default="UNKNOWN")
    is_paused = db.Column(db.Boolean, default=False)  # Fixed Crash
    is_stopped = db.Column(db.Boolean, default=False)  # Fixed Crash
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    children = db.relationship('Device', backref=db.backref('uplink', remote_side=[id]))