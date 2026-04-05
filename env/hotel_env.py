# hotel_env.py
# Hotel Robot Delivery Environment
# Features:
#   1. Guest Rating System    — 1-5 stars based on delivery speed
#   2. Battery Management     — robot must recharge or dies mid-delivery
#   3. Angry Guest System     — guest mood degrades over time, cancels if too slow

from tasks import get_task, list_tasks

from typing import Literal
from pydantic import BaseModel


# ------------------------------------------------------------------
# Typed Pydantic models — required by OpenEnv spec
# ------------------------------------------------------------------

class HotelObservation(BaseModel):
    current_floor: int
    current_room:  int
    target_floor:  int
    target_room:   int
    delivered:     bool
    guest_rating:  int
    guest_mood:    Literal["happy", "neutral", "annoyed", "angry", "furious"]
    battery:       int
    charging:      bool
    steps:         int


class HotelAction(BaseModel):
    action: Literal["up", "down", "next_room", "prev_room", "deliver", "finish", "recharge"]


class HotelReward(BaseModel):
    value:   float
    done:    bool
    success: bool





class HotelEnv:
    """
    Hotel Robot Delivery Environment

    The robot must navigate to the correct floor and room and deliver the item.
    It must manage battery AND race against a guest who gets progressively angrier.

    Guest Mood Timeline:
        Steps  0-10 : 😊 Happy    — full rewards
        Steps 11-20 : 😐 Neutral  — reward multiplier 0.8x
        Steps 21-30 : 😠 Annoyed  — reward multiplier 0.5x
        Steps 31-40 : 😡 Angry    — reward multiplier 0.2x
        Steps 41+   : 🤬 Furious  — ORDER CANCELLED, -10 reward, episode ends

    Battery:
        Charging station at Floor 1, Room 100
        up/down costs 10 battery
        next_room/prev_room costs 3 battery
        Hard task starts at 80% battery — must recharge or dies

    Actions:
        up, down, next_room, prev_room, deliver, finish, recharge

    State:
        current_floor, current_room, target_floor, target_room,
        delivered, guest_rating, guest_mood,
        battery, charging, steps
    """

    VALID_ACTIONS = ["up", "down", "next_room", "prev_room", "deliver", "finish", "recharge"]

    MIN_FLOOR = 1
    MAX_FLOOR = 10
    MIN_ROOM  = 100
    MAX_ROOM  = 599

    CHARGE_FLOOR = 1
    CHARGE_ROOM  = 100

    BATTERY_START    = 100
    BATTERY_UP_DOWN  = 10   # cost per floor move
    BATTERY_ROOM     = 3    # cost per room move

    # Guest mood thresholds
    MOOD_HAPPY    = (0,  10)
    MOOD_NEUTRAL  = (11, 20)
    MOOD_ANNOYED  = (21, 30)
    MOOD_ANGRY    = (31, 40)
    MOOD_FURIOUS  = 41       # cancels order at this step

    MOOD_MULTIPLIERS = {
        "happy":   1.0,
        "neutral": 0.8,
        "annoyed": 0.5,
        "angry":   0.2,
        "furious": 0.0,
    }

    def __init__(self, task_name: str = "easy"):
        self.task      = get_task(task_name)
        self.task_name = task_name

        self.current_floor = None
        self.current_room  = None
        self.target_floor  = None
        self.target_room   = None
        self.delivered     = False
        self.guest_rating  = 0
        self.guest_mood    = "happy"
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
        self.guest_mood    = "happy"
        self.battery       = self.task.get("start_battery", self.BATTERY_START)
        self.charging      = False
        self.steps         = 0
        self.done          = False
        return self.state()

    # ------------------------------------------------------------------
    # Guest mood logic
    # ------------------------------------------------------------------
    def _get_guest_mood(self) -> str:
        if self.steps >= self.MOOD_FURIOUS:  return "furious"
        elif self.steps >= self.MOOD_ANGRY[0]:   return "angry"
        elif self.steps >= self.MOOD_ANNOYED[0]:  return "annoyed"
        elif self.steps >= self.MOOD_NEUTRAL[0]:  return "neutral"
        else:                                      return "happy"

    def _get_mood_emoji(self) -> str:
        emojis = {
            "happy":   "😊 Happy",
            "neutral": "😐 Neutral",
            "annoyed": "😠 Annoyed",
            "angry":   "😡 Angry",
            "furious": "🤬 Furious",
        }
        return emojis.get(self.guest_mood, "😊 Happy")

    # ------------------------------------------------------------------
    # Guest rating after delivery
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

        # Update mood and charging status
        self.guest_mood = self._get_guest_mood()
        self.charging   = (
            self.current_floor == self.CHARGE_FLOOR and
            self.current_room  == self.CHARGE_ROOM
        )

        # ------------------------------------------------------------------
        # Check if guest cancels order (furious)
        # ------------------------------------------------------------------
        if self.guest_mood == "furious" and not self.delivered:
            self.done = True
            reward   -= 10.0
            info["message"] = (
                f"🤬 ORDER CANCELLED! Guest got furious after {self.steps} steps. "
                f"-10 penalty. Always deliver within 40 steps!"
            )
            return self.state(), round(reward, 2), self.done, info

        # ------------------------------------------------------------------
        # Mood multiplier — rewards shrink as guest gets angrier
        # ------------------------------------------------------------------
        mood_multiplier = self.MOOD_MULTIPLIERS[self.guest_mood]

        # ------------------------------------------------------------------
        # Handle actions
        # ------------------------------------------------------------------
        if action == "up":
            if self.current_floor < self.MAX_FLOOR:
                self.current_floor += 1
                self.battery       -= self.BATTERY_UP_DOWN
                base_reward = 0.5 if self.current_floor <= self.target_floor else -0.5
                reward += base_reward * mood_multiplier
            else:
                info["message"] = "Already at top floor."

        elif action == "down":
            if self.current_floor > self.MIN_FLOOR:
                self.current_floor -= 1
                self.battery       -= self.BATTERY_UP_DOWN
                base_reward = 0.5 if self.current_floor >= self.target_floor else -0.5
                reward += base_reward * mood_multiplier
            else:
                info["message"] = "Already at ground floor."

        elif action == "next_room":
            if self.current_room < self.MAX_ROOM:
                self.current_room += 1
                self.battery      -= self.BATTERY_ROOM
                base_reward = 0.2 if self.current_room <= self.target_room else -0.2
                reward += base_reward * mood_multiplier
            else:
                info["message"] = "Already at max room."

        elif action == "prev_room":
            if self.current_room > self.MIN_ROOM:
                self.current_room -= 1
                self.battery      -= self.BATTERY_ROOM
                base_reward = 0.2 if self.current_room >= self.target_room else -0.2
                reward += base_reward * mood_multiplier
            else:
                info["message"] = "Already at min room."

        elif action == "recharge":
            if self.charging:
                if self.battery < 100:
                    if self.battery < 30:
                        reward += 1.0 * mood_multiplier
                        info["message"] = (
                            f"Smart recharge! Battery was {self.battery}%. "
                            f"Refilled to 100%. Guest mood: {self._get_mood_emoji()}"
                        )
                    elif self.battery > 50:
                        reward -= 1.0
                        info["message"] = (
                            f"Unnecessary recharge! Battery was {self.battery}% — "
                            f"wasted time. Guest is getting impatient! {self._get_mood_emoji()}"
                        )
                    else:
                        info["message"] = f"Recharged to 100%. Guest mood: {self._get_mood_emoji()}"
                    self.battery = 100
                else:
                    reward -= 0.5
                    info["message"] = "Battery already full. Wasted a step!"
            else:
                reward -= 1.0
                info["message"] = (
                    f"Not at charging station! "
                    f"Go to Floor {self.CHARGE_FLOOR} Room {self.CHARGE_ROOM} first."
                )

        elif action == "deliver":
            if self.current_floor == self.target_floor and self.current_room == self.target_room:
                if not self.delivered:
                    self.delivered    = True
                    self.guest_rating = self._calculate_guest_rating()
                    rating_bonus      = (self.guest_rating / 5.0) * 2.0
                    base_reward       = 3.0 + rating_bonus
                    reward           += base_reward * mood_multiplier
                    info["message"]   = (
                        f"Delivered! Guest mood: {self._get_mood_emoji()} | "
                        f"{self.guest_rating} stars ({'⭐' * self.guest_rating}) | "
                        f"Battery: {self.battery}%"
                    )
                else:
                    info["message"] = "Already delivered."
            else:
                reward -= 2.0
                info["message"] = (
                    f"Wrong location! At F{self.current_floor} R{self.current_room}, "
                    f"need F{self.target_floor} R{self.target_room}. "
                    f"Guest mood: {self._get_mood_emoji()}"
                )

        elif action == "finish":
            if self.delivered:
                reward   += 5.0 * mood_multiplier
                self.done = True
                info["message"] = (
                    f"Task complete! "
                    f"Rating: {'⭐' * self.guest_rating} | "
                    f"Mood: {self._get_mood_emoji()} | "
                    f"Battery: {self.battery}%"
                )
            else:
                reward -= 1.0
                info["message"] = "Cannot finish — item not yet delivered."

        # Bonus for correct floor/room (scaled by mood)
        if self.current_floor == self.target_floor:
            reward += 1.0 * mood_multiplier
        if self.current_room == self.target_room:
            reward += 2.0 * mood_multiplier

        # ------------------------------------------------------------------
        # Battery death check
        # ------------------------------------------------------------------
        if self.battery <= 0:
            self.battery = 0
            self.done    = True
            reward      -= 5.0
            info["message"] = (
                f"🔋 Battery died! Robot stopped. "
                f"Guest mood was: {self._get_mood_emoji()}. Delivery failed."
            )

        # Step limit check
        if self.steps >= self.task["max_steps"] and not self.done:
            self.done = True
            info["message"] = f"Step limit reached. Guest mood: {self._get_mood_emoji()}"

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
            "guest_mood":    self.guest_mood,
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
    print("=== Testing HotelEnv: Battery + Guest Rating + Angry Guest ===\n")

    for task_name in ["easy", "medium", "hard"]:
        print(f"--- Task: {task_name} ---")
        env   = HotelEnv(task_name=task_name)
        state = env.reset()
        print(f"Start : Floor {state['current_floor']} Room {state['current_room']} | "
              f"Target: Floor {state['target_floor']} Room {state['target_room']} | "
              f"Battery: {state['battery']}% | Mood: 😊 Happy")
        print()

        for _ in range(80):
            s         = env.state()
            cf, cr    = s["current_floor"], s["current_room"]
            tf, tr    = s["target_floor"],  s["target_room"]
            battery   = s["battery"]
            delivered = s["delivered"]

            direct_cost = abs(tf - cf) * HotelEnv.BATTERY_UP_DOWN + abs(tr - cr) * HotelEnv.BATTERY_ROOM
            needs_recharge = battery < direct_cost + 10 and not delivered

            if needs_recharge:
                if cf > 1:     action = "down"
                elif cr > 100: action = "prev_room"
                elif cr < 100: action = "next_room"
                else:          action = "recharge"
            elif delivered:    action = "finish"
            elif cf < tf:      action = "up"
            elif cf > tf:      action = "down"
            elif cr < tr:      action = "next_room"
            elif cr > tr:      action = "prev_room"
            else:              action = "deliver"

            state, reward, done, info = env.step(action)
            print(f"  {action:12s} | Reward: {reward:+.2f} | "
                  f"Bat: {state['battery']:3d}% | "
                  f"Mood: {state['guest_mood']:8s} | "
                  f"{info.get('message', '')}")
            if done:
                print(f"\n  Final → Delivered: {state['delivered']} | "
                      f"Rating: {'⭐' * state['guest_rating'] if state['guest_rating'] else 'none'} | "
                      f"Steps: {state['steps']}")
                break
        print()