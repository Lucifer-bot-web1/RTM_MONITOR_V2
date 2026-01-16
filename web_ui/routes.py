import json
import socket
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


# --- MIDDLEWARE ---
@bp.before_request
def check_expiry_lock():
    allowed = ['main.login', 'main.logout', 'main.recovery', 'static']
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


# --- DASHBOARD & TOPOLOGY ---
@bp.route('/dashboard')
@login_required
def dashboard():
    up = Device.query.filter_by(state="UP").count()
    down = Device.query.filter_by(state="DOWN").count()
    total = Device.query.count()
    devices = Device.query.all()
    # 'now' variable added for clock
    return render_template('dashboard.html', up=up, down=down, total=total, devices=devices, now=datetime.now())


# API for Vis.js Topology Map
@bp.route('/api/topology')
@login_required
def api_topology():
    devices = Device.query.all()
    nodes = []
    edges = []

    for d in devices:
        # Node Color based on status
        color = "#10b981" if d.state == "UP" else "#ef4444"
        shape = "box" if d.device_type == "SWITCH" else "ellipse"

        nodes.append({
            "id": d.id,
            "label": f"{d.name}\n({d.ip})",
            "color": {"background": color, "border": "white"},
            "shape": shape,
            "font": {"color": "white"}
        })

        # Link to Uplink (Parent)
        if d.uplink_device_id:
            edges.append({"from": d.uplink_device_id, "to": d.id})

    return jsonify({"nodes": nodes, "edges": edges})


# --- DEVICES: SCANNER & BULK ADD ---
@bp.route('/devices')
@login_required
def devices():
    devices = Device.query.all()
    return render_template('devices.html', devices=devices)


@bp.route('/devices/add', methods=['POST'])
@login_required
def devices_add():
    mode = request.form.get('mode')  # 'single' or 'scan'

    if mode == 'single':
        ip = request.form.get('ip')
        name = request.form.get('name')
        dtype = request.form.get('device_type')
        uplink_id = request.form.get('uplink_id')

        if uplink_id == "0": uplink_id = None  # Root device

        if not Device.query.filter_by(ip=ip).first():
            new_dev = Device(ip=ip, name=name, device_type=dtype, uplink_device_id=uplink_id)
            db.session.add(new_dev)
            db.session.commit()
            flash(f"Device {name} Added.", "success")
        else:
            flash("IP Already Exists.", "warning")

    elif mode == 'scan':
        # Simple Logic: Scan a range (e.g., 192.168.1.1 to 10)
        subnet = request.form.get('subnet')  # e.g., "192.168.1."
        start = int(request.form.get('start_ip'))
        end = int(request.form.get('end_ip'))
        uplink_id = request.form.get('uplink_id_scan')
        if uplink_id == "0": uplink_id = None

        count = 0
        for i in range(start, end + 1):
            target_ip = f"{subnet}{i}"
            if not Device.query.filter_by(ip=target_ip).first():
                # Bulk add logic (In real tool, we would ping first)
                d = Device(ip=target_ip, name=f"Auto-Dev-{i}", device_type="UNKNOWN", uplink_device_id=uplink_id)
                db.session.add(d)
                count += 1

        db.session.commit()
        flash(f"Bulk Added {count} devices.", "success")

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


# --- TERMINAL (THIS WAS MISSING!) ---
@bp.route('/terminal')
@login_required
def terminal():
    return render_template('terminal.html', ip="Select a Device")


# --- SETTINGS ---
@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if current_user.role != 'ADMIN': return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        sec = request.form.get("section")
        if sec == "theme":
            Setting.set("theme_style", request.form.get("theme_style"))
        # (Add other settings saving logic here as needed)
        flash("Settings Saved.", "success")
        return redirect(url_for('main.settings'))

    return render_template('settings.html', themes=["dark", "light"], current_theme="dark", templates={})


# --- UTILS ---
@bp.route('/api/trigger_alarm', methods=['POST'])
@login_required
def trigger_alarm_api():
    AudioManager.play_alarm(5)
    return jsonify({"status": "ok"})


@bp.route('/backup/download')
@login_required
def backup_download():
    return jsonify({"status": "success", "file": "backup.zip"})


@bp.route('/backup/restore', methods=['POST'])
@login_required
def backup_restore():
    return redirect(url_for('main.settings'))


@bp.route('/recovery')
def recovery():
    return "Recovery Mode"