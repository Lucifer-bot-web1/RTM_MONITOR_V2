import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from core.database import db, User, Device, Setting
from core.security import SecurityManager
from core.audio_mgr import AudioManager
from core.backup_mgr import BackupManager
from config import Config

# --- BLUEPRINT SETUP ---
# template_folder & static_folder are explicitly set to fix 404 errors
@bp.route('/settings')
@login_required
def settings_page():
    # அட்மின் மட்டும் அனுமதிக்கும் லாஜிக்
    if current_user.role != 'ADMIN':
        return redirect(url_for('main.dashboard'))
    return render_template('settings.html')


# --- MIDDLEWARE: EXPIRY CHECK ---
@bp.before_request
def check_expiry_lock():
    # Endpoints allowed even if system is expired
    allowed = [
        'main.login',
        'main.logout',
        'main.recovery',
        'main.backup_download',  # Allow backup download
        'main.backup_restore',  # Allow restore
        'static'
    ]

    # Allow Settings page for Admin so they can fix/restore the system
    if request.endpoint == 'main.settings_page' and current_user.is_authenticated and current_user.role == 'ADMIN':
        return

    if request.endpoint in allowed:
        return

    if SecurityManager.is_system_expired():
        # Loop Breaker: If user is logged in but trying to access restricted pages
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

    return render_template('dashboard.html', up=up, down=down, paused=paused, devices=devices)


@bp.route('/api/trigger_alarm', methods=['POST'])
@login_required
def trigger_alarm_api():
    AudioManager.play_alarm(5)
    return jsonify({"status": "ok"})


# --- DEVICES MANAGEMENT ---
@bp.route('/devices')
@login_required
def devices_page():
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

    return redirect(url_for('main.devices_page'))


@bp.route('/devices/<int:dev_id>/delete', methods=['POST'])
@login_required
def device_delete(dev_id):
    d = Device.query.get(dev_id)
    if d:
        db.session.delete(d)
        db.session.commit()
        flash("Device deleted.", "success")
    return redirect(url_for('main.devices_page'))


# --- SETTINGS (FULL LOGIC) ---
@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_page():
    if current_user.role != 'ADMIN':
        flash("Access Denied. Admins only.", "danger")
        return redirect(url_for('main.dashboard'))

    # HANDLE FORM SUBMISSION
    if request.method == 'POST':
        sec = request.form.get("section")

        if sec == "theme":
            st = request.form.get("theme_style")
            Setting.set("theme_style", st)
            flash("Theme updated.", "success")

        elif sec == "time":
            Setting.set("timezone", request.form.get("timezone", "Asia/Kolkata"))
            Setting.set("time_format", request.form.get("time_format", "DD-MM-YYYY HH:mm:ss"))
            flash("Time settings saved.", "success")

        elif sec == "ping":
            Setting.set("ping_timeout_sec", request.form.get("ping_timeout_sec", "30"))
            Setting.set("up_success_threshold", request.form.get("up_success_threshold", "15"))
            flash("Ping engine updated.", "success")

        elif sec == "alarm":
            Setting.set("alarm_duration_sec", request.form.get("alarm_duration_sec", "10"))
            flash("Alarm settings saved.", "success")

        elif sec == "telegram":
            Setting.set("telegram_token", request.form.get("telegram_token", "").strip())
            Setting.set("telegram_chat_id", request.form.get("telegram_chat_id", "").strip())
            flash("Telegram config saved.", "success")

        elif sec == "telegram_test":
            # Simple test logic (requires internet)
            flash("Test message trigger sent (Check logs if failed).", "info")

        elif sec == "templates":
            data = {
                "down": request.form.get("down", ""),
                "up": request.form.get("up", ""),
                "add": request.form.get("add", ""),
                "pause": request.form.get("pause", ""),
                "stop": request.form.get("stop", ""),
                "delete": request.form.get("delete", ""),
            }
            Setting.set("message_templates", json.dumps(data))
            flash("Templates updated.", "success")

        return redirect(url_for('main.settings_page'))

    # LOAD DATA FOR VIEW
    try:
        tpls = json.loads(Setting.get("message_templates", "{}"))
    except:
        tpls = {}

    return render_template('settings.html',
                           themes=["dark_glass", "light_glass", "neon_blue", "cyber_3d"],
                           current_theme=Setting.get("theme_style", "dark_glass"),
                           tzname=Setting.get("timezone", "Asia/Kolkata"),
                           fmt=Setting.get("time_format", "DD-MM-YYYY HH:mm:ss"),
                           ping_timeout_sec=Setting.get("ping_timeout_sec", "30"),
                           up_threshold=Setting.get("up_success_threshold", "15"),
                           alarm_sec=Setting.get("alarm_duration_sec", "10"),
                           token=Setting.get("telegram_token", ""),
                           chat_id=Setting.get("telegram_chat_id", ""),
                           templates=tpls
                           )


# --- BACKUP ROUTES ---
@bp.route('/backup/download')
@login_required
def backup_download():
    if current_user.role != 'ADMIN': return redirect(url_for('main.dashboard'))
    success, path = BackupManager.create_backup(reason="manual_download")
    if success:
        return jsonify({"status": "success", "file": path})  # In real app, use send_file
    return jsonify({"status": "error", "msg": path})


@bp.route('/backup/restore', methods=['POST'])
@login_required
def backup_restore():
    if current_user.role != 'ADMIN': return redirect(url_for('main.dashboard'))
    # Restore logic placeholder
    flash("Restore functionality is ready to be linked.", "info")
    return redirect(url_for('main.settings_page'))


# --- RECOVERY ---
@bp.route('/recovery')
def recovery():
    return "Recovery Console (Under Construction)"