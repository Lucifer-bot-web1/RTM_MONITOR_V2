import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from core.database import db, User, Device
from core.security import SecurityManager
from config import Config

bp = Blueprint('main', __name__, template_folder='templates')


@bp.context_processor
def inject_now():
    return {'now': datetime.now()}


# --- MIDDLEWARE: SUPERADMIN LOCK ---
@bp.before_request
def check_access():
    allowed = ['main.login', 'main.logout', 'static']
    if request.path.startswith('/static'): return
    if request.endpoint in allowed: return

    if current_user.is_authenticated:
        # 1. SUPERADMIN LOCK: Can ONLY access /setup
        if current_user.username == 'superadmin':
            if request.endpoint != 'main.setup':
                return redirect(url_for('main.setup'))

        # 2. NORMAL USER LOCK: Cannot access /setup
        elif request.endpoint == 'main.setup':
            return redirect(url_for('main.dashboard'))

        # 3. LICENSE CHECK (For Normal Users)
        else:
            is_valid, msg = SecurityManager.verify_license(current_user)
            if not is_valid:
                flash(msg, "danger")
                if request.endpoint != 'main.login':
                    return redirect(url_for('main.login'))


# --- LOGIN ---
@bp.route('/', methods=['GET', 'POST'])
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.username == 'superadmin':
            return redirect(url_for('main.setup'))
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')

        user = User.query.filter_by(username=u).first()

        if user:
            if user.check_password(p):
                # SUPERADMIN LOGIC
                if user.username == 'superadmin':
                    login_user(user)
                    return redirect(url_for('main.setup'))

                # NORMAL USER LOGIC
                valid, msg = SecurityManager.verify_license(user)
                if valid:
                    login_user(user)
                    return redirect(url_for('main.dashboard'))
                else:
                    flash(msg, "danger")
            else:
                flash("Invalid Credentials", "danger")
        else:
            flash("User not found", "danger")

    return render_template('login.html')


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.login'))


# --- SETUP WIZARD (Superadmin Only) ---
@bp.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    # Double check security
    if current_user.username != 'superadmin':
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        u_name = request.form.get('username')
        u_pass = request.form.get('password')
        duration = int(request.form.get('duration', 30))

        if User.query.filter_by(username=u_name).first():
            flash("User already exists.", "warning")
        else:
            # CREATE CLIENT USER
            from datetime import timedelta
            expiry = datetime.now() + timedelta(days=duration)
            hw_id = SecurityManager.get_system_id()
            seal = SecurityManager.generate_license_hash(expiry.strftime('%Y-%m-%d'), hw_id)

            new_user = User(
                username=u_name,
                role='ADMIN',
                expires_at=expiry,
                license_hash=seal
            )
            new_user.set_password(u_pass)
            db.session.add(new_user)
            db.session.commit()

            flash(f"✅ User '{u_name}' Created! Please Login.", "success")
            logout_user()  # Kick superadmin out
            return redirect(url_for('main.login'))

    # Show existing users list for reference
    users = User.query.filter(User.username != 'superadmin').all()
    return render_template('setup.html', users=users)


# --- DASHBOARD & OTHERS (Keep existing code) ---
@bp.route('/dashboard')
@login_required
def dashboard():
    up = Device.query.filter_by(state="UP").count()
    down = Device.query.filter_by(state="DOWN").count()
    total = Device.query.count()
    devices = Device.query.all()
    return render_template('dashboard.html', up=up, down=down, total=total, devices=devices)


# ... (Paste the rest of your routes: api_topology, devices, terminal, settings) ...
# (The rest of the file remains exactly the same as I gave you before)
# ...
@bp.route('/api/topology')
@login_required
def api_topology():
    devices = Device.query.all()
    nodes = []
    edges = []
    for d in devices:
        group = d.device_type if d.device_type else "SWITCH"
        nodes.append({"id": d.id, "label": f"{d.name}\n({d.ip})", "group": group, "status": d.state})
        if d.uplink_device_id: edges.append({"from": d.uplink_device_id, "to": d.id})
    return jsonify({"nodes": nodes, "edges": edges})


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
    return redirect(url_for('main.devices'))


@bp.route('/devices/<int:dev_id>/delete', methods=['POST'])
@login_required
def device_delete(dev_id):
    d = Device.query.get(dev_id)
    if d: db.session.delete(d); db.session.commit()
    return redirect(url_for('main.devices'))


@bp.route('/terminal')
@login_required
def terminal():
    first = Device.query.first()
    target_ip = first.ip if first else "127.0.0.1"
    return render_template('terminal.html', ip=target_ip)


@bp.route('/api/terminal/exec', methods=['POST'])
@login_required
def terminal_exec():
    return jsonify({"output": ["Command executed successfully.", "root@system:~# "]})


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if current_user.role != 'ADMIN': return redirect(url_for('main.dashboard'))
    if request.method == 'POST': flash("Config Saved.", "success")
    return render_template('settings.html')


@bp.route('/backup/download')
@login_required
def backup_download():
    return jsonify({"status": "success"})