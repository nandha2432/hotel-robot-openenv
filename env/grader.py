# grader.py
# Scores agent performance including guest star rating
# Returns a score between 0.0 and 1.0

from hotel_env import HotelEnv


def grade(task_name: str, actions: list) -> dict:
    """
    Runs the agent's actions and scores performance.

    Scoring:
        Reached correct floor  -> +0.1
        Reached correct room   -> +0.1
        Delivered              -> +0.2
        Guest rating (1-5)     -> (rating / 5) * 0.6  -> up to +0.6
        Max total              -> 1.0

    This means a fast agent (5 stars) scores much higher than a slow one (1 star).
    """
    env = HotelEnv(task_name=task_name)
    env.reset()

    reached_floor = False
    reached_room  = False
    delivered     = False
    guest_rating  = 0
    steps_taken   = 0

    for action in actions:
        state, reward, done, info = env.step(action)
        steps_taken += 1

        if state["current_floor"] == state["target_floor"]:
            reached_floor = True
        if state["current_room"] == state["target_room"]:
            reached_room = True
        if state["delivered"]:
            delivered    = True
            guest_rating = state["guest_rating"]

        if done:
            break

    # --- Calculate score ---
    score = 0.0
    if reached_floor: score += 0.1
    if reached_room:  score += 0.1
    if delivered:     score += 0.2

    # Guest rating contributes up to 0.6
    if guest_rating > 0:
        score += (guest_rating / 5.0) * 0.6

    score = min(round(score, 2), 1.0)

    # --- Summary ---
    stars = "⭐" * guest_rating if guest_rating > 0 else "no rating"
    parts = []
    if reached_floor: parts.append("reached floor")
    if reached_room:  parts.append("reached room")
    if delivered:     parts.append(f"delivered ({stars})")
    if not parts:     parts.append("no milestones reached")

    return {
        "score":         score,
        "reached_floor": reached_floor,
        "reached_room":  reached_room,
        "delivered":     delivered,
        "guest_rating":  guest_rating,
        "steps_taken":   steps_taken,
        "message":       f"Task '{task_name}' | Steps: {steps_taken} | Score: {score:.2f} | " + ", ".join(parts),
    }


def grade_all(actions_per_task: dict) -> dict:
    results     = {}
    total_score = 0.0
    for task_name, actions in actions_per_task.items():
        result              = grade(task_name, actions)
        results[task_name]  = result
        total_score        += result["score"]
    results["average_score"] = round(total_score / len(results), 2) if results else 0.0
    return results


def rule_based_actions(task_name: str) -> list:
    from tasks import get_task
    task = get_task(task_name)
    cf, cr = task["start_floor"], task["start_room"]
    tf, tr = task["target_floor"], task["target_room"]
    actions = []
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
    print("=== Testing Grader with Guest Rating ===\n")

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
            print(f"  Floor reached : {result['reached_floor']}")
            print(f"  Room reached  : {result['reached_room']}")
            print(f"  Delivered     : {result['delivered']}")
            print(f"  Guest rating  : {result['guest_rating']} stars")
            print(f"  Score         : {result['score']}")