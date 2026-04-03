# server.py
# FastAPI server — exposes Hotel Robot Environment as HTTP API
# HuggingFace Space validator pings POST /reset to confirm the Space is live

import sys
import os

# Make sure env/ folder is on the path so imports work from root
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "env"))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from hotel_env import HotelEnv   # works because we added env/ to sys.path

app = FastAPI(
    title="Hotel Robot Delivery Environment",
    description="OpenEnv RL environment — hotel robot navigates floors and rooms to deliver items.",
    version="1.0.0",
)

# Store one env instance per task name
envs: dict = {}


# ------------------------------------------------------------------
# Request models
# ------------------------------------------------------------------
class ResetRequest(BaseModel):
    task_name: Optional[str] = "easy"

class StepRequest(BaseModel):
    action: str
    task_name: Optional[str] = "easy"


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "name": "Hotel Robot Delivery Environment",
        "version": "1.0.0",
        "tasks": ["easy", "medium", "hard"],
        "endpoints": ["POST /reset", "POST /step", "GET /state", "GET /tasks"],
    }


@app.post("/reset")
def reset(request: ResetRequest = ResetRequest()):
    """
    Reset the environment to starting state.
    Required by the OpenEnv validator — must return HTTP 200.
    """
    task_name = request.task_name or "easy"
    try:
        env = HotelEnv(task_name=task_name)
        state = env.reset()
        envs[task_name] = env
        return {
            "observation": state,
            "task": task_name,
            "done": False,
            "message": f"Environment reset for task '{task_name}'",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step")
def step(request: StepRequest):
    """
    Take one action. Returns observation, reward, done, info.
    Auto-resets if environment not initialized.
    """
    task_name = request.task_name or "easy"

    # Auto-reset if needed
    if task_name not in envs:
        env = HotelEnv(task_name=task_name)
        env.reset()
        envs[task_name] = env

    env = envs[task_name]
    state, reward, done, info = env.step(request.action)

    return {
        "observation": state,
        "reward":      reward,
        "done":        done,
        "info":        info,
    }


@app.get("/state")
def get_state(task_name: str = "easy"):
    """
    Returns the current state without taking any action.
    """
    if task_name not in envs:
        raise HTTPException(
            status_code=400,
            detail=f"No active environment for task '{task_name}'. Call POST /reset first."
        )
    return {"observation": envs[task_name].state()}


@app.get("/tasks")
def list_tasks():
    """
    Lists all available tasks and their details.
    """
    return {
        "tasks": [
            {
                "name":        "easy",
                "description": "Same floor, nearby room. Max 20 steps.",
                "start":       "Floor 1, Room 101",
                "target":      "Floor 1, Room 103",
                "max_steps":   20,
            },
            {
                "name":        "medium",
                "description": "Different floor and room. Max 40 steps.",
                "start":       "Floor 1, Room 101",
                "target":      "Floor 3, Room 305",
                "max_steps":   40,
            },
            {
                "name":        "hard",
                "description": "Many floors, tight step limit. Max 25 steps.",
                "start":       "Floor 2, Room 210",
                "target":      "Floor 5, Room 512",
                "max_steps":   25,
            },
        ]
    }