from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import bcrypt

db = SQLAlchemy()


# --- SETTINGS TABLE ---
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


# --- USER TABLE (UPDATED) ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), default="ADMIN")

    # --- NEW LICENSE FIELDS ---
    expires_at = db.Column(db.DateTime)  # License Expiry Date
    license_hash = db.Column(db.String(128))  # The Digital Lock (Seal)

    active = db.Column(db.Boolean, default=True)

    def set_password(self, pw):
        self.password_hash = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, pw):
        try:
            return bcrypt.checkpw(pw.encode('utf-8'), self.password_hash.encode('utf-8'))
        except:
            return False


# --- DEVICE TABLE ---
class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    device_type = db.Column(db.String(16), default="SWITCH")
    uplink_device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=True)
    state = db.Column(db.String(16), default="UNKNOWN")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    children = db.relationship('Device', backref=db.backref('uplink', remote_side=[id]))