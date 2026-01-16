from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from core.database import db, User, Device
from core.security import SecurityManager
from core.audio_mgr import AudioManager
from config import Config

# FIX: Added static_folder to fix CSS 404
bp = Blueprint('main', __name__, template_folder='templates', static_folder='static', static_url_path='/static')


# --- MIDDLEWARE ---
@bp.before_request
def check_expiry_lock():
    # Allow these endpoints always
    allowed = ['main.login', 'main.logout', 'main.recovery', 'static']

    if request.endpoint in allowed:
        return

    if SecurityManager.is_system_expired():
        # FIX: If user is logged in but expired, log them out to prevent Loop
        if current_user.is_authenticated:
            logout_user()
            flash("License Expired. Session Terminated.", "danger")
        return redirect(url_for('main.login'))


# --- ROUTES ---
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


@bp.route('/dashboard')
@login_required
def dashboard():
    up = Device.query.filter_by(state="UP").count()
    down = Device.query.filter_by(state="DOWN").count()
    devices = Device.query.all()
    return render_template('dashboard.html', up=up, down=down, devices=devices)


@bp.route('/api/trigger_alarm', methods=['POST'])
def trigger_alarm_api():
    AudioManager.play_alarm(5)
    return jsonify({"status": "ok"})


# --- DEVICE ROUTES ---
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
    if ip and name:
        if not Device.query.filter_by(ip=ip).first():
            db.session.add(Device(ip=ip, name=name))
            db.session.commit()
    return redirect(url_for('main.devices_page'))


# --- RECOVERY ---
@bp.route('/recovery')
def recovery():
    return "Recovery Console (Under Construction)"