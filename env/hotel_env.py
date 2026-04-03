# hotel_env.py
# Main environment class for Hotel Robot Delivery Environment

from tasks import get_task, list_tasks


class HotelEnv:
    """
    Hotel Robot Delivery Environment

    The robot starts at a given floor and room.
    It must navigate to the target floor and room, deliver the item, then finish.

    Actions:
        up          -> move up one floor
        down        -> move down one floor
        next_room   -> move to next room number
        prev_room   -> move to previous room number
        deliver     -> deliver item if at correct location
        finish      -> finish task after delivery

    State:
        current_floor   -> robot's current floor
        current_room    -> robot's current room
        target_floor    -> destination floor
        target_room     -> destination room
        delivered       -> whether item has been delivered
        steps           -> number of steps taken so far
    """

    VALID_ACTIONS = ["up", "down", "next_room", "prev_room", "deliver", "finish"]

    MIN_FLOOR = 1
    MAX_FLOOR = 10
    MIN_ROOM = 100
    MAX_ROOM = 599

    def __init__(self, task_name: str = "easy"):
        self.task = get_task(task_name)
        self.task_name = task_name

        # These will be set properly in reset()
        self.current_floor = None
        self.current_room = None
        self.target_floor = None
        self.target_room = None
        self.delivered = False
        self.steps = 0
        self.done = False

    # ------------------------------------------------------------------
    # reset() — start a fresh episode
    # ------------------------------------------------------------------
    def reset(self) -> dict:
        """
        Resets the environment to the task's starting state.
        Returns the initial observation (state dictionary).
        """
        self.current_floor = self.task["start_floor"]
        self.current_room  = self.task["start_room"]
        self.target_floor  = self.task["target_floor"]
        self.target_room   = self.task["target_room"]
        self.delivered     = False
        self.steps         = 0
        self.done          = False

        return self.state()

    # ------------------------------------------------------------------
    # step(action) — take one action, return (state, reward, done, info)
    # ------------------------------------------------------------------
    def step(self, action: str):
        """
        Takes one action and returns (state, reward, done, info).

        Args:
            action: one of VALID_ACTIONS

        Returns:
            state  -> current state dictionary
            reward -> float reward for this step
            done   -> True if episode is over
            info   -> extra information dictionary
        """

        if self.done:
            return self.state(), 0.0, True, {"message": "Episode already finished."}

        if action not in self.VALID_ACTIONS:
            return self.state(), -0.5, False, {"message": f"Invalid action: {action}"}

        reward = 0.0
        info = {}

        # --- Step penalty every move ---
        reward -= 0.1
        self.steps += 1

        # --- Handle each action ---

        if action == "up":
            if self.current_floor < self.MAX_FLOOR:
                self.current_floor += 1
                # reward moving closer or penalize moving away
                if self.current_floor <= self.target_floor:
                    reward += 0.5   # getting closer
                else:
                    reward -= 0.5   # overshooting
            else:
                info["message"] = "Already at top floor."

        elif action == "down":
            if self.current_floor > self.MIN_FLOOR:
                self.current_floor -= 1
                if self.current_floor >= self.target_floor:
                    reward += 0.5   # getting closer
                else:
                    reward -= 0.5   # overshooting
            else:
                info["message"] = "Already at ground floor."

        elif action == "next_room":
            if self.current_room < self.MAX_ROOM:
                self.current_room += 1
                if self.current_room <= self.target_room:
                    reward += 0.2
                else:
                    reward -= 0.2
            else:
                info["message"] = "Already at max room."

        elif action == "prev_room":
            if self.current_room > self.MIN_ROOM:
                self.current_room -= 1
                if self.current_room >= self.target_room:
                    reward += 0.2
                else:
                    reward -= 0.2
            else:
                info["message"] = "Already at min room."

        elif action == "deliver":
            if self.current_floor == self.target_floor and self.current_room == self.target_room:
                if not self.delivered:
                    self.delivered = True
                    reward += 3.0
                    info["message"] = "Item delivered successfully!"
                else:
                    info["message"] = "Already delivered."
            else:
                # wrong location delivery attempt
                reward -= 2.0
                info["message"] = (
                    f"Wrong location! You are at Floor {self.current_floor} "
                    f"Room {self.current_room}, but target is "
                    f"Floor {self.target_floor} Room {self.target_room}."
                )

        elif action == "finish":
            if self.delivered:
                reward += 5.0
                self.done = True
                info["message"] = "Task complete! Robot finished successfully."
            else:
                reward -= 1.0
                info["message"] = "Cannot finish — item not yet delivered."

        # --- Bonus rewards for reaching correct floor / room ---
        if self.current_floor == self.target_floor:
            reward += 1.0

        if self.current_room == self.target_room:
            reward += 2.0

        # --- Check step limit ---
        if self.steps >= self.task["max_steps"] and not self.done:
            self.done = True
            info["message"] = "Step limit reached. Episode ended."

        return self.state(), round(reward, 2), self.done, info

    # ------------------------------------------------------------------
    # state() — return current state as a dictionary
    # ------------------------------------------------------------------
    def state(self) -> dict:
        """Returns the current state of the environment."""
        return {
            "current_floor": self.current_floor,
            "current_room":  self.current_room,
            "target_floor":  self.target_floor,
            "target_room":   self.target_room,
            "delivered":     self.delivered,
            "steps":         self.steps,
        }

    # ------------------------------------------------------------------
    # Helper — list available tasks
    # ------------------------------------------------------------------
    @staticmethod
    def available_tasks() -> list:
        return list_tasks()


# ------------------------------------------------------------------
# Quick manual test — run this file directly to check it works
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Testing HotelEnv ===\n")

    for task_name in ["easy", "medium", "hard"]:
        print(f"--- Task: {task_name} ---")
        env = HotelEnv(task_name=task_name)
        obs = env.reset()
        print(f"Initial state: {obs}")

        # Use rule-based actions — guaranteed to work
        for step in range(30):
            state = env.state()
            cf, cr = state["current_floor"], state["current_room"]
            tf, tr = state["target_floor"],  state["target_room"]

            if state["delivered"]:
                action = "finish"
            elif cf < tf:
                action = "up"
            elif cf > tf:
                action = "down"
            elif cr < tr:
                action = "next_room"
            elif cr > tr:
                action = "prev_room"
            else:
                action = "deliver"

            s, reward, done, info = env.step(action)
            print(f"  Action: {action:12s} | Reward: {reward:+.2f} | Done: {done} | {info.get('message', '')}")
            if done:
                break

        print(f"  Final state: {env.state()}\n")