import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import google.generativeai as genai

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

gemini_api_key = os.getenv("GEMINI_API_KEY")
model = None

if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

tasks = []
plans = []


class Task(BaseModel):
    id: int
    text: str
    completed: bool
    createdAt: str


class Plan(BaseModel):
    id: int
    title: str
    completed: bool
    priority: str
    createdAt: str


class ChatRequest(BaseModel):
    message: str


def generate_fallback_reply(message: str) -> str:
    prompt = message.strip()
    if not prompt:
        return "Ask me about your tasks, plans, or productivity workflow and I can help."

    lowered = prompt.lower()

    if any(word in lowered for word in ["plan", "schedule", "roadmap"]):
        return (
            "Here is a simple plan:\n"
            "1. Define the goal in one sentence.\n"
            "2. Break it into 3 small actions.\n"
            "3. Pick the first action you can finish today.\n"
            "4. Review progress at the end of the day."
        )

    if any(word in lowered for word in ["task", "todo", "work"]):
        return (
            "A good next step is to sort your work into three buckets: urgent, important, and optional. "
            "Start with one urgent item, then move to one important item before adding anything new."
        )

    if any(word in lowered for word in ["hello", "hi", "hey"]):
        return (
            "Hello! I am your productivity assistant. Ask me to break down a task, create a study plan, "
            "or help organize your day."
        )

    return (
        "I can help you turn that into a clearer action plan. Try asking for next steps, a study schedule, "
        "a task breakdown, or a short productivity strategy."
    )


@app.get("/tasks")
def get_tasks():
    return tasks


@app.post("/tasks")
def add_task(task: Task):
    tasks.append(task)
    return task


@app.put("/tasks/{task_id}")
def update_task(task_id: int, updated: Task):
    for index, task in enumerate(tasks):
        if task.id == task_id:
            tasks[index] = updated
            return updated
    return {"error": "Task not found"}


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    global tasks
    tasks = [task for task in tasks if task.id != task_id]
    return {"message": "Deleted"}


@app.get("/plans")
def get_plans():
    return plans


@app.post("/plans")
def add_plan(plan: Plan):
    plans.append(plan)
    return plan


@app.put("/plans/{plan_id}")
def update_plan(plan_id: int, updated: Plan):
    for index, plan in enumerate(plans):
        if plan.id == plan_id:
            plans[index] = updated
            return updated
    return {"error": "Plan not found"}


@app.delete("/plans/{plan_id}")
def delete_plan(plan_id: int):
    global plans
    plans = [plan for plan in plans if plan.id != plan_id]
    return {"message": "Deleted"}


@app.post("/chat")
async def chat(data: ChatRequest):
    prompt = data.message.strip()
    if not prompt:
        return {"reply": "Please type a message so I can help.", "source": "fallback"}

    if model is None:
        return {"reply": generate_fallback_reply(prompt), "source": "fallback"}

    try:
        response = model.generate_content(prompt)
        reply = getattr(response, "text", "").strip()
        if not reply:
            reply = generate_fallback_reply(prompt)
            return {"reply": reply, "source": "fallback"}
        return {"reply": reply, "source": "gemini"}
    except Exception as error:
        return {"reply": generate_fallback_reply(prompt), "source": "fallback", "error": str(error)}
