# grader.py
# Scores how well the agent completed the delivery task
# Returns a score between 0.0 and 1.0

from hotel_env import HotelEnv


def grade(task_name: str, actions: list) -> dict:
    """
    Runs the agent's actions against the environment and scores performance.

    Scoring:
        Correct floor reached   -> +0.3
        Correct room reached    -> +0.3
        Delivery completed      -> +0.4
        Final score             -> min(total, 1.0)
    """
    env = HotelEnv(task_name=task_name)
    env.reset()

    reached_floor = False
    reached_room  = False
    delivered     = False
    steps_taken   = 0

    for action in actions:
        state, reward, done, info = env.step(action)
        steps_taken += 1

        if state["current_floor"] == state["target_floor"]:
            reached_floor = True
        if state["current_room"] == state["target_room"]:
            reached_room = True
        if state["delivered"]:
            delivered = True

        if done:
            break

    score = 0.0
    if reached_floor: score += 0.3
    if reached_room:  score += 0.3
    if delivered:     score += 0.4
    score = min(score, 1.0)

    parts = []
    if reached_floor: parts.append("reached correct floor")
    if reached_room:  parts.append("reached correct room")
    if delivered:     parts.append("delivered item")
    if not parts:     parts.append("no milestones reached")

    return {
        "score":         round(score, 2),
        "reached_floor": reached_floor,
        "reached_room":  reached_room,
        "delivered":     delivered,
        "steps_taken":   steps_taken,
        "message":       f"Task '{task_name}' | Steps: {steps_taken} | Score: {score:.2f} | " + ", ".join(parts),
    }


def grade_all(actions_per_task: dict) -> dict:
    results = {}
    total_score = 0.0
    for task_name, actions in actions_per_task.items():
        result = grade(task_name, actions)
        results[task_name] = result
        total_score += result["score"]
    results["average_score"] = round(total_score / len(results), 2) if results else 0.0
    return results


# ------------------------------------------------------------------
# Rule-based helper — generates perfect actions for any task
# ------------------------------------------------------------------
def rule_based_actions(task_name: str) -> list:
    from tasks import get_task
    task = get_task(task_name)
    cf = task["start_floor"]
    cr = task["start_room"]
    tf = task["target_floor"]
    tr = task["target_room"]

    actions = []
    while cf < tf: actions.append("up");        cf += 1
    while cf > tf: actions.append("down");      cf -= 1
    while cr < tr: actions.append("next_room"); cr += 1
    while cr > tr: actions.append("prev_room"); cr -= 1
    actions.append("deliver")
    actions.append("finish")
    return actions


# ------------------------------------------------------------------
# Test — uses rule-based actions so always correct
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Testing Grader ===\n")

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
            print(f"  Score         : {result['score']}")