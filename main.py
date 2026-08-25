from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# In-memory storage for the AC switch state
state_db = {"ac_power_on": False}

class RelayState(BaseModel):
    ac_power_on: bool

@app.get("/status")
def get_status():
    """The ESP32 hits this endpoint to check the target power state"""
    return state_db

@app.post("/toggle")
def set_status(payload: RelayState):
    """External applications call this to flip the remote switch"""
    state_db["ac_power_on"] = payload.ac_power_on
    return {"message": "State synchronized", "current_db": state_db}
