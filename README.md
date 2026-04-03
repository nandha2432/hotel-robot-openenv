---
title: Hotel Robot Openenv
emoji: ??
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# 🏨 Hotel Robot Delivery Environment

An OpenEnv reinforcement learning environment where a hotel delivery robot navigates floors and rooms to complete delivery tasks efficiently.

---

## 📌 Environment Description

A robot operates inside a multi-floor hotel building. It must navigate to the correct floor and room, deliver an item, and finish the task — all within a limited number of steps.

This environment simulates a real-world task: autonomous delivery robots are increasingly used in hotels, hospitals, and warehouses. Training agents in this environment develops navigation and sequential decision-making skills directly applicable to real robotic systems.

---

## 🎮 Action Space

| Action      | Description                                      |
|-------------|--------------------------------------------------|
| `up`        | Move up one floor                                |
| `down`      | Move down one floor                              |
| `next_room` | Increase room number by 1                        |
| `prev_room` | Decrease room number by 1                        |
| `deliver`   | Deliver item (only works at correct floor + room)|
| `finish`    | Finish episode (only works after delivering)     |

---

## 👁️ Observation Space

| Field           | Type | Description                        |
|-----------------|------|------------------------------------|
| `current_floor` | int  | Robot's current floor              |
| `current_room`  | int  | Robot's current room number        |
| `target_floor`  | int  | Target delivery floor              |
| `target_room`   | int  | Target delivery room number        |
| `delivered`     | bool | Whether the item has been delivered|
| `steps`         | int  | Number of steps taken so far       |

**Example observation:**
```json
{
  "current_floor": 1,
  "current_room": 101,
  "target_floor": 3,
  "target_room": 305,
  "delivered": false,
  "steps": 0
}
```

---

## 🏆 Reward Function

| Event                              | Reward |
|------------------------------------|--------|
| Every step taken                   |  -0.1  |
| Moving closer to target floor      |  +0.5  |
| Moving away from target floor      |  -0.5  |
| Being on correct floor (each step) |  +1.0  |
| Being on correct room (each step)  |  +2.0  |
| Delivering at correct location     |  +3.0  |
| Wrong delivery attempt             |  -2.0  |
| Finishing after delivery           |  +5.0  |

The reward function provides dense signal throughout the episode — not just at the end. This guides the agent to navigate efficiently and penalises wasted steps.

---

## 📋 Tasks

| Task     | Start              | Target             | Max Steps | Difficulty                        |
|----------|--------------------|--------------------|-----------|-----------------------------------|
| `easy`   | Floor 1, Room 101  | Floor 1, Room 103  | 20        | Same floor, 2 rooms away          |
| `medium` | Floor 1, Room 101  | Floor 3, Room 305  | 40        | Different floor, different room   |
| `hard`   | Floor 2, Room 210  | Floor 5, Room 512  | 25        | 3 floors up, many rooms, tight limit |

---

## 📊 Grader

Each task is scored between **0.0 and 1.0**:

| Milestone             | Score |
|-----------------------|-------|
| Reached correct floor |  +0.3 |
| Reached correct room  |  +0.3 |
| Delivered item        |  +0.4 |
| **Max total**         |  **1.0** |

---

## 🚀 Setup & Usage

### 1. Clone the repo
```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/hotel-robot-openenv
cd hotel-robot-openenv
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the server locally
```bash
uvicorn server:app --host 0.0.0.0 --port 7860
```

### 4. Test the endpoints
```bash
# Reset environment
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_name": "easy"}'

# Take a step
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action": "next_room", "task_name": "easy"}'

# Check current state
curl http://localhost:7860/state?task_name=easy

# List all tasks
curl http://localhost:7860/tasks
```

### 5. Run the inference agent
```bash
export HF_TOKEN=your_token_here
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct

python inference.py
```

---

## 🐳 Docker

### Build
```bash
docker build -t hotel-robot-openenv .
```

### Run
```bash
docker run -p 7860:7860 \
  -e HF_TOKEN=your_token \
  -e API_BASE_URL=https://router.huggingface.co/v1 \
  -e MODEL_NAME=Qwen/Qwen2.5-72B-Instruct \
  hotel-robot-openenv
```

---

## 📁 Project Structure

```
hotel-robot-openenv/
├── env/
│   ├── __init__.py       # Package marker
│   ├── hotel_env.py      # Main environment class
│   ├── tasks.py          # Task definitions (easy/medium/hard)
│   └── grader.py         # Scoring logic (0.0 to 1.0)
├── inference.py          # Agent — LLM + rule-based fallback
├── server.py             # FastAPI server (HTTP API)
├── openenv.yaml          # OpenEnv configuration
├── Dockerfile            # Container setup
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## 📈 Baseline Scores

Scores achieved by the rule-based agent (no LLM required):

| Task     | Score | Steps |
|----------|-------|-------|
| `easy`   |  1.00 |     4 |
| `medium` |  1.00 |    44 |
| `hard`   |  1.00 |    27 |

---

## 🔧 Environment Variables

| Variable       | Description            | Default                              |
|----------------|------------------------|--------------------------------------|
| `HF_TOKEN`     | HuggingFace API key    | required                             |
| `API_BASE_URL` | LLM API endpoint       | `https://router.huggingface.co/v1`   |
| `MODEL_NAME`   | Model for inference    | `Qwen/Qwen2.5-72B-Instruct`          |

---

## 📜 License

MIT
