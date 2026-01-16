import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from core.database import db, User, Device, Setting
from core.security import SecurityManager
from core.audio_mgr import AudioManager
from core.backup_mgr import BackupManager

# --- 🔥 THE FIX IS HERE 🔥 ---
# static_folder='static'      -> Soludhu: "Files inga (web_ui/static) irukku"
# static_url_path='/static'   -> Soludhu: "Browser /static nu ketta, inga irundhu edu"
bp = Blueprint('main', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/static')


# --- MIDDLEWARE ---
@bp.before_request
def check_expiry_lock():
    # Allow static files (CSS/JS) to load even if expired
    allowed = ['main.login', 'main.logout', 'main.recovery']

    # FIX: Allow any request starting with /static to pass (CSS/JS loading)
    if request.path.startswith('/static'):
        return

    if request.endpoint == 'main.settings' and current_user.is_authenticated and current_user.role == 'ADMIN':
        return

    if request.endpoint in allowed:
        return

    if SecurityManager.is_system_expired():
        if current_user.is_authenticated:
            logout_user()
            flash("System License Expired. Session Terminated.", "danger")
        return redirect(url_for('main.login'))


# --- AUTH ROUTES ---
@bp.route('/', methods=['GET', 'POST'])
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

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
    # 'now' variable added for clock
    return render_template('dashboard.html', up=up, down=down, paused=paused, devices=devices, now=datetime.now())


# --- DEVICES ---
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
            flash(f"Device {name} added.", "success")
        else:
            flash("IP already exists.", "warning")
    else:
        flash("IP and Name are required.", "danger")

    return redirect(url_for('main.devices'))


@bp.route('/devices/<int:dev_id>/delete', methods=['POST'])
@login_required
def device_delete(dev_id):
    d = Device.query.get(dev_id)
    if d:
        db.session.delete(d)
        db.session.commit()
        flash("Device deleted.", "success")
    return redirect(url_for('main.devices'))


# --- TERMINAL ---
@bp.route('/terminal')
@login_required
def terminal():
    return render_template('terminal.html', ip="Select a Device")


# --- SETTINGS ---
@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if current_user.role != 'ADMIN':
        flash("Access Denied. Admins only.", "danger")
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        flash("Settings updated (Demo Mode).", "success")
        return redirect(url_for('main.settings'))

    return render_template('settings.html',
                           themes=["dark_glass", "light_glass"],
                           current_theme=Setting.get("theme_style", "dark_glass"),
                           templates={})


# --- BACKUP ---
@bp.route('/backup/download')
@login_required
def backup_download():
    if current_user.role != 'ADMIN': return redirect(url_for('main.dashboard'))
    success, path = BackupManager.create_backup(reason="manual_download")
    if success:
        return jsonify({"status": "success", "file": path})
    return jsonify({"status": "error", "msg": path})


@bp.route('/backup/restore', methods=['POST'])
@login_required
def backup_restore():
    if current_user.role != 'ADMIN': return redirect(url_for('main.dashboard'))
    flash("Restore functionality is ready.", "info")
    return redirect(url_for('main.settings'))


# --- RECOVERY ---
@bp.route('/recovery')
def recovery():
    return "<h1>Recovery Mode</h1><p>Contact Support.</p><a href='/login'>Back</a>"


# --- API ---
@bp.route('/api/trigger_alarm', methods=['POST'])
@login_required
def trigger_alarm_api():
    AudioManager.play_alarm(5)
    return jsonify({"status": "ok"})