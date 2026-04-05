---
title: Hotel Robot Openenv
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
tags:
  - openenv
  - reinforcement-learning
  - robotics
  - real-world
---

# Hotel Robot Delivery Environment

An OpenEnv reinforcement learning environment where a hotel delivery robot must navigate floors and rooms, manage its battery, and race against an increasingly angry guest to complete deliveries.

---

## Environment Description

A robot operates inside a multi-floor hotel. It must navigate to the correct floor and room and deliver an item — all while managing three competing constraints:

1. **Guest Rating** — guest gives 1-5 stars based on delivery speed
2. **Battery Management** — robot must recharge at Floor 1 Room 100 or it dies mid-delivery
3. **Angry Guest System** — guest mood degrades every step and cancels the order if too slow

This makes it a genuine multi-constraint RL problem, not a simple navigation task.

---

## Action Space

| Action      | Description                                           | Battery Cost |
|-------------|-------------------------------------------------------|--------------|
| `up`        | Move up one floor                                     | -10          |
| `down`      | Move down one floor                                   | -10          |
| `next_room` | Increase room number by 1                             | -3           |
| `prev_room` | Decrease room number by 1                             | -3           |
| `deliver`   | Deliver item (only at correct floor AND room)         | 0            |
| `finish`    | End task (only after delivering)                      | 0            |
| `recharge`  | Refill battery to 100% (only at Floor 1, Room 100)   | 0            |

---

## Observation Space

| Field           | Type | Description                                      |
|-----------------|------|--------------------------------------------------|
| `current_floor` | int  | Robot's current floor                            |
| `current_room`  | int  | Robot's current room number                      |
| `target_floor`  | int  | Target delivery floor                            |
| `target_room`   | int  | Target delivery room number                      |
| `delivered`     | bool | Whether the item has been delivered              |
| `guest_rating`  | int  | Star rating 0-5 (set after delivery)             |
| `guest_mood`    | str  | happy / neutral / annoyed / angry / furious      |
| `battery`       | int  | Battery level 0-100                              |
| `charging`      | bool | Whether robot is at charging station             |
| `steps`         | int  | Number of steps taken so far                     |

---

## Guest Mood System

| Steps     | Mood      | Reward Multiplier | Effect                          |
|-----------|-----------|-------------------|---------------------------------|
| 0 - 10    | Happy     | 1.0x              | Full rewards                    |
| 11 - 20   | Neutral   | 0.8x              | Slightly reduced rewards        |
| 21 - 30   | Annoyed   | 0.5x              | Half rewards                    |
| 31 - 40   | Angry     | 0.2x              | Minimal rewards                 |
| 41+       | Furious   | 0.0x              | ORDER CANCELLED, -10 penalty    |

---

## Reward Function

| Event                              | Reward                        |
|------------------------------------|-------------------------------|
| Every step taken                   | -0.1                          |
| Moving toward correct floor        | +0.5 x mood multiplier        |
| Being on correct floor             | +1.0 x mood multiplier        |
| Being on correct room              | +2.0 x mood multiplier        |
| Smart recharge (battery < 30%)     | +1.0 x mood multiplier        |
| Unnecessary recharge (battery > 50%)| -1.0                         |
| Delivering at correct location     | +3.0 + rating bonus x mood    |
| Finishing after delivery           | +5.0 x mood multiplier        |
| Wrong delivery attempt             | -2.0                          |
| Battery dies                       | -5.0                          |
| Order cancelled (furious guest)    | -10.0                         |

---

## Tasks

| Task     | Start             | Target            | Battery | Max Steps | Challenge                              |
|----------|-------------------|-------------------|---------|-----------|----------------------------------------|
| `easy`   | Floor 1, Room 101 | Floor 1, Room 103 | 100%    | 20        | Simple nav, guest stays happy          |
| `medium` | Floor 1, Room 101 | Floor 3, Room 106 | 100%    | 30        | Multi-floor, battery survives          |
| `hard`   | Floor 1, Room 101 | Floor 5, Room 115 | 80%     | 60        | Must recharge or dies, guest gets mad  |

---

## Grader Scoring

| Milestone                  | Score              |
|----------------------------|--------------------|
| Reached correct floor      | +0.05              |
| Reached correct room       | +0.05              |
| Delivered                  | +0.20              |
| Guest rating (1-5 stars)   | (rating/5) x 0.40  |
| Mood bonus at delivery     | up to +0.20        |
| Battery remaining          | (battery/100) x 0.10|
| **Max total**              | **1.0**            |

---

## Baseline Scores

| Task     | Score | Steps | Guest Mood | Stars |
|----------|-------|-------|------------|-------|
| `easy`   | 0.99  | 4     | Happy      | 5     |
| `medium` | 0.97  | 9     | Happy      | 5     |
| `hard`   | 0.74  | 23    | Annoyed    | 4     |

---

## Setup & Usage

### Install
```bash
pip install -r requirements.txt
```

### Run server locally
```bash
uvicorn server:app --host 0.0.0.0 --port 7860
```

### Test endpoints
```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_name": "easy"}'

curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action": "next_room", "task_name": "easy"}'
```

### Run inference agent
```bash
export HF_TOKEN=your_token
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
python inference.py
```

---

## Docker

```bash
docker build -t hotel-robot-openenv .
docker run -p 7860:7860 \
  -e HF_TOKEN=your_token \
  -e API_BASE_URL=https://router.huggingface.co/v1 \
  -e MODEL_NAME=Qwen/Qwen2.5-72B-Instruct \
  hotel-robot-openenv
```

---

## Project Structure

```
hotel-robot-openenv/
├── env/
│   ├── __init__.py       # Package marker
│   ├── hotel_env.py      # Main environment (battery + mood + rating)
│   ├── tasks.py          # Task definitions (easy/medium/hard)
│   └── grader.py         # Scoring logic (0.0 to 1.0)
├── inference.py          # Agent — LLM + smart rule-based fallback
├── server.py             # FastAPI server (HTTP API)
├── openenv.yaml          # OpenEnv configuration
├── Dockerfile            # Container setup
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## Environment Variables

| Variable       | Description         | Default                            |
|----------------|---------------------|------------------------------------|
| `HF_TOKEN`     | HuggingFace API key | required                           |
| `API_BASE_URL` | LLM API endpoint    | https://router.huggingface.co/v1   |
| `MODEL_NAME`   | Model for inference | Qwen/Qwen2.5-72B-Instruct          |

---

## License

MIT