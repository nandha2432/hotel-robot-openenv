# server.py
# FastAPI server — exposes Hotel Robot Environment as HTTP API

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "env"))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from hotel_env import HotelEnv

app = FastAPI(
    title="Hotel Robot Delivery Environment",
    description=(
        "OpenEnv RL environment — hotel robot navigates floors and rooms to deliver items. "
        "Features: guest rating system, battery management, angry guest system."
    ),
    version="1.0.0",
)

envs: dict = {}

class ResetRequest(BaseModel):
    task_name: Optional[str] = "easy"

class StepRequest(BaseModel):
    action: str
    task_name: Optional[str] = "easy"

@app.get("/")
def root():
    return {
        "name":      "Hotel Robot Delivery Environment",
        "version":   "1.0.0",
        "features":  ["guest rating", "battery management", "angry guest system"],
        "tasks":     ["easy", "medium", "hard"],
        "actions":   ["up", "down", "next_room", "prev_room", "deliver", "finish", "recharge"],
        "endpoints": ["POST /reset", "POST /step", "GET /state", "GET /tasks"],
    }

@app.post("/reset")
def reset(request: ResetRequest = ResetRequest()):
    task_name = request.task_name or "easy"
    try:
        env   = HotelEnv(task_name=task_name)
        state = env.reset()
        envs[task_name] = env
        return {
            "observation": state,
            "task":        task_name,
            "done":        False,
            "message":     f"Environment reset for task '{task_name}'",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/step")
def step(request: StepRequest):
    task_name = request.task_name or "easy"
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
    if task_name not in envs:
        raise HTTPException(status_code=400, detail=f"Call POST /reset first for task '{task_name}'.")
    return {"observation": envs[task_name].state()}

@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {
                "name":          "easy",
                "description":   "Same floor, nearby room. Battery sufficient, guest stays happy.",
                "start":         "Floor 1, Room 101",
                "target":        "Floor 1, Room 103",
                "start_battery": 100,
                "max_steps":     20,
            },
            {
                "name":          "medium",
                "description":   "Different floor and room. Battery used but survives without recharge.",
                "start":         "Floor 1, Room 101",
                "target":        "Floor 3, Room 106",
                "start_battery": 100,
                "max_steps":     30,
            },
            {
                "name":          "hard",
                "description":   "Starts at 80% battery. Must recharge or dies. Guest gets annoyed.",
                "start":         "Floor 1, Room 101",
                "target":        "Floor 5, Room 115",
                "start_battery": 80,
                "max_steps":     60,
            },
        ]
    }