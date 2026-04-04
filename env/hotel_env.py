# hotel_env.py
# Hotel Robot Delivery Environment
# Features: Guest Rating System + Battery Management

from tasks import get_task, list_tasks


class HotelEnv:
    """
    Hotel Robot Delivery Environment

    The robot must navigate to the correct floor and room and deliver the item.
    It must also manage its battery — if battery hits 0 the episode ends in failure.

    Charging station is always at Floor 1, Room 100.
    Robot must go there and use 'recharge' action to refill battery.

    Actions:
        up          -> move up one floor       (costs 3 battery)
        down        -> move down one floor     (costs 3 battery)
        next_room   -> move to next room       (costs 1 battery)
        prev_room   -> move to prev room       (costs 1 battery)
        deliver     -> deliver item            (costs 0 battery)
        finish      -> finish task             (costs 0 battery)
        recharge    -> recharge battery        (must be at Floor 1 Room 100)

    State:
        current_floor   -> robot's current floor
        current_room    -> robot's current room
        target_floor    -> destination floor
        target_room     -> destination room
        delivered       -> whether item has been delivered
        guest_rating    -> star rating 0-5 from guest after delivery
        battery         -> current battery level (0-100)
        charging        -> whether robot is currently at charging station
        steps           -> steps taken
    """

    VALID_ACTIONS = ["up", "down", "next_room", "prev_room", "deliver", "finish", "recharge"]

    MIN_FLOOR = 1
    MAX_FLOOR = 10
    MIN_ROOM  = 100
    MAX_ROOM  = 599

    CHARGE_FLOOR = 1
    CHARGE_ROOM  = 100

    BATTERY_START    = 100
    BATTERY_UP_DOWN  = 3    # cost per floor move
    BATTERY_ROOM     = 1    # cost per room move

    def __init__(self, task_name: str = "easy"):
        self.task      = get_task(task_name)
        self.task_name = task_name

        self.current_floor = None
        self.current_room  = None
        self.target_floor  = None
        self.target_room   = None
        self.delivered     = False
        self.guest_rating  = 0
        self.battery       = self.BATTERY_START
        self.charging      = False
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
        self.battery       = self.BATTERY_START
        self.charging      = False
        self.steps         = 0
        self.done          = False
        return self.state()

    # ------------------------------------------------------------------
    # Guest rating
    # ------------------------------------------------------------------
    def _calculate_guest_rating(self) -> int:
        max_steps = self.task["max_steps"]
        ratio     = self.steps / max_steps
        if ratio < 0.30:   return 5
        elif ratio < 0.50: return 4
        elif ratio < 0.70: return 3
        elif ratio < 0.90: return 2
        else:              return 1

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
        reward     -= 0.1
        self.steps += 1

        # Update charging status
        self.charging = (
            self.current_floor == self.CHARGE_FLOOR and
            self.current_room  == self.CHARGE_ROOM
        )

        # ------------------------------------------------------------------
        # Handle actions
        # ------------------------------------------------------------------
        if action == "up":
            if self.current_floor < self.MAX_FLOOR:
                self.current_floor += 1
                self.battery       -= self.BATTERY_UP_DOWN
                reward += 0.5 if self.current_floor <= self.target_floor else -0.5
            else:
                info["message"] = "Already at top floor."

        elif action == "down":
            if self.current_floor > self.MIN_FLOOR:
                self.current_floor -= 1
                self.battery       -= self.BATTERY_UP_DOWN
                reward += 0.5 if self.current_floor >= self.target_floor else -0.5
            else:
                info["message"] = "Already at ground floor."

        elif action == "next_room":
            if self.current_room < self.MAX_ROOM:
                self.current_room += 1
                self.battery      -= self.BATTERY_ROOM
                reward += 0.2 if self.current_room <= self.target_room else -0.2
            else:
                info["message"] = "Already at max room."

        elif action == "prev_room":
            if self.current_room > self.MIN_ROOM:
                self.current_room -= 1
                self.battery      -= self.BATTERY_ROOM
                reward += 0.2 if self.current_room >= self.target_room else -0.2
            else:
                info["message"] = "Already at min room."

        elif action == "recharge":
            if self.charging:
                if self.battery < 100:
                    if self.battery < 30:
                        # Smart recharge — battery was low, good decision
                        reward += 1.0
                        info["message"] = f"Smart recharge! Battery was low ({self.battery}%). Refilled to 100%."
                    elif self.battery > 50:
                        # Wasteful recharge — battery was fine
                        reward -= 1.0
                        info["message"] = f"Unnecessary recharge. Battery was {self.battery}% — wasted time."
                    else:
                        info["message"] = f"Recharging. Battery refilled to 100%."
                    self.battery = 100
                else:
                    reward -= 0.5
                    info["message"] = "Battery already full. Wasted a step."
            else:
                reward -= 1.0
                info["message"] = (
                    f"Not at charging station! "
                    f"Charging station is at Floor {self.CHARGE_FLOOR} Room {self.CHARGE_ROOM}."
                )

        elif action == "deliver":
            if self.current_floor == self.target_floor and self.current_room == self.target_room:
                if not self.delivered:
                    self.delivered    = True
                    self.guest_rating = self._calculate_guest_rating()
                    rating_bonus      = (self.guest_rating / 5.0) * 2.0
                    reward           += 3.0 + rating_bonus
                    info["message"]   = (
                        f"Delivered! Guest gives {self.guest_rating} star"
                        f"{'s' if self.guest_rating > 1 else ''}! "
                        f"Battery remaining: {self.battery}%."
                    )
                else:
                    info["message"] = "Already delivered."
            else:
                reward -= 2.0
                info["message"] = (
                    f"Wrong location! At Floor {self.current_floor} "
                    f"Room {self.current_room}, need Floor "
                    f"{self.target_floor} Room {self.target_room}."
                )

        elif action == "finish":
            if self.delivered:
                reward   += 5.0
                self.done = True
                info["message"] = (
                    f"Task complete! Rating: {self.guest_rating} stars. "
                    f"Battery remaining: {self.battery}%."
                )
            else:
                reward -= 1.0
                info["message"] = "Cannot finish — item not yet delivered."

        # Bonus for correct floor/room
        if self.current_floor == self.target_floor:
            reward += 1.0
        if self.current_room == self.target_room:
            reward += 2.0

        # ------------------------------------------------------------------
        # Battery death check
        # ------------------------------------------------------------------
        if self.battery <= 0:
            self.battery = 0
            self.done    = True
            reward      -= 5.0
            info["message"] = "Battery died! Robot stopped. Delivery failed."

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
            "battery":       self.battery,
            "charging":      self.charging,
            "steps":         self.steps,
        }

    @staticmethod
    def available_tasks() -> list:
        return list_tasks()


# ------------------------------------------------------------------
# Quick test
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Testing HotelEnv with Battery System ===\n")

    for task_name in ["easy", "medium", "hard"]:
        print(f"--- Task: {task_name} ---")
        env   = HotelEnv(task_name=task_name)
        state = env.reset()
        print(f"Initial: Floor {state['current_floor']} Room {state['current_room']} | "
              f"Target: Floor {state['target_floor']} Room {state['target_room']} | "
              f"Battery: {state['battery']}%")

        for _ in range(50):
            s  = env.state()
            cf, cr    = s["current_floor"], s["current_room"]
            tf, tr    = s["target_floor"],  s["target_room"]
            battery   = s["battery"]
            delivered = s["delivered"]

            # Battery low — go recharge first
            if battery < 20 and not delivered:
                if cf > 1:              action = "down"
                elif cr > 100:          action = "prev_room"
                else:                   action = "recharge"
            elif delivered:             action = "finish"
            elif cf < tf:               action = "up"
            elif cf > tf:               action = "down"
            elif cr < tr:               action = "next_room"
            elif cr > tr:               action = "prev_room"
            else:                       action = "deliver"

            state, reward, done, info = env.step(action)
            print(f"  {action:12s} | Reward: {reward:+.2f} | "
                  f"Battery: {state['battery']:3d}% | "
                  f"Rating: {state['guest_rating']} | "
                  f"{info.get('message', '')}")
            if done:
                break
        print()