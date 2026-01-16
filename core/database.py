from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
from passlib.hash import bcrypt
import json

db = SQLAlchemy()


# --- UTILS ---
def get_utc_now():
    return datetime.now(timezone.utc)


# --- MODELS ---
class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)

    @staticmethod
    def get(key, default=None):
        s = Setting.query.filter_by(key=key).first()
        return s.value if s else default

    @staticmethod
    def set(key, value):
        s = Setting.query.filter_by(key=key).first()
        if not s:
            s = Setting(key=key, value=str(value))
            db.session.add(s)
        else:
            s.value = str(value)
        db.session.commit()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), default="ADMIN")
    expires_at = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True)
    contact_info = db.Column(db.Text)  # JSON stored as text

    def set_password(self, pw): self.password_hash = bcrypt.hash(pw)

    def check_password(self, pw): return bcrypt.verify(pw, self.password_hash)

    def is_expired(self):
        if not self.expires_at: return False
        return get_utc_now() > self.expires_at.replace(tzinfo=timezone.utc)


class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    device_type = db.Column(db.String(16), default="SWITCH")
    brand = db.Column(db.String(64))
    state = db.Column(db.String(16), default="UNKNOWN")  # UP, DOWN, PAUSED
    is_paused = db.Column(db.Boolean, default=False)
    is_stopped = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class Audit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ts = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.Column(db.String(64))
    action = db.Column(db.String(64))
    detail = db.Column(db.Text)

# Add Ping, Incident, Alert models similarly if needed for full logs