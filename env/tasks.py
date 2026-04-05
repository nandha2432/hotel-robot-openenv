# tasks.py
TASKS = {
    "easy": {
        "name": "easy",
        "description": "Same floor, nearby room. Battery easily sufficient.",
        "start_floor":   1,
        "start_room":    101,
        "target_floor":  1,
        "target_room":   103,
        "start_battery": 100,
        "max_steps":     20,
        # battery cost: 2 rooms x3 = 6 used — no recharge needed
    },
    "medium": {
        "name": "medium",
        "description": "Different floor and room. Battery gets used but survives.",
        "start_floor":   1,
        "start_room":    101,
        "target_floor":  3,
        "target_room":   106,
        "start_battery": 100,
        "max_steps":     30,
        # battery cost: 2x10 + 5x3 = 35 used — no recharge needed
    },
    "hard": {
        "name": "hard",
        "description": "Starts with 80% battery. MUST recharge or dies before delivery!",
        "start_floor":   1,
        "start_room":    101,
        "target_floor":  5,
        "target_room":   115,
        "start_battery": 80,
        "max_steps":     60,
        # WITHOUT recharge: 4x10 + 14x3 = 82 battery needed > 80 — DIES
        # WITH recharge: go to room 100, recharge to 100, then navigate
        #   cost after recharge: 4x10 + 15x3 = 85, 15% battery left — survives!
    },
}

def get_task(task_name: str) -> dict:
    if task_name not in TASKS:
        raise ValueError(f"Unknown task: '{task_name}'. Choose from: {list(TASKS.keys())}")
    return TASKS[task_name]

def list_tasks() -> list:
    return list(TASKS.keys())