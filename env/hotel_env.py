# hotel_env.py
# Hotel Robot Delivery Environment with Guest Rating System

from tasks import get_task, list_tasks


class HotelEnv:
    """
    Hotel Robot Delivery Environment

    The robot starts at a given floor and room.
    It must navigate to the target floor and room, deliver the item, then finish.
    After delivery, the guest gives a star rating (1-5) based on delivery speed.

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
        guest_rating    -> star rating from guest (0 = not yet rated, 1-5 after delivery)
        steps           -> number of steps taken so far
    """

    VALID_ACTIONS = ["up", "down", "next_room", "prev_room", "deliver", "finish"]

    MIN_FLOOR = 1
    MAX_FLOOR = 10
    MIN_ROOM  = 100
    MAX_ROOM  = 599

    def __init__(self, task_name: str = "easy"):
        self.task      = get_task(task_name)
        self.task_name = task_name

        self.current_floor = None
        self.current_room  = None
        self.target_floor  = None
        self.target_room   = None
        self.delivered     = False
        self.guest_rating  = 0       # 0 = not yet rated
        self.steps         = 0
        self.done          = False

    # ------------------------------------------------------------------
    # reset()
    # ------------------------------------------------------------------
    def reset(self) -> dict:
        self.current_floor = self.task["start_floor"]
        self.current_room  = self.task["start_room"]
        self.target_floor  = self.task["target_floor"]
        self.target_room   = self.task["target_room"]
        self.delivered     = False
        self.guest_rating  = 0
        self.steps         = 0
        self.done          = False
        return self.state()

    # ------------------------------------------------------------------
    # Guest rating logic
    # ------------------------------------------------------------------
    def _calculate_guest_rating(self) -> int:
        """
        Guest rates 1-5 stars based on how fast the delivery was.
        Compares steps used vs max steps allowed.

        5 stars -> used less than 30% of max steps  (very fast)
        4 stars -> used less than 50% of max steps  (fast)
        3 stars -> used less than 70% of max steps  (average)
        2 stars -> used less than 90% of max steps  (slow)
        1 star  -> used 90% or more of max steps    (very slow)
        """
        max_steps  = self.task["max_steps"]
        ratio      = self.steps / max_steps

        if ratio < 0.30:
            return 5
        elif ratio < 0.50:
            return 4
        elif ratio < 0.70:
            return 3
        elif ratio < 0.90:
            return 2
        else:
            return 1

    # ------------------------------------------------------------------
    # step(action)
    # ------------------------------------------------------------------
    def step(self, action: str):
        if self.done:
            return self.state(), 0.0, True, {"message": "Episode already finished."}

        if action not in self.VALID_ACTIONS:
            return self.state(), -0.5, False, {"message": f"Invalid action: {action}"}

        reward = 0.0
        info   = {}

        # Step penalty
        reward    -= 0.1
        self.steps += 1

        if action == "up":
            if self.current_floor < self.MAX_FLOOR:
                self.current_floor += 1
                reward += 0.5 if self.current_floor <= self.target_floor else -0.5
            else:
                info["message"] = "Already at top floor."

        elif action == "down":
            if self.current_floor > self.MIN_FLOOR:
                self.current_floor -= 1
                reward += 0.5 if self.current_floor >= self.target_floor else -0.5
            else:
                info["message"] = "Already at ground floor."

        elif action == "next_room":
            if self.current_room < self.MAX_ROOM:
                self.current_room += 1
                reward += 0.2 if self.current_room <= self.target_room else -0.2
            else:
                info["message"] = "Already at max room."

        elif action == "prev_room":
            if self.current_room > self.MIN_ROOM:
                self.current_room -= 1
                reward += 0.2 if self.current_room >= self.target_room else -0.2
            else:
                info["message"] = "Already at min room."

        elif action == "deliver":
            if self.current_floor == self.target_floor and self.current_room == self.target_room:
                if not self.delivered:
                    self.delivered    = True
                    self.guest_rating = self._calculate_guest_rating()
                    reward           += 3.0

                    # Bonus reward based on guest rating
                    rating_bonus = (self.guest_rating / 5.0) * 2.0
                    reward      += rating_bonus

                    info["message"] = (
                        f"Item delivered! Guest gives {self.guest_rating} star"
                        f"{'s' if self.guest_rating > 1 else ''}! "
                        f"Rating bonus: +{rating_bonus:.1f}"
                    )
                else:
                    info["message"] = "Already delivered."
            else:
                reward -= 2.0
                info["message"] = (
                    f"Wrong location! At Floor {self.current_floor} "
                    f"Room {self.current_room}, need Floor {self.target_floor} "
                    f"Room {self.target_room}."
                )

        elif action == "finish":
            if self.delivered:
                reward    += 5.0
                self.done  = True
                info["message"] = (
                    f"Task complete! Final guest rating: "
                    f"{self.guest_rating} star{'s' if self.guest_rating > 1 else ''}."
                )
            else:
                reward -= 1.0
                info["message"] = "Cannot finish — item not yet delivered."

        # Bonus for being on correct floor/room
        if self.current_floor == self.target_floor:
            reward += 1.0
        if self.current_room == self.target_room:
            reward += 2.0

        # Step limit check
        if self.steps >= self.task["max_steps"] and not self.done:
            self.done = True
            info["message"] = "Step limit reached. Episode ended."

        return self.state(), round(reward, 2), self.done, info

    # ------------------------------------------------------------------
    # state()
    # ------------------------------------------------------------------
    def state(self) -> dict:
        return {
            "current_floor": self.current_floor,
            "current_room":  self.current_room,
            "target_floor":  self.target_floor,
            "target_room":   self.target_room,
            "delivered":     self.delivered,
            "guest_rating":  self.guest_rating,
            "steps":         self.steps,
        }

    @staticmethod
    def available_tasks() -> list:
        return list_tasks()


# ------------------------------------------------------------------
# Quick test
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Testing HotelEnv with Guest Rating ===\n")

    for task_name in ["easy", "medium", "hard"]:
        print(f"--- Task: {task_name} ---")
        env   = HotelEnv(task_name=task_name)
        state = env.reset()
        print(f"Initial state: {state}")

        for step in range(50):
            s  = env.state()
            cf, cr = s["current_floor"], s["current_room"]
            tf, tr = s["target_floor"],  s["target_room"]

            if s["delivered"]:        action = "finish"
            elif cf < tf:             action = "up"
            elif cf > tf:             action = "down"
            elif cr < tr:             action = "next_room"
            elif cr > tr:             action = "prev_room"
            else:                     action = "deliver"

            state, reward, done, info = env.step(action)
            print(f"  {action:12s} | Reward: {reward:+.2f} | Rating: {state['guest_rating']} | {info.get('message','')}")
            if done:
                break

        print(f"  Final state: {env.state()}\n")