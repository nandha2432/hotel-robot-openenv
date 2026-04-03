# tasks.py
# Defines the three delivery tasks for the Hotel Robot Environment

TASKS = {
    "easy": {
        "name": "easy",
        "description": "Deliver item on the same floor, nearby room",
        "start_floor": 1,
        "start_room": 101,
        "target_floor": 1,
        "target_room": 103,
        "max_steps": 20,
        # min steps: next_room x2 + deliver + finish = 4
    },

    "medium": {
        "name": "medium",
        "description": "Deliver item to a different floor and room",
        "start_floor": 1,
        "start_room": 101,
        "target_floor": 3,
        "target_room": 106,
        "max_steps": 20,
        # min steps: up x2 + next_room x5 + deliver + finish = 10
    },

    "hard": {
        "name": "hard",
        "description": "Deliver item across many floors with a tight step limit",
        "start_floor": 1,
        "start_room": 101,
        "target_floor": 4,
        "target_room": 112,
        "max_steps": 20,
        # min steps: up x3 + next_room x11 + deliver + finish = 16
        # only 4 steps of margin — genuinely hard
    },
}


def get_task(task_name: str) -> dict:
    if task_name not in TASKS:
        raise ValueError(f"Unknown task: '{task_name}'. Choose from: {list(TASKS.keys())}")
    return TASKS[task_name]


def list_tasks() -> list:
    return list(TASKS.keys())