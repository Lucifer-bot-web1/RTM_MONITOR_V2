import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from core.database import db, User, Device
from core.security import SecurityManager
from config import Config

bp = Blueprint('main', __name__, template_folder='templates')


@bp.context_processor
def inject_now():
    return {'now': datetime.now()}


# --- MIDDLEWARE ---
@bp.before_request
def check_access():
    allowed = ['main.login', 'main.logout', 'static']
    if request.path.startswith('/static'): return
    if request.endpoint in allowed: return

    if current_user.is_authenticated:
        # SUPERADMIN LOCK
        if current_user.username == 'superadmin':
            if request.endpoint != 'main.setup':
                return redirect(url_for('main.setup'))
        # NORMAL USER LOCK
        elif request.endpoint == 'main.setup':
            return redirect(url_for('main.dashboard'))
        # LICENSE CHECK
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
            # CHECK BLOCK STATUS
            if not user.active and user.username != 'superadmin':
                flash("🚫 ACCOUNT BLOCKED. Contact Administrator.", "danger")
                return render_template('login.html')

            if user.check_password(p):
                if user.username == 'superadmin':
                    login_user(user)
                    return redirect(url_for('main.setup'))

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


# --- SETUP WIZARD (Superadmin Control Panel) ---
@bp.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    if current_user.username != 'superadmin':
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')

        # --- 1. CREATE USER ---
        if action == 'create':
            u_name = request.form.get('username')
            u_pass = request.form.get('password')
            duration_val = request.form.get('duration')

            if User.query.filter_by(username=u_name).first():
                flash("User already exists.", "warning")
            else:
                # Handle Duration (Days vs Minutes for Testing)
                if duration_val == 'test_5m':
                    expiry = datetime.now() + timedelta(minutes=5)
                else:
                    expiry = datetime.now() + timedelta(days=int(duration_val))

                hw_id = SecurityManager.get_system_id()
                seal = SecurityManager.generate_license_hash(expiry.strftime('%Y-%m-%d'), hw_id)

                new_user = User(username=u_name, role='ADMIN', expires_at=expiry, license_hash=seal, active=True)
                new_user.set_password(u_pass)
                db.session.add(new_user)
                db.session.commit()
                flash(f"✅ User '{u_name}' Created!", "success")

        # --- 2. RENEW LICENSE (Extend 1 Year) ---
        elif action == 'renew':
            user_id = request.form.get('user_id')
            user = User.query.get(user_id)
            if user:
                # Extend by 365 Days from TODAY
                new_expiry = datetime.now() + timedelta(days=365)
                hw_id = SecurityManager.get_system_id()
                new_seal = SecurityManager.generate_license_hash(new_expiry.strftime('%Y-%m-%d'), hw_id)

                user.expires_at = new_expiry
                user.license_hash = new_seal
                user.active = True  # Unblock if blocked
                db.session.commit()
                flash(f"🔄 License Renewed for {user.username} (+1 Year)", "success")

        # --- 3. BLOCK / UNBLOCK ---
        elif action == 'toggle_block':
            user_id = request.form.get('user_id')
            user = User.query.get(user_id)
            if user:
                user.active = not user.active
                db.session.commit()
                status = "Unblocked" if user.active else "Blocked"
                flash(f"User {user.username} is now {status}", "info")

        # --- 4. DELETE USER ---
        elif action == 'delete':
            user_id = request.form.get('user_id')
            user = User.query.get(user_id)
            if user:
                db.session.delete(user)
                db.session.commit()
                flash(f"🗑️ User {user.username} Deleted.", "warning")

    # List all users except superadmin
    users = User.query.filter(User.username != 'superadmin').all()
    return render_template('setup.html', users=users)


# ... (Keep existing dashboard, api, devices routes as they are) ...
# --- DASHBOARD & OTHERS (Existing Code Below) ---
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