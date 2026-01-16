# Pure Python file acting as a container for HTML strings
# This allows 'main.py' to remain clean.

BASE_CSS = """
<style>
:root{ --bg:#0f172a; --txt:#f1f5f9; --glass:rgba(30,41,59,0.7); --accent:#3b82f6; --danger:#ef4444; }
body { background: var(--bg); color: var(--txt); font-family: 'Segoe UI', sans-serif; margin:0; overflow:hidden; }
.container { height: 100vh; display: flex; flex-direction: column; }
.header { padding: 15px; background: var(--glass); display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #334155; }
.content { flex:1; overflow-y: auto; padding: 20px; }
/* Table Scroll Fix */
table { width: 100%; border-collapse: collapse; }
th { position: sticky; top: 0; background: #1e293b; padding: 10px; text-align: left; z-index: 10; }
td { padding: 10px; border-bottom: 1px solid #334155; }
.btn { padding: 8px 16px; background: var(--accent); border:none; color:white; border-radius:4px; cursor:pointer; }
.btn:hover { opacity: 0.9; }
.badge { padding: 4px 8px; border-radius: 12px; font-size: 12px; }
.up { background: #22c55e; color: black; }
.down { background: #ef4444; color: white; }
</style>
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
"""

# LOGIN PAGE
TPL_LOGIN = f"""
<!doctype html><html><head><title>Login</title>{BASE_CSS}</head><body>
<div style="display:flex; justify-content:center; align-items:center; height:100vh;">
  <div style="background:var(--glass); padding:40px; border-radius:10px; width:300px;">
    <h2 style="text-align:center">J.A.R.V.I.S Monitor</h2>
    <form method="post">
      <input style="width:100%; padding:10px; margin-bottom:10px; background:#1e293b; border:1px solid #334155; color:white;" name="username" placeholder="Username">
      <input style="width:100%; padding:10px; margin-bottom:20px; background:#1e293b; border:1px solid #334155; color:white;" type="password" name="password" placeholder="Password">
      <button class="btn" style="width:100%">LOGIN</button>
    </form>
    <div style="margin-top:20px; text-align:center; font-size:12px; color:#94a3b8;">Protected by RTM Pro Architecture</div>
  </div>
</div>
</body></html>
"""

# DASHBOARD (With Scroll Fix & SocketIO)
TPL_DASHBOARD = f"""
<!doctype html><html><head><title>Dashboard</title>{BASE_CSS}</head><body>
<div class="container">
  <div class="header">
    <h3>RTM Pro Dashboard</h3>
    <div>
        <a href="/devices" class="btn">Devices</a>
        <a href="/logout" class="btn" style="background:var(--danger)">Logout</a>
    </div>
  </div>
  <div class="content">
    <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:15px; margin-bottom:20px;">
       <div style="background:var(--glass); padding:20px; border-radius:8px;">UP: <b id="c_up">{{{{up}}}}</b></div>
       <div style="background:var(--glass); padding:20px; border-radius:8px;">DOWN: <b id="c_down" style="color:var(--danger)">{{{{down}}}}</b></div>
    </div>
    <div style="background:var(--glass); border-radius:8px; overflow:hidden;">
        <table>
            <thead><tr><th>IP</th><th>Name</th><th>State</th><th>RTT</th></tr></thead>
            <tbody id="dev_list">
                {{% for d in devices %}}
                <tr id="row_{{{{d.ip.replace('.','_')}}}}">
                    <td>{{{{d.ip}}}}</td>
                    <td>{{{{d.name}}}}</td>
                    <td><span class="badge {{{{d.state.lower()}}}}">{{{{d.state}}}}</span></td>
                    <td>-</td>
                </tr>
                {{% endfor %}}
            </tbody>
        </table>
    </div>
  </div>
</div>
<script>
const socket = io();
socket.on('device_update', (d) => {{
    const row = document.getElementById('row_' + d.ip.replace(/\./g,'_'));
    if(row) {{
        row.querySelector('.badge').className = 'badge ' + d.state.toLowerCase();
        row.querySelector('.badge').innerText = d.state;
    }}
}});
socket.on('alert', (msg) => {{ alert(msg.msg); }});
</script>
</body></html>
"""

# Add other templates (Settings, Devices, Expiry) similarly...