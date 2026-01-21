from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user, login_user, logout_user
from core.database import db, User, Device
from core.security import SecurityManager
import datetime

bp = Blueprint('main', __name__, template_folder='templates')


@bp.context_processor
def inject_now():
    return {'now': datetime.datetime.now()}


@bp.before_request
def check_access():
    allowed = ['main.login', 'main.logout', 'static']
    if request.path.startswith('/static'): return
    if request.endpoint in allowed: return
    if current_user.is_authenticated:
        if current_user.username == 'superadmin':
            if request.endpoint != 'main.setup': return redirect(url_for('main.setup'))
        elif request.endpoint == 'main.setup':
            return redirect(url_for('main.dashboard'))
        else:
            valid, msg = SecurityManager.verify_license(current_user)
            if not valid:
                flash(msg, "danger")
                if request.endpoint != 'main.login': return redirect(url_for('main.login'))


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.username == 'superadmin': return redirect(url_for('main.setup'))
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        user = User.query.filter_by(username=u).first()

        if user:
            if not user.active and user.username != 'superadmin':
                flash("Blocked.", "danger");
                return render_template('login.html')
            if user.check_password(p):
                if user.username == 'superadmin': login_user(user); return redirect(url_for('main.setup'))
                valid, msg = SecurityManager.verify_license(user)
                if valid:
                    login_user(user); return redirect(url_for('main.dashboard'))
                else:
                    flash(msg, "danger")
            else:
                flash("Invalid Password", "danger")
        else:
            flash("User not found", "danger")
    return render_template('login.html')


@bp.route('/logout')
def logout(): logout_user(); return redirect(url_for('main.login'))


@bp.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    if current_user.username != 'superadmin': return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            u_name = request.form.get('username');
            u_pass = request.form.get('password');
            dur = request.form.get('duration')
            if not User.query.filter_by(username=u_name).first():
                exp = datetime.datetime.now() + datetime.timedelta(minutes=5 if dur == 'test_5m' else int(dur))
                hw_id = SecurityManager.get_system_id()
                seal = SecurityManager.generate_license_hash(exp.strftime('%Y-%m-%d'), hw_id)
                u = User(username=u_name, role='ADMIN', expires_at=exp, license_hash=seal, active=True)
                u.set_password(u_pass);
                db.session.add(u);
                db.session.commit();
                flash("Created!", "success")
        elif action == 'renew':
            u = User.query.get(request.form.get('user_id'))
            if u:
                u.expires_at = datetime.datetime.now() + datetime.timedelta(days=365)
                u.license_hash = SecurityManager.generate_license_hash(u.expires_at.strftime('%Y-%m-%d'),
                                                                       SecurityManager.get_system_id())
                u.active = True;
                db.session.commit();
                flash("Renewed!", "success")
        elif action == 'toggle_block':
            u = User.query.get(request.form.get('user_id'))
            if u: u.active = not u.active; db.session.commit(); flash("Status Changed", "info")
        elif action == 'delete':
            u = User.query.get(request.form.get('user_id'))
            if u: db.session.delete(u); db.session.commit(); flash("Deleted", "warning")

    users = User.query.filter(User.username != 'superadmin').all()
    return render_template('setup.html', users=users)


@bp.route('/dashboard')
@login_required
def dashboard():
    up = Device.query.filter_by(state="UP").count()
    down = Device.query.filter_by(state="DOWN").count()
    devices = Device.query.all()
    return render_template('dashboard.html', up=up, down=down, total=len(devices), devices=devices)


# --- TOPOLOGY API ---
@bp.route('/api/topology')
@login_required
def api_topology():
    devices = Device.query.all()
    nodes = [{"id": 0, "label": "INTERNET", "shape": "cloud", "color": "#00fff2", "size": 30}]
    edges = []
    for d in devices:
        color = "#2ecc71" if d.state == "UP" else "#ff4757"
        nodes.append({"id": d.id, "label": f"{d.name}\n{d.ip}", "shape": "dot", "color": color})
        edges.append({"from": 0, "to": d.id, "color": "#005555"})
    return jsonify({"nodes": nodes, "edges": edges})


@bp.route('/devices')
@login_required
def devices(): return render_template('devices.html', devices=Device.query.all())


@bp.route('/devices/add', methods=['POST'])
@login_required
def devices_add():
    if not Device.query.filter_by(ip=request.form.get('ip')).first():
        db.session.add(Device(ip=request.form.get('ip'), name=request.form.get('name'),
                              device_type=request.form.get('device_type')))
        db.session.commit();
        flash("Added", "success")
    return redirect(url_for('main.devices'))


@bp.route('/devices/<int:id>/delete', methods=['POST'])
@login_required
def device_delete(id):
    d = Device.query.get(id)
    if d: db.session.delete(d); db.session.commit()
    return redirect(url_for('main.devices'))


@bp.route('/terminal')
@login_required
def terminal(): return render_template('terminal.html', ip="127.0.0.1")


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST': flash("Saved", "success")
    return render_template('settings.html')


@bp.route('/backup/download')
@login_required
def backup_download(): return jsonify({"status": "success"})