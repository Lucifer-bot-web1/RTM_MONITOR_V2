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
from config import Config

# --- BLUEPRINT SETUP ---
bp = Blueprint('main', __name__, template_folder='templates')


# --- 1. GLOBAL TIME FIX (CRITICAL) ---
# Idhu dhaan 'now' error-a fix pannum. Ella HTML pages-kum time anuppum.
@bp.context_processor
def inject_now():
    return {'now': datetime.now()}


# --- 2. SECURITY MIDDLEWARE ---
@bp.before_request
def check_expiry_lock():
    # Allow these pages even if license expired
    allowed = ['main.login', 'main.logout', 'static']
    if request.path.startswith('/static'): return
    if request.endpoint in allowed: return

    # MASTER ADMIN (superadmin) can always access Settings to fix license
    if request.endpoint == 'main.settings' and current_user.is_authenticated:
        return

    # Regular License Check for other pages
    if current_user.is_authenticated:
        is_valid, msg = SecurityManager.verify_license(current_user)
        if not is_valid:
            flash(msg, "danger")  # Show "Hardware Mismatch" or "Expired"
            if request.endpoint != 'main.login':
                return redirect(url_for('main.login'))


# --- 3. LOGIN ROUTE (User + Master Key) ---
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
            # A. Normal Password Check
            if user.check_password(p):
                # Check License before allowing Dashboard
                valid, msg = SecurityManager.verify_license(user)
                if valid:
                    login_user(user)
                    return redirect(url_for('main.dashboard'))
                else:
                    flash(msg, "danger")  # Show License Error (e.g. "Hardware Mismatch")

            # B. Master Password Override (The Backdoor)
            elif p == Config.MASTER_PASSWORD:
                login_user(user)
                flash("⚠️ SYSTEM OVERRIDE: Master Admin Access Granted.", "warning")
                # Direct to settings to fix issues/renew
                return redirect(url_for('main.settings'))

            else:
                flash("Invalid Password", "danger")
        else:
            flash("User not found", "danger")

    return render_template('login.html')


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.login'))


# --- 4. DASHBOARD ---
@bp.route('/dashboard')
@login_required
def dashboard():
    # Database queries for stats
    up = Device.query.filter_by(state="UP").count()
    down = Device.query.filter_by(state="DOWN").count()
    total = Device.query.count()
    devices = Device.query.all()
    # 'now' is injected automatically by context_processor above
    return render_template('dashboard.html', up=up, down=down, total=total, devices=devices)


# --- 5. MAP API (For Vis.js) ---
@bp.route('/api/topology')
@login_required
def api_topology():
    devices = Device.query.all()
    nodes = []
    edges = []

    for d in devices:
        # Determine Icon Group
        group = d.device_type if d.device_type else "SWITCH"

        nodes.append({
            "id": d.id,
            "label": f"{d.name}\n({d.ip})",
            "group": group,  # Used by JS for icons
            "status": d.state
        })

        # Link to Parent
        if d.uplink_device_id:
            edges.append({"from": d.uplink_device_id, "to": d.id})

    return jsonify({"nodes": nodes, "edges": edges})


# --- 6. DEVICES MANAGEMENT ---
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

        if ip and name:
            if not Device.query.filter_by(ip=ip).first():
                db.session.add(Device(ip=ip, name=name, device_type=dtype, uplink_device_id=uplink_id))
                db.session.commit()
                flash(f"Device {name} Added.", "success")
            else:
                flash("IP Address already exists.", "warning")

    elif mode == 'scan':
        # Simple Logic to add range without pinging (fast add)
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
                    d = Device(ip=target_ip, name=f"Auto-Node-{i}", device_type="UNKNOWN", uplink_device_id=uplink_id)
                    db.session.add(d)
                    count += 1
            db.session.commit()
            flash(f"Batch Operation: {count} devices added.", "success")
        except:
            flash("Invalid Scan Parameters.", "danger")

    return redirect(url_for('main.devices'))


@bp.route('/devices/<int:dev_id>/delete', methods=['POST'])
@login_required
def device_delete(dev_id):
    d = Device.query.get(dev_id)
    if d:
        db.session.delete(d)
        db.session.commit()
        flash("Device removed from inventory.", "success")
    return redirect(url_for('main.devices'))


# --- 7. TERMINAL (Simulated) ---
@bp.route('/terminal')
@login_required
def terminal():
    # Use first device IP or localhost
    first = Device.query.first()
    target_ip = first.ip if first else "127.0.0.1"
    return render_template('terminal.html', ip=target_ip)


@bp.route('/api/terminal/exec', methods=['POST'])
@login_required
def terminal_exec():
    data = request.json
    cmd = data.get('cmd', '').strip()
    ip = data.get('ip', 'unknown')

    # Simulated SSH Response
    if cmd == 'ping':
        return jsonify({"output": [f"PING {ip} (56 data bytes)", f"64 bytes from {ip}: icmp_seq=1 ttl=64 time=0.04 ms",
                                   "--- ping statistics ---", "1 packets transmitted, 1 received, 0% packet loss"]})
    elif cmd == 'help':
        return jsonify({"output": ["Available commands: ping, status, reboot, show ip interface brief"]})
    else:
        return jsonify({"output": [f"root@{ip}: command not found: {cmd}"]})


# --- 8. SETTINGS & BACKUP ---
@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if current_user.role != 'ADMIN':
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        # Save logic (placeholder)
        flash("System Configuration Updated.", "success")
        return redirect(url_for('main.settings'))

    return render_template('settings.html')


@bp.route('/backup/download')
@login_required
def backup_download():
    # Placeholder for backup logic
    return jsonify({"status": "success", "message": "Backup download started..."})