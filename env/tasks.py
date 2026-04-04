# tasks.py
TASKS = {
    "easy": {
        "name": "easy",
        "description": "Same floor, nearby room. Battery starts at 100%.",
        "start_floor": 1,
        "start_room":  101,
        "target_floor": 1,
        "target_room":  103,
        "max_steps": 20,
        # min steps: next_room x2 + deliver + finish = 4
        # battery cost: 2 (rooms) = 98% remaining
    },
    "medium": {
        "name": "medium",
        "description": "Different floor and room. Must manage battery carefully.",
        "start_floor": 1,
        "start_room":  101,
        "target_floor": 3,
        "target_room":  106,
        "max_steps": 30,
        # min steps: up x2 + next_room x5 + deliver + finish = 10
        # battery cost: 6 (floors) + 5 (rooms) = 89% remaining
    },
    "hard": {
        "name": "hard",
        "description": "Many floors, tight steps. Battery may need recharging.",
        "start_floor": 1,
        "start_room":  101,
        "target_floor": 5,
        "target_room":  115,
        "max_steps": 35,
        # min steps: up x4 + next_room x14 + deliver + finish = 20
        # battery cost: 12 (floors) + 14 (rooms) = 74% remaining
        # agent must decide whether to recharge or risk it
    },
}

def get_task(task_name: str) -> dict:
    if task_name not in TASKS:
        raise ValueError(f"Unknown task: '{task_name}'. Choose from: {list(TASKS.keys())}")
    return TASKS[task_name]

def list_tasks() -> list:
    return list(TASKS.keys())