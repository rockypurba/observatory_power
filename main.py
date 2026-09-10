from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime, timezone

app = FastAPI()

# Global state trackers
relay_database = {
    "relay_1": True,
    "relay_2": True,
    "relay_3": True,
    "relay_4": True
}
current_observatory_temp = 0.0

# Watchdog variables to capture the heartbeat of the controller
last_heartbeat_time = None  # Tracks the exact datetime of the last ESP32 contact

# Structured payload for the ESP32's POST sync
class ESP32Report(BaseModel):
    temperature_f: float

@app.post("/sync/")
def sync_hardware_and_cloud(payload: ESP32Report):
    """
    The ESP32 calls this endpoint every second via POST.
    Updates the temperature reading and logs the arrival time as a heartbeat.
    """
    global current_observatory_temp, last_heartbeat_time
    current_observatory_temp = payload.temperature_f
    
    # Save the exact current timestamp in timezone-aware UTC format
    last_heartbeat_time = datetime.now(timezone.utc)
    
    return relay_database

@app.get("/temperature/")
def get_current_temperature():
    """
    Returns the current temperature and includes device connectivity status
    so external scripts know if the telemetry stream is stale.
    """
    is_online = False
    if last_heartbeat_time is not None:
        seconds_since_last_poll = (datetime.now(timezone.utc) - last_heartbeat_time).total_seconds()
        if seconds_since_last_poll <= 5.0:
            is_online = True

    return {
        "status": "success",
        "controller_online": is_online,
        "temperature_f": round(current_observatory_temp, 1),
        "temperature_c": round((current_observatory_temp - 32) * 5.0 / 9.0, 1),
        "last_seen_seconds_ago": round((datetime.now(timezone.utc) - last_heartbeat_time).total_seconds(), 1) if last_heartbeat_time else None
    }

@app.get("/", response_class=HTMLResponse)
def control_panel_ui():
    """Renders the mobile-friendly web dashboard with real-time connection badges"""
    
    # Evaluate the connectivity matrix state
    if last_heartbeat_time is None:
        status_badge = '<div class="conn-badge offline">🔴 CONTROLLER NOT DETECTED (NEVER CONNECTED)</div>'
    else:
        # Calculate time passed since the last ESP32 communication loop execution
        seconds_since_contact = (datetime.now(timezone.utc) - last_heartbeat_time).total_seconds()
        
        # If the device skips more than 5 polling heartbeats, flag it as dropped
        if seconds_since_contact > 5.0:
            status_badge = f'<div class="conn-badge offline">🔴 CONTROLLER OFFLINE (Disconnected {round(seconds_since_contact)}s ago)</div>'
        else:
            status_badge = '<div class="conn-badge online">🟢 CONTROLLER ONLINE (Connected via Ethernet)</div>'

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Observatory Power Control</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; margin: 40px auto; max-width: 500px; background: #121212; color: #e0e0e0; }}
            h2 {{ color: #4A90E2; margin-bottom: 15px; }}
            .conn-badge {{ font-size: 14px; font-weight: bold; padding: 8px; border-radius: 6px; margin-bottom: 15px; }}
            .conn-badge.online {{ background: #1b5e20; color: #a5d6a7; border: 1px solid #2e7d32; }}
            .conn-badge.offline {{ background: #b71c1c; color: #ffcdd2; border: 1px solid #c62828; animation: blink 2s infinite; }}
            .temp-display {{ font-size: 22px; color: #FF9800; font-weight: bold; margin-bottom: 20px; background: #221a0f; padding: 10px; border-radius: 8px; border: 1px solid #ff980033; }}
            .card {{ background: #1e1e1e; padding: 20px; border-radius: 10px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); display: flex; justify-content: space-between; align-items: center; }}
            .relay-title {{ font-size: 18px; font-weight: bold; }}
            .status {{ font-weight: bold; padding: 4px 8px; border-radius: 4px; margin-right: 10px; }}
            .status.on {{ background: #2e7d32; color: #fff; }}
            .status.off {{ background: #c62828; color: #fff; }}
            button {{ padding: 10px 20px; font-size: 14px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }}
            .btn-on {{ background: #4caf50; color: white; }}
            .btn-off {{ background: #f44336; color: white; }}
            @keyframes blink {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.6; }} 100% {{ opacity: 1; }} }}
        </style>
    </head>
    <body>
        <h2>Observatory Controller</h2>
        {status_badge}
        <div class="temp-display">Enclosure Temp: {current_observatory_temp:.1f} °F</div>
        <hr style="border: 0; border-top: 1px solid #333; margin-bottom: 20px;">
    """
    
    names = ["Mount (Ch 1)", "Roof (Ch 2)", "PC (Ch 3)", "Misc (Ch 4)"]
    for i in range(1, 5):
        current_state = relay_database[f"relay_{i}"]
        status_label = "ON" if current_state else "OFF"
        status_class = "on" if current_state else "off"
        target_action = "false" if current_state else "true"
        button_label = "Turn OFF" if current_state else "Turn ON"
        button_class = "btn-off" if current_state else "btn-on"
        
        html_content += f"""
        <div class="card">
            <span class="relay-title">{names[i-1]}</span>
            <div>
                <span class="status {status_class}">{status_label}</span>
                <form action="/toggle-web" method="post" style="display: inline;">
                    <input type="hidden" name="channel" value="{i}">
                    <input type="hidden" name="state" value="{target_action}">
                    <button type="submit" class="{button_class}">{button_label}</button>
                </form>
            </div>
        </div>
        """
        
    html_content += "</body></html>"
    return html_content

@app.post("/toggle-web")
def handle_form_toggle(channel: int = Form(...), state: str = Form(...)):
    bool_state = True if state.lower() == "true" else False
    relay_database[f"relay_{channel}"] = bool_state
    return HTMLResponse(content="<script>window.location.href='/';</script>", status_code=200)
