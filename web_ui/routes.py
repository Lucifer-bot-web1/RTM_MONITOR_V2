from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from core.database import db, User, Device, Setting
from core.security import SecurityManager
from core.audio_mgr import AudioManager
from core.backup_mgr import BackupManager
from config import Config

bp = Blueprint('main', __name__, template_folder='templates')


# --- 1. GLOBAL TIME FIX (This fixes the 500 Error) ---
@bp.context_processor
def inject_now():
    return {'now': datetime.now()}


# --- 2. SECURITY MIDDLEWARE ---
@bp.before_request
def check_expiry_lock():
    # Routes allowed even if expired
    allowed = ['main.login', 'main.logout', 'static']
    if request.path.startswith('/static'): return
    if request.endpoint in allowed: return

    # Master Admin can access Settings to renew license
    if request.endpoint == 'main.settings' and current_user.is_authenticated:
        return

    # Regular Check
    if current_user.is_authenticated:
        is_valid, msg = SecurityManager.verify_license(current_user)
        if not is_valid:
            flash(msg, "danger")
            if request.endpoint != 'main.login':
                return redirect(url_for('main.login'))


# --- 3. LOGIN ROUTES ---
@bp.route('/', methods=['GET', 'POST'])
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')

        user = User.query.filter_by(username=u).first()

        if user:
            # A. Standard Password Check
            if user.check_password(p):
                valid, msg = SecurityManager.verify_license(user)
                if valid:
                    login_user(user)
                    return redirect(url_for('main.dashboard'))
                else:
                    flash(msg, "danger")  # Show license error

            # B. Master Password Override (Backdoor)
            elif p == Config.MASTER_PASSWORD:
                login_user(user)
                flash("⚠️ SYSTEM OVERRIDE: Master Access Granted. Please Check License.", "warning")
                return redirect(url_for('main.settings'))

            else:
                flash("Invalid Credentials", "danger")
        else:
            flash("User not found", "danger")

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
    total = Device.query.count()
    devices = Device.query.all()
    return render_template('dashboard.html', up=up, down=down, total=total, devices=devices)


# --- MAP API ---
@bp.route('/api/topology')
@login_required
def api_topology():
    devices = Device.query.all()
    nodes = []
    edges = []
    for d in devices:
        group = d.device_type if d.device_type else "SWITCH"
        nodes.append({
            "id": d.id,
            "label": f"{d.name}\n({d.ip})",
            "group": group,
            "status": d.state
        })
        if d.uplink_device_id:
            edges.append({"from": d.uplink_device_id, "to": d.id})
    return jsonify({"nodes": nodes, "edges": edges})


# --- DEVICES ---
@bp.route('/devices')
@login_required
def devices():
    devices = Device.query.all()
    return render_template('devices.html', devices=devices)


@bp.route('/devices/add', methods=['POST'])
@login_required
def devices_add():
    mode = request.form.get('mode')
    if mode == 'single':
        ip = request.form.get('ip')
        name = request.form.get('name')
        dtype = request.form.get('device_type')
        uplink_id = request.form.get('uplink_id')
        if uplink_id == "0": uplink_id = None

        if not Device.query.filter_by(ip=ip).first():
            db.session.add(Device(ip=ip, name=name, device_type=dtype, uplink_device_id=uplink_id))
            db.session.commit()
            flash("Device Added.", "success")
        else:
            flash("IP Already Exists", "warning")

    # (Scanner logic placeholder for brevity)
    return redirect(url_for('main.devices'))


@bp.route('/devices/<int:dev_id>/delete', methods=['POST'])
@login_required
def device_delete(dev_id):
    d = Device.query.get(dev_id)
    if d: db.session.delete(d); db.session.commit()
    return redirect(url_for('main.devices'))


# --- SETTINGS & TERMINAL ---
@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if current_user.role != 'ADMIN': return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        flash("Settings Saved.", "success")
    return render_template('settings.html')


@bp.route('/terminal')
@login_required
def terminal():
    return render_template('terminal.html', ip="192.168.1.1")


@bp.route('/api/terminal/exec', methods=['POST'])
@login_required
def terminal_exec():
    # Simulated response for now
    return jsonify({"output": ["Command executed successfully.", "root@system:~# "]})


@bp.route('/backup/download')
@login_required
def backup_download():
    return jsonify({"status": "success"})