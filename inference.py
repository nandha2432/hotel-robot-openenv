# inference.py
# Agent that interacts with the Hotel Robot Environment
# Uses OpenAI client to call an LLM for action decisions
# Emits [START], [STEP], [END] logs as required by OpenEnv spec

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "env"))

from openai import OpenAI
from env.hotel_env import HotelEnv
from env.grader import grade

# ------------------------------------------------------------------
# Configuration — read from environment variables
# ------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")

BENCHMARK    = "hotel-robot-openenv"
MAX_STEPS    = 30
TEMPERATURE  = 0.2
MAX_TOKENS   = 50

SUCCESS_SCORE_THRESHOLD = 0.6   # score >= 0.6 counts as success

# ------------------------------------------------------------------
# Logging helpers — mandatory format
# ------------------------------------------------------------------
def log_start(task: str, env: str, model: str):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error):
    error_val = error if error else "null"
    done_val  = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: list):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

# ------------------------------------------------------------------
# System prompt — tells the LLM what it must do
# ------------------------------------------------------------------
SYSTEM_PROMPT = """
You are controlling a hotel delivery robot.
Your job is to navigate to the target floor and room, deliver the item, then finish.

Available actions (reply with ONLY one of these exact words):
  up          -> move up one floor
  down        -> move down one floor
  next_room   -> increase room number by 1
  prev_room   -> decrease room number by 1
  deliver     -> deliver item (only works at correct floor AND room)
  finish      -> finish task (only works after delivering)

Rules:
- Move floor first, then move room.
- Only say "deliver" when current_floor == target_floor AND current_room == target_room.
- Only say "finish" after delivered is true.
- Reply with ONLY the action word. Nothing else.
""".strip()

# ------------------------------------------------------------------
# Build prompt from current state
# ------------------------------------------------------------------
def build_prompt(state: dict) -> str:
    return f"""
Current floor : {state['current_floor']}
Current room  : {state['current_room']}
Target floor  : {state['target_floor']}
Target room   : {state['target_room']}
Delivered     : {state['delivered']}
Steps taken   : {state['steps']}

What is your next action?
""".strip()

# ------------------------------------------------------------------
# Ask LLM for next action
# ------------------------------------------------------------------
def get_action(client: OpenAI, state: dict) -> str:
    VALID_ACTIONS = ["up", "down", "next_room", "prev_room", "deliver", "finish"]

    prompt = build_prompt(state)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        action = (completion.choices[0].message.content or "").strip().lower()

        # Clean up — take only the first word in case LLM adds extra text
        action = action.split()[0] if action else "down"

        if action not in VALID_ACTIONS:
            print(f"[DEBUG] LLM returned invalid action '{action}', defaulting to rule-based", flush=True)
            action = rule_based_action(state)

        return action

    except Exception as e:
        print(f"[DEBUG] LLM call failed: {e} — using rule-based fallback", flush=True)
        return rule_based_action(state)

# ------------------------------------------------------------------
# Rule-based fallback agent (no LLM needed)
# Works perfectly and guarantees a baseline score
# ------------------------------------------------------------------
def rule_based_action(state: dict) -> str:
    cf = state["current_floor"]
    cr = state["current_room"]
    tf = state["target_floor"]
    tr = state["target_room"]
    delivered = state["delivered"]

    if delivered:
        return "finish"

    # First fix the floor
    if cf < tf:
        return "up"
    if cf > tf:
        return "down"

    # Floor is correct, now fix the room
    if cr < tr:
        return "next_room"
    if cr > tr:
        return "prev_room"

    # Both correct — deliver
    return "deliver"

# ------------------------------------------------------------------
# Run one episode for a given task
# ------------------------------------------------------------------
def run_episode(client: OpenAI, task_name: str):
    env = HotelEnv(task_name=task_name)
    state = env.reset()

    rewards     = []
    steps_taken = 0
    score       = 0.0
    success     = False
    actions_log = []   # for grader

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        for step in range(1, MAX_STEPS + 1):

            # Get action from LLM (with rule-based fallback)
            action = get_action(client, state)
            actions_log.append(action)

            # Step the environment
            state, reward, done, info = env.step(action)

            error = info.get("message") if "Wrong" in info.get("message", "") or "Cannot" in info.get("message", "") else None

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action, reward=reward, done=done, error=error)

            if done:
                break

        # Grade the episode
        grade_result = grade(task_name, actions_log)
        score   = grade_result["score"]
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Episode error: {e}", flush=True)

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score

# ------------------------------------------------------------------
# Main — run all 3 tasks
# ------------------------------------------------------------------
def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    tasks = ["easy", "medium", "hard"]
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

        score = run_episode(client, task_name)
        all_scores[task_name] = score

    # Final summary
    print("\n" + "=" * 50, flush=True)
    print("FINAL SCORES", flush=True)
    print("=" * 50, flush=True)
    for task_name, score in all_scores.items():
        status = "✅ PASS" if score >= SUCCESS_SCORE_THRESHOLD else "❌ FAIL"
        print(f"  {task_name:8s} : {score:.2f}  {status}", flush=True)

    avg = sum(all_scores.values()) / len(all_scores)
    print(f"\n  Average  : {avg:.2f}", flush=True)
    print("=" * 50, flush=True)


if __name__ == "__main__":
    main()