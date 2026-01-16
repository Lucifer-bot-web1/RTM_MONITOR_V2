const socket = io();

// Connection Status
socket.on('connect', () => {
    console.log("Connected to J.A.R.V.I.S Server");
});

// Live Device Updates
socket.on('device_update', (data) => {
    // Look for the row
    const rowId = `row_${data.ip.replace(/\./g, '_')}`;
    const row = document.getElementById(rowId);

    if (row) {
        // Update State Badge
        const badge = row.querySelector('.badge');
        badge.className = `badge ${data.state.toLowerCase()}`;
        badge.innerText = data.state;

        // Update RTT
        const rttCell = row.querySelector('.rtt-val');
        if(rttCell) rttCell.innerText = data.rtt + ' ms';
    }
});

// Alert Handling
socket.on('alert', (data) => {
    // Show Toast Notification (Can be added later)
    console.log("ALERT:", data.msg);
});

// Sound Toggle (Optional Frontend Control)
function testSound() {
    fetch('/api/trigger_alarm', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({duration: 2})
    });
}