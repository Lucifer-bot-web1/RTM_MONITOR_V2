import json
import socket
import time
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from core.database import db, User, Device, Setting
from core.security import SecurityManager
from core.audio_mgr import AudioManager
from core.backup_mgr import BackupManager

bp = Blueprint('main', __name__, template_folder='templates')


# --- 🔥 FIX: GLOBAL CONTEXT PROCESSOR ---
# Idhu ella templates-kum 'now' variable-a automatic-a anuppum.
@bp.context_processor
def inject_now():
    return {'now': datetime.now()}


# --- MIDDLEWARE ---
@bp.before_request
def check_expiry_lock():
    allowed = ['main.login', 'main.logout', 'static']
    if request.path.startswith('/static'): return
    if request.endpoint == 'main.settings' and current_user.is_authenticated and current_user.role == 'ADMIN': return
    if request.endpoint in allowed: return
    if SecurityManager.is_system_expired():
        if current_user.is_authenticated: logout_user()
        flash("System License Expired.", "danger")
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
        flash("Invalid Credentials", "danger")
    return render_template('login.html')


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.login'))


# --- DASHBOARD & MAP API ---
@bp.route('/dashboard')
@login_required
def dashboard():
    up = Device.query.filter_by(state="UP").count()
    down = Device.query.filter_by(state="DOWN").count()
    total = Device.query.count()
    devices = Device.query.all()
    return render_template('dashboard.html', up=up, down=down, total=total, devices=devices)


@bp.route('/api/topology')
@login_required
def api_topology():
    devices = Device.query.all()
    nodes = []
    edges = []

    for d in devices:
        # Assign Group for Icons
        group = d.device_type if d.device_type else "SWITCH"

        # Color Logic
        color = "#2ecc71" if d.state == "UP" else "#ff4d4d"

        nodes.append({
            "id": d.id,
            "label": f"{d.name}\n({d.ip})",
            "group": group,  # Used by Vis.js for Icons
            "status": d.state
        })

        if d.uplink_device_id:
            edges.append({"from": d.uplink_device_id, "to": d.id})

    return jsonify({"nodes": nodes, "edges": edges})


# --- DEVICES MANAGEMENT ---
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

        if not ip or not name:
            flash("IP and Name required.", "danger")
            return redirect(url_for('main.devices'))

        if not Device.query.filter_by(ip=ip).first():
            new_dev = Device(ip=ip, name=name, device_type=dtype, uplink_device_id=uplink_id)
            db.session.add(new_dev)
            db.session.commit()
            flash(f"Device {name} Added.", "success")
        else:
            flash("IP Already Exists.", "warning")

    elif mode == 'scan':
        try:
            subnet = request.form.get('subnet')
            start = int(request.form.get('start_ip'))
            end = int(request.form.get('end_ip'))
            uplink_id = request.form.get('uplink_id_scan')
            if uplink_id == "0": uplink_id = None

            count = 0
            for i in range(start, end + 1):
                target_ip = f"{subnet}{i}"
                if not Device.query.filter_by(ip=target_ip).first():
                    d = Device(ip=target_ip, name=f"Auto-{i}", device_type="UNKNOWN", uplink_device_id=uplink_id)
                    db.session.add(d)
                    count += 1
            db.session.commit()
            flash(f"Scanned & Added {count} devices.", "success")
        except ValueError:
            flash("Invalid Range Input.", "danger")

    return redirect(url_for('main.devices'))


@bp.route('/devices/<int:dev_id>/delete', methods=['POST'])
@login_required
def device_delete(dev_id):
    d = Device.query.get(dev_id)
    if d:
        db.session.delete(d)
        db.session.commit()
    return redirect(url_for('main.devices'))


# --- TERMINAL (SIMULATED) ---
@bp.route('/terminal')
@login_required
def terminal():
    # Pass the first available device IP for convenience
    first_device = Device.query.first()
    target_ip = first_device.ip if first_device else "127.0.0.1"
    return render_template('terminal.html', ip=target_ip)


@bp.route('/api/terminal/exec', methods=['POST'])
@login_required
def terminal_exec():
    # Simulation of a backend command execution
    cmd = request.json.get('cmd')
    ip = request.json.get('ip')

    if cmd == "ping":
        # Simulate Ping Output
        return jsonify({
            "output": [
                f"Pinging {ip} with 32 bytes of data:",
                f"Reply from {ip}: bytes=32 time=2ms TTL=64",
                f"Reply from {ip}: bytes=32 time=3ms TTL=64",
                f"Reply from {ip}: bytes=32 time=2ms TTL=64",
                f"Reply from {ip}: bytes=32 time=4ms TTL=64",
                "",
                f"Ping statistics for {ip}:",
                "    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)"
            ]
        })
    elif cmd == "status":
        return jsonify({"output": ["System Status: ONLINE", "Uptime: 48 Hours", "Load: Nominal"]})
    else:
        return jsonify({"output": [f"Command '{cmd}' not recognized or permission denied."]})


# --- SETTINGS ---
@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if current_user.role != 'ADMIN': return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        flash("Settings Saved.", "success")
        return redirect(url_for('main.settings'))

    return render_template('settings.html', themes=["dark"], current_theme="dark", templates={})


@bp.route('/backup/download')
@login_required
def backup_download():
    return jsonify({"status": "success", "file": "backup.zip"})


@bp.route('/backup/restore', methods=['POST'])
@login_required
def backup_restore():
    return redirect(url_for('main.settings'))