from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()

# 1. State Database tracking all 4 onboard relays individually
# True = Active/ON, False = Safe/OFF
relay_database = {
    "relay_1": False,
    "relay_2": False,
    "relay_3": False,
    "relay_4": False
}

# 2. Structured Pydantic payload definition for Postman updates
class RelayControl(BaseModel):
    channel: int = Field(..., ge=1, le=4, description="The relay number to switch (1-4)")
    state: bool = Field(..., description="Target electrical state (True = ON, False = OFF)")

@app.get("/state/")
def get_all_states():
    """
    The ESP32 controller continuously polls this endpoint.
    It returns a full JSON map of all 4 channels at once.
    """
    return relay_database

@app.post("/update/")
def update_relay_channel(payload: RelayControl):
    """
    Call this from Postman or your dashboard to toggle a specific relay.
    Example JSON payload: {"channel": 4, "state": true}
    """
    dict_key = f"relay_{payload.channel}"
    relay_database[dict_key] = payload.state
    
    return {
        "status": "synchronized",
        "modified_channel": payload.channel,
        "new_state": payload.state,
        "full_system_snapshot": relay_database
    }

