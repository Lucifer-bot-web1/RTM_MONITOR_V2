import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from core.database import db, User, Device, Setting
from core.security import SecurityManager
from core.audio_mgr import AudioManager
from core.backup_mgr import BackupManager

# BLUEPRINT SETUP (Static folder correctly linked)
bp = Blueprint('main', __name__, template_folder='templates', static_folder='static')

# --- MIDDLEWARE ---
@bp.before_request
def check_expiry_lock():
    allowed = ['main.login', 'main.logout', 'main.recovery', 'main.static']
    if request.endpoint == 'main.settings' and current_user.is_authenticated and current_user.role == 'ADMIN': return
    if request.endpoint in allowed: return
    if SecurityManager.is_system_expired():
        if current_user.is_authenticated: logout_user()
        return redirect(url_for('main.login'))

# --- AUTH ROUTES ---
@bp.route('/', methods=['GET', 'POST'])
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        user = User.query.filter_by(username=u).first()
        if user and user.check_password(p):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash("Invalid Username or Password", "danger")
    return render_template('login.html')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.login'))

# --- DASHBOARD ---
@bp.route('/dashboard')
@login_required
def dashboard():
    up = Device.query.filter_by(state="UP").count()
    down = Device.query.filter_by(state="DOWN").count()
    paused = Device.query.filter_by(is_paused=True).count()
    devices = Device.query.all()
    # Fixed: Added 'now' for the clock
    return render_template('dashboard.html', up=up, down=down, paused=paused, devices=devices, now=datetime.now())

# --- DEVICES (Fixed: Renamed function to match HTML) ---
@bp.route('/devices')
@login_required
def devices():
    devices = Device.query.all()
    return render_template('devices.html', devices=devices)

@bp.route('/devices/add', methods=['POST'])
@login_required
def devices_add():
    ip = request.form.get('ip')
    name = request.form.get('name')
    dtype = request.form.get('device_type', 'SWITCH')
    if ip and name:
        if not Device.query.filter_by(ip=ip).first():
            db.session.add(Device(ip=ip, name=name, device_type=dtype))
            db.session.commit()
    return redirect(url_for('main.devices'))

@bp.route('/devices/<int:dev_id>/delete', methods=['POST'])
@login_required
def device_delete(dev_id):
    d = Device.query.get(dev_id)
    if d:
        db.session.delete(d)
        db.session.commit()
    return redirect(url_for('main.devices'))

# --- TERMINAL ---
@bp.route('/terminal')
@login_required
def terminal():
    return render_template('terminal.html', ip="Select Device")

# --- SETTINGS ---
@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if current_user.role != 'ADMIN': return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        flash("Settings Saved (Demo).", "success")
        return redirect(url_for('main.settings'))
    return render_template('settings.html', themes=["dark_glass"], current_theme="dark_glass", templates={})

# --- BACKUP ---
@bp.route('/backup/download')
@login_required
def backup_download():
    return jsonify({"status": "success", "file": "backup.zip"})

@bp.route('/backup/restore', methods=['POST'])
@login_required
def backup_restore():
    return redirect(url_for('main.settings'))

# --- API ---
@bp.route('/api/trigger_alarm', methods=['POST'])
@login_required
def trigger_alarm_api():
    AudioManager.play_alarm(5)
    return jsonify({"status": "ok"})

# --- RECOVERY (Fixed: Added Missing Route) ---
@bp.route('/recovery')
def recovery():
    return "<h1>Recovery Mode</h1><a href='/login'>Back</a>"