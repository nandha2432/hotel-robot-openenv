# grader.py
# Scores agent performance:
#   - Guest rating (speed)
#   - Battery management
#   - Guest mood at delivery (angry guest system)

from hotel_env import HotelEnv


def grade(task_name: str, actions: list) -> dict:
    """
    Scoring breakdown (max 1.0):
        Reached correct floor          -> +0.05
        Reached correct room           -> +0.05
        Delivered                      -> +0.20
        Guest rating 1-5 stars         -> (rating/5) * 0.40  -> up to +0.40
        Mood bonus (happy/neutral/etc) -> up to +0.20
        Battery remaining              -> (battery/100) * 0.10 -> up to +0.10
        Max total                      -> 1.0

    Mood bonus:
        happy   -> +0.20
        neutral -> +0.15
        annoyed -> +0.10
        angry   -> +0.05
        furious -> +0.00 (order cancelled, no delivery)
    """
    env = HotelEnv(task_name=task_name)
    env.reset()

    reached_floor     = False
    reached_room      = False
    delivered         = False
    guest_rating      = 0
    guest_mood        = "happy"
    battery_remaining = 0
    steps_taken       = 0

    for action in actions:
        state, reward, done, info = env.step(action)
        steps_taken += 1

        if state["current_floor"] == state["target_floor"]: reached_floor = True
        if state["current_room"]  == state["target_room"]:  reached_room  = True
        if state["delivered"]:
            delivered         = True
            guest_rating      = state["guest_rating"]
            guest_mood        = state["guest_mood"]
            battery_remaining = state["battery"]

        if done:
            if not delivered:
                battery_remaining = state["battery"]
                guest_mood        = state["guest_mood"]
            break

    # --- Score ---
    mood_bonus = {
        "happy":   0.20,
        "neutral": 0.15,
        "annoyed": 0.10,
        "angry":   0.05,
        "furious": 0.00,
    }

    score = 0.0
    if reached_floor: score += 0.05
    if reached_room:  score += 0.05
    if delivered:
        score += 0.20
        score += (guest_rating / 5.0) * 0.40
        score += mood_bonus.get(guest_mood, 0.0)
        score += (battery_remaining / 100.0) * 0.10

    score = min(round(score, 2), 1.0)

    mood_emoji = {
        "happy": "😊", "neutral": "😐",
        "annoyed": "😠", "angry": "😡", "furious": "🤬"
    }
    stars = "⭐" * guest_rating if guest_rating > 0 else "none"
    parts = []
    if reached_floor: parts.append("reached floor")
    if reached_room:  parts.append("reached room")
    if delivered:     parts.append(f"delivered ({stars})")
    else:             parts.append("delivery failed")

    return {
        "score":             score,
        "reached_floor":     reached_floor,
        "reached_room":      reached_room,
        "delivered":         delivered,
        "guest_rating":      guest_rating,
        "guest_mood":        guest_mood,
        "battery_remaining": battery_remaining,
        "steps_taken":       steps_taken,
        "message": (
            f"Task '{task_name}' | Steps: {steps_taken} | "
            f"Mood: {mood_emoji.get(guest_mood,'😊')} {guest_mood} | "
            f"Battery: {battery_remaining}% | "
            f"Score: {score:.2f} | " + ", ".join(parts)
        ),
    }


def grade_all(actions_per_task: dict) -> dict:
    results = {}
    total   = 0.0
    for task_name, actions in actions_per_task.items():
        result             = grade(task_name, actions)
        results[task_name] = result
        total             += result["score"]
    results["average_score"] = round(total / len(results), 2)
    return results


def rule_based_actions(task_name: str) -> list:
    """
    Generates optimal actions with smart battery recharge.
    Recharges before journey if battery won't survive direct path.
    """
    from tasks import get_task
    task    = get_task(task_name)
    cf, cr  = task["start_floor"], task["start_room"]
    tf, tr  = task["target_floor"], task["target_room"]
    battery = task.get("start_battery", 100)

    FLOOR_COST = HotelEnv.BATTERY_UP_DOWN
    ROOM_COST  = HotelEnv.BATTERY_ROOM

    actions     = []
    direct_cost = abs(tf - cf) * FLOOR_COST + abs(tr - cr) * ROOM_COST

    if direct_cost >= battery:
        # Go to charger first
        while cr > 100: actions.append("prev_room"); cr -= 1
        while cr < 100: actions.append("next_room"); cr += 1
        actions.append("recharge")
        battery = 100

    # Navigate to target
    while cf < tf: actions.append("up");        cf += 1
    while cf > tf: actions.append("down");      cf -= 1
    while cr < tr: actions.append("next_room"); cr += 1
    while cr > tr: actions.append("prev_room"); cr -= 1
    actions.append("deliver")
    actions.append("finish")
    return actions


# ------------------------------------------------------------------
# Test
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Testing Grader: Battery + Guest Rating + Angry Guest ===\n")

    results = grade_all({
        "easy":   rule_based_actions("easy"),
        "medium": rule_based_actions("medium"),
        "hard":   rule_based_actions("hard"),
    })

    for task, result in results.items():
        if task == "average_score":
            print(f"\nOverall Average Score: {result}")
        else:
            print(f"\n{result['message']}")
            print(f"  Delivered        : {result['delivered']}")
            print(f"  Guest rating     : {result['guest_rating']} ⭐")
            print(f"  Guest mood       : {result['guest_mood']}")
            print(f"  Battery remaining: {result['battery_remaining']}%")
            print(f"  Score            : {result['score']}")