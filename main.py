from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

# Global state trackers
relay_database = {
    "relay_1": False,
    "relay_2": False,
    "relay_3": False,
    "relay_4": False
}
current_observatory_temp = 0.0  # Maintained live by the ESP32's POST requests

# Structured payload for the ESP32's POST sync
class ESP32Report(BaseModel):
    temperature_f: float

@app.post("/sync/")
def sync_hardware_and_cloud(payload: ESP32Report):
    """
    The ESP32 calls this endpoint every second via POST.
    It receives the temperature and returns the relay states instantly.
    """
    global current_observatory_temp
    current_observatory_temp = payload.temperature_f
    return relay_database

@app.get("/temperature/")
def get_current_temperature():
    """
    Returns the current temperature reading upon user request.
    Can be used by external scripts, home automation, or checked in a browser.
    """
    return {
        "status": "success",
        "temperature_f": round(current_observatory_temp, 1),
        "temperature_c": round((current_observatory_temp - 32) * 5.0 / 9.0, 1)
    }

@app.get("/", response_class=HTMLResponse)
def control_panel_ui():
    """Renders the mobile-friendly web dashboard"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Observatory Power Control</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; margin: 40px auto; max-width: 500px; background: #121212; color: #e0e0e0; }}
            h2 {{ color: #4A90E2; margin-bottom: 5px; }}
            .temp-display {{ font-size: 22px; color: #FF9800; font-weight: bold; margin-bottom: 20px; background: #221a0f; padding: 10px; border-radius: 8px; border: 1px solid #ff980033; }}
            .card {{ background: #1e1e1e; padding: 20px; border-radius: 10px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); display: flex; justify-content: space-between; align-items: center; }}
            .relay-title {{ font-size: 18px; font-weight: bold; }}
            .status {{ font-weight: bold; padding: 4px 8px; border-radius: 4px; margin-right: 10px; }}
            .status.on {{ background: #2e7d32; color: #fff; }}
            .status.off {{ background: #c62828; color: #fff; }}
            button {{ padding: 10px 20px; font-size: 14px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }}
            .btn-on {{ background: #4caf50; color: white; }}
            .btn-off {{ background: #f44336; color: white; }}
        </style>
    </head>
    <body>
        <h2>Observatory Controller</h2>
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
