# inference.py
# Agent that interacts with the Hotel Robot Environment
# Uses OpenAI client to call an LLM for action decisions
# Emits [START], [STEP], [END] logs as required by OpenEnv spec

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "env"))

from openai import OpenAI
from env.hotel_env import HotelEnv
from env.grader import grade

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "your-key-here")

BENCHMARK               = "hotel-robot-openenv"
MAX_STEPS               = 60
TEMPERATURE             = 0.2
MAX_TOKENS              = 20
SUCCESS_SCORE_THRESHOLD = 0.6

# ------------------------------------------------------------------
# Logging — mandatory OpenEnv format
# ------------------------------------------------------------------
def log_start(task: str, env: str, model: str):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error):
    error_val = error if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: list):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)

# ------------------------------------------------------------------
# System prompt — includes all new features
# ------------------------------------------------------------------
SYSTEM_PROMPT = """
You are controlling a hotel delivery robot.
Navigate to the target floor and room, deliver the item, then finish.
The guest gets angrier every step — deliver fast or the order gets cancelled!
Manage your battery — recharge at Floor 1 Room 100 if needed.

Available actions (reply with ONLY one exact word):
  up          -> move up one floor        (costs 10 battery)
  down        -> move down one floor      (costs 10 battery)
  next_room   -> increase room by 1       (costs 3 battery)
  prev_room   -> decrease room by 1       (costs 3 battery)
  deliver     -> deliver item             (only at correct floor AND room)
  finish      -> end task                 (only after delivering)
  recharge    -> refill battery to 100%   (only at Floor 1 Room 100)

Strategy:
  1. If battery < 30 and not delivered, go to Floor 1 Room 100 and recharge
  2. Fix floor first, then fix room
  3. Deliver as fast as possible — guest cancels after 40 steps
  4. Reply with ONLY the action word. Nothing else.
""".strip()

# ------------------------------------------------------------------
# Build prompt with full state including new fields
# ------------------------------------------------------------------
def build_prompt(state: dict) -> str:
    return f"""
Current floor : {state['current_floor']}
Current room  : {state['current_room']}
Target floor  : {state['target_floor']}
Target room   : {state['target_room']}
Delivered     : {state['delivered']}
Battery       : {state['battery']}%
Guest mood    : {state['guest_mood']}
Steps taken   : {state['steps']}

Charging station is at Floor 1 Room 100.
What is your next action?
""".strip()

# ------------------------------------------------------------------
# Rule-based fallback — handles battery + recharge + angry guest
# ------------------------------------------------------------------
def rule_based_action(state: dict) -> str:
    cf        = state["current_floor"]
    cr        = state["current_room"]
    tf        = state["target_floor"]
    tr        = state["target_room"]
    battery   = state["battery"]
    delivered = state["delivered"]

    FLOOR_COST = HotelEnv.BATTERY_UP_DOWN
    ROOM_COST  = HotelEnv.BATTERY_ROOM

    if delivered:
        return "finish"

    # Calculate battery needed to reach target from current position
    battery_needed = abs(tf - cf) * FLOOR_COST + abs(tr - cr) * ROOM_COST

    # If battery won't survive the trip — go recharge first
    if battery < battery_needed + 10:
        if cf > 1:     return "down"
        elif cr > 100: return "prev_room"
        elif cr < 100: return "next_room"
        else:          return "recharge"

    # Navigate to target
    if cf < tf: return "up"
    if cf > tf: return "down"
    if cr < tr: return "next_room"
    if cr > tr: return "prev_room"

    return "deliver"

# ------------------------------------------------------------------
# Get action from LLM with rule-based fallback
# ------------------------------------------------------------------
def get_action(client: OpenAI, state: dict) -> str:
    VALID_ACTIONS = ["up", "down", "next_room", "prev_room", "deliver", "finish", "recharge"]

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": build_prompt(state)},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        action = (completion.choices[0].message.content or "").strip().lower()
        action = action.split()[0] if action else ""

        if action not in VALID_ACTIONS:
            print(f"[DEBUG] LLM returned '{action}' — using rule-based fallback", flush=True)
            return rule_based_action(state)

        return action

    except Exception as e:
        print(f"[DEBUG] LLM call failed: {e} — using rule-based fallback", flush=True)
        return rule_based_action(state)

# ------------------------------------------------------------------
# Run one episode
# ------------------------------------------------------------------
def run_episode(client: OpenAI, task_name: str) -> float:
    env   = HotelEnv(task_name=task_name)
    state = env.reset()

    rewards     = []
    steps_taken = 0
    score       = 0.0
    success     = False
    actions_log = []

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        for step in range(1, MAX_STEPS + 1):
            action = get_action(client, state)
            actions_log.append(action)

            state, reward, done, info = env.step(action)
            msg = info.get("message", "")

            error = msg if any(w in msg for w in ["Wrong", "Cannot", "CANCEL", "died"]) else None

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action, reward=reward, done=done, error=error)

            if done:
                break

        grade_result = grade(task_name, actions_log)
        score        = grade_result["score"]
        success      = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Episode error: {e}", flush=True)

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    client     = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    tasks      = ["easy", "medium", "hard"]
    all_scores = {}

    print("=" * 50, flush=True)
    print("Hotel Robot Delivery — Inference", flush=True)
    print(f"Model : {MODEL_NAME}", flush=True)
    print(f"API   : {API_BASE_URL}", flush=True)
    print("=" * 50, flush=True)

    for task_name in tasks:
        print(f"\n{'='*50}", flush=True)
        print(f"Running task: {task_name.upper()}", flush=True)
        print(f"{'='*50}", flush=True)
        score              = run_episode(client, task_name)
        all_scores[task_name] = score

    print("\n" + "=" * 50, flush=True)
    print("FINAL SCORES", flush=True)
    print("=" * 50, flush=True)
    for task_name, score in all_scores.items():
        status = "PASS" if score >= SUCCESS_SCORE_THRESHOLD else "FAIL"
        print(f"  {task_name:8s} : {score:.2f}  {status}", flush=True)
    avg = sum(all_scores.values()) / len(all_scores)
    print(f"\n  Average  : {avg:.2f}", flush=True)
    print("=" * 50, flush=True)


if __name__ == "__main__":
    main()