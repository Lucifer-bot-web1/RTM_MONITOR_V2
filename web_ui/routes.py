from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from datetime import datetime, timezone

# Import Core Modules
from core.database import db, User, Device, Setting
from core.security import SecurityManager
from core.audio_mgr import AudioManager
from core.backup_mgr import BackupManager
from config import Config

# Create the Blueprint
bp = Blueprint('main', __name__, template_folder='templates', static_folder='static')


# --- 1. MIDDLEWARE: SECURITY & EXPIRY CHECK ---

def is_system_locked():
    """
    Checks if the system is expired using SecurityManager.
    """
    return SecurityManager.is_system_expired()


@bp.before_request
def check_expiry_lock():
    """
    intercepts every request.
    If system is expired, BLOCKS access to Dashboard/Devices.
    ALLOWS access to Login, Logout, Static files (CSS/JS), and Recovery.
    """
    # List of endpoints allowed even when expired
    allowed_endpoints = [
        'main.login',
        'main.logout',
        'main.recovery',
        'main.recovery_action',
        'static'
    ]

    if is_system_locked():
        if request.endpoint and request.endpoint not in allowed_endpoints:
            flash("System License Expired. Please contact Administrator/Developer.", "danger")
            return redirect(url_for('main.login'))


# --- 2. AUTHENTICATION ROUTES ---

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash("Invalid Username or Password", "danger")

    return render_template('login.html')  # Note: Create login.html or use TPL string if preferred


@bp.route('/logout')
def logout():
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for('main.login'))


# --- 3. DASHBOARD & MONITORING ---

@bp.route('/dashboard')
@login_required
def dashboard():
    # Fetch Counts
    up_count = Device.query.filter_by(state="UP").count()
    down_count = Device.query.filter_by(state="DOWN").count()
    paused_count = Device.query.filter_by(is_paused=True).count()

    # Fetch All Devices for the table
    devices = Device.query.order_by(Device.name.asc()).all()

    return render_template('dashboard.html',
                           up=up_count,
                           down=down_count,
                           paused=paused_count,
                           devices=devices)


@bp.route('/api/trigger_alarm', methods=['POST'])
@login_required
def trigger_alarm_api():
    """Endpoint for frontend/testing to trigger sound"""
    data = request.get_json() or {}
    duration = data.get('duration', 5)
    AudioManager.play_alarm(duration)
    return jsonify({"status": "success", "message": "Alarm triggered"})


# --- 4. DEVICE MANAGEMENT ---

@bp.route('/devices')
@login_required
def devices_page():
    devices = Device.query.all()
    return render_template('devices.html', devices=devices)


@bp.route('/devices/add', methods=['POST'])
@login_required
def devices_add():
    ip = request.form.get('ip', '').strip()
    name = request.form.get('name', '').strip()
    dtype = request.form.get('device_type', 'switch')

    if not ip or not name:
        flash("IP and Name are required!", "danger")
        return redirect(url_for('main.devices_page'))

    # Check duplicate
    if Device.query.filter_by(ip=ip).first():
        flash("Device with this IP already exists.", "danger")
        return redirect(url_for('main.devices_page'))

    new_dev = Device(ip=ip, name=name, device_type=dtype)
    db.session.add(new_dev)
    db.session.commit()

    flash(f"Device {name} added successfully.", "success")
    return redirect(url_for('main.devices_page'))


@bp.route('/devices/<int:dev_id>/delete', methods=['POST'])
@login_required
def device_delete(dev_id):
    dev = Device.query.get_or_404(dev_id)
    name = dev.name
    db.session.delete(dev)
    db.session.commit()
    flash(f"Device {name} deleted.", "success")
    return redirect(url_for('main.devices_page'))


# --- 5. SETTINGS & RECOVERY ---

@bp.route('/settings')
@login_required
def settings_page():
    # Only Admin can access settings
    if current_user.role != 'ADMIN':
        flash("Access Denied.", "danger")
        return redirect(url_for('main.dashboard'))

    return render_template('settings.html')  # Need to create settings.html


@bp.route('/recovery', methods=['GET', 'POST'])
def recovery():
    """Developer Backdoor for Resetting Password/Expiry"""
    if request.method == 'POST':
        master_key = request.form.get('master_key')
        if master_key == Config.MASTER_PASSWORD:
            # Grant access to recovery action page or perform action
            return render_template('recovery_console.html')
        else:
            flash("Invalid Master Key", "danger")

    return render_template('recovery_login.html')  # Need to create this template if using recovery