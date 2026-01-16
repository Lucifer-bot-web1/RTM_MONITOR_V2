import sys
import threading
import time
import socket
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import bcrypt
from pythonping import ping as py_ping

# --- CONFIGURATION ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'jarvis-top-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rtm_single.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- CSS & UI THEME (EMBEDDED) ---
# Professional Dark Theme (No external file needed)
Professional_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
:root {
    --bg-dark: #0f172a;
    --bg-card: #1e293b;
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --accent: #3b82f6;
    --success: #10b981;
    --danger: #ef4444;
}
* { margin:0; padding:0; box-sizing:border-box; font-family: 'Inter', sans-serif; }
body { background: var(--bg-dark); color: var(--text-main); height: 100vh; display: flex; overflow: hidden; }

/* Sidebar */
.sidebar { width: 250px; background: var(--bg-card); border-right: 1px solid #334155; padding: 20px; display: flex; flex-direction: column; }
.brand { font-size: 24px; font-weight: bold; color: var(--accent); margin-bottom: 40px; display: flex; align-items: center; gap: 10px; }
.nav-link { display: block; padding: 12px 15px; color: var(--text-muted); text-decoration: none; border-radius: 8px; margin-bottom: 5px; transition: 0.3s; }
.nav-link:hover, .nav-link.active { background: var(--accent); color: white; }
.nav-footer { margin-top: auto; }

/* Main Content */
.main { flex: 1; padding: 30px; overflow-y: auto; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
.page-title { font-size: 28px; font-weight: 600; }

/* Cards */
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
.card { background: var(--bg-card); padding: 20px; border-radius: 12px; border: 1px solid #334155; }
.stat-val { font-size: 36px; font-weight: bold; margin-top: 10px; }
.text-green { color: var(--success); }
.text-red { color: var(--danger); }

/* Table */
table { width: 100%; border-collapse: collapse; margin-top: 10px; }
th { text-align: left; color: var(--text-muted); padding: 15px; border-bottom: 1px solid #334155; }
td { padding: 15px; border-bottom: 1px solid #334155; vertical-align: middle; }
.badge { padding: 5px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.badge-up { background: rgba(16, 185, 129, 0.2); color: var(--success); }
.badge-down { background: rgba(239, 68, 68, 0.2); color: var(--danger); }

/* Forms */
.input-box { width: 100%; padding: 12px; background: var(--bg-dark); border: 1px solid #334155; color: white; border-radius: 8px; margin-bottom: 15px; }
.btn { padding: 12px 20px; background: var(--accent); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
.btn:hover { opacity: 0.9; }
.btn-danger { background: var(--danger); }

/* Login Center */
.login-wrap { height: 100vh; display: flex; align-items: center; justify-content: center; background: radial-gradient(circle, #1e293b 0%, #0f172a 100%); }
.login-box { width: 400px; padding: 40px; background: rgba(30, 41, 59, 0.8); border-radius: 16px; border: 1px solid #334155; backdrop-filter: blur(10px); }
</style>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
"""


# --- DATABASE MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))


class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(100))
    status = db.Column(db.String(20), default="UNKNOWN")  # UP / DOWN
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- HTML TEMPLATES (EMBEDDED) ---
TPL_BASE = f"""
<!DOCTYPE html>
<html>
<head><title>RTM Pro Monitor</title>{Professional_CSS}</head>
<body>
    <div class="sidebar">
        <div class="brand"><i class="fas fa-network-wired"></i> RTM Pro</div>
        <nav>
            <a href="/dashboard" class="nav-link"><i class="fas fa-chart-pie"></i> Dashboard</a>
            <a href="/devices" class="nav-link"><i class="fas fa-server"></i> Devices</a>
            <a href="/logout" class="nav-link" style="margin-top: 20px; color: var(--danger);"><i class="fas fa-sign-out-alt"></i> Logout</a>
        </nav>
        <div class="nav-footer" style="color:#64748b; font-size:12px;">v2.0 Single Core</div>
    </div>
    <div class="main">
        {{% with messages = get_flashed_messages() %}}
            {{% if messages %}}
                <div style="padding:10px; background:rgba(59,130,246,0.2); color:#60a5fa; border-radius:8px; margin-bottom:20px;">
                    {{{{ messages[0] }}}}
                </div>
            {{% endif %}}
        {{% endwith %}}
        {{% block content %}}{{% endblock %}}
    </div>
</body>
</html>
"""

TPL_LOGIN = f"""
<!DOCTYPE html>
<html>
<head><title>Login</title>{Professional_CSS}</head>
<body>
    <div class="login-wrap">
        <div class="login-box">
            <h2 style="text-align:center; margin-bottom:10px;">RTM ACCESS</h2>
            <p style="text-align:center; color:#94a3b8; margin-bottom:30px;">Professional Network Monitor</p>
            <form method="POST">
                <input type="text" name="username" class="input-box" placeholder="Username" required>
                <input type="password" name="password" class="input-box" placeholder="Password" required>
                <button class="btn" style="width:100%">SECURE LOGIN</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

TPL_DASHBOARD = """
{% extends "base" %}
{% block content %}
<div class="header">
    <div class="page-title">Network Overview</div>
    <a href="/scan_now" class="btn">Force Scan <i class="fas fa-sync"></i></a>
</div>

<div class="grid">
    <div class="card">
        <div style="color:var(--text-muted)">Total Devices</div>
        <div class="stat-val">{{ total }}</div>
    </div>
    <div class="card">
        <div style="color:var(--text-muted)">Online (UP)</div>
        <div class="stat-val text-green">{{ up }}</div>
    </div>
    <div class="card">
        <div style="color:var(--text-muted)">Offline (DOWN)</div>
        <div class="stat-val text-red">{{ down }}</div>
    </div>
</div>

<div class="card">
    <h3>Live Status</h3>
    <table>
        <thead>
            <tr>
                <th>Status</th>
                <th>Device Name</th>
                <th>IP Address</th>
                <th>Last Update</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
            {% for d in devices %}
            <tr>
                <td>
                    <span class="badge {% if d.status == 'UP' %}badge-up{% else %}badge-down{% endif %}">
                        {{ d.status }}
                    </span>
                </td>
                <td style="font-weight:600">{{ d.name }}</td>
                <td style="font-family:monospace; color:var(--accent)">{{ d.ip }}</td>
                <td style="color:var(--text-muted)">{{ d.last_seen.strftime('%H:%M:%S') }}</td>
                <td><a href="/delete/{{d.id}}" class="text-red"><i class="fas fa-trash"></i></a></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
"""

TPL_DEVICES = """
{% extends "base" %}
{% block content %}
<div class="header">
    <div class="page-title">Device Management</div>
</div>

<div class="card" style="max-width: 600px;">
    <h3 style="margin-bottom:20px;">Add New Device</h3>
    <form method="POST">
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
            <input type="text" name="ip" class="input-box" placeholder="IP Address (e.g., 192.168.1.1)" required>
            <input type="text" name="name" class="input-box" placeholder="Device Name (e.g., Core Switch)" required>
        </div>
        <button class="btn">Add Device</button>
    </form>
</div>
{% endblock %}
"""


# --- ROUTES ---
@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        user = User.query.filter_by(username=u).first()
        if user and user.check_password(p):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Access Denied: Invalid Credentials")
    return render_template_string(TPL_LOGIN)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    devices = Device.query.all()
    up = Device.query.filter_by(status='UP').count()
    down = Device.query.filter_by(status='DOWN').count()
    # We pass the strings into a render function that supports inheritance via dict
    return render_template_string(TPL_DASHBOARD, total=len(devices), up=up, down=down, devices=devices)


@app.route('/devices', methods=['GET', 'POST'])
@login_required
def devices():
    if request.method == 'POST':
        ip = request.form['ip']
        name = request.form['name']
        if not Device.query.filter_by(ip=ip).first():
            db.session.add(Device(ip=ip, name=name))
            db.session.commit()
            flash("Device Added Successfully")
        else:
            flash("Error: IP Already Exists")
    return render_template_string(TPL_DEVICES)


@app.route('/delete/<int:id>')
@login_required
def delete_device(id):
    d = Device.query.get(id)
    if d:
        db.session.delete(d)
        db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/scan_now')
@login_required
def scan_now():
    # Manual Trigger
    ping_job()
    return redirect(url_for('dashboard'))


# --- TEMPLATE INHERITANCE HACK ---
# This allows using {% extends "base" %} with strings
@app.context_processor
def inject_base():
    return dict(base=TPL_BASE)


def get_template_source(template_name):
    if template_name == 'base': return TPL_BASE
    return None


app.jinja_loader.get_source = lambda env, template: (get_template_source(template), None, lambda: True)


# --- BACKGROUND PINGER ---
def ping_job():
    with app.app_context():
        devices = Device.query.all()
        print(f"--- Scanning {len(devices)} Devices ---")
        for d in devices:
            try:
                # Ping with 1 second timeout
                resp = py_ping(d.ip, count=1, timeout=1)
                new_status = "UP" if resp.success() else "DOWN"
            except:
                new_status = "DOWN"

            if d.status != new_status:
                print(f"ALERT: {d.name} is now {new_status}")
                # Here you can add Beep sound logic later
                d.status = new_status
                d.last_seen = datetime.utcnow()
                db.session.commit()


def background_worker():
    while True:
        ping_job()
        time.sleep(30)  # Scan every 30 seconds


# --- MAIN EXECUTION ---
if __name__ == '__main__':
    # 1. Create DB
    with app.app_context():
        db.create_all()
        # Create Admin if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print(">>> Admin Created: admin / admin123")

    # 2. Start Pinger Thread
    t = threading.Thread(target=background_worker, daemon=True)
    t.start()

    # 3. Run Server
    print(">>> J.A.R.V.I.S Single Core Running on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)