import os
from datetime import date, timedelta
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import google.generativeai as genai

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
   allow_origins=[
    "http://localhost:5173",
    "https://task-frontend-six-lac.vercel.app",
    "https://task-frontend-git-main-satyamgondrawars-projects.vercel.app"
],
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
    date: Optional[str] = None


class Plan(BaseModel):
    id: int
    title: str
    completed: bool
    priority: str
    createdAt: str


class ChatRequest(BaseModel):
    message: str


class PlannerRequest(BaseModel):
    content: str
    days: int = 5


def split_content_into_tasks(content: str) -> list[str]:
    raw_lines = [line.strip(" -\t\r") for line in content.splitlines()]
    cleaned_lines = [line for line in raw_lines if line]

    if len(cleaned_lines) >= 3:
        return cleaned_lines

    sentences = [
        sentence.strip(" .")
        for sentence in content.replace("\n", ". ").split(".")
        if sentence.strip()
    ]

    if sentences:
        return sentences

    return [content.strip()]


def build_day_wise_plan(content: str, days: int) -> list[dict]:
    normalized_days = max(1, min(days, 30))
    task_items = split_content_into_tasks(content)
    today = date.today()
    grouped_plan = []

    for day_index in range(normalized_days):
        grouped_plan.append(
            {
                "day": f"Day {day_index + 1}",
                "date": (today + timedelta(days=day_index)).isoformat(),
                "tasks": [],
            }
        )

    for index, task_text in enumerate(task_items):
        grouped_plan[index % normalized_days]["tasks"].append(task_text)

    for item in grouped_plan:
        if not item["tasks"]:
            item["tasks"].append("Review progress and revise unfinished work")

    return grouped_plan


def generate_fallback_reply(message: str) -> str:
    prompt = message.strip()
    if not prompt:
        return "Ask me about your tasks, plans, or productivity workflow and I can help."

    lowered = prompt.lower()

    if any(word in lowered for word in ["procrastinating", "procrastinate", "lazy", "stuck"]):
        return (
            "Start with just 10 minutes of work instead of waiting to feel fully ready. "
            "Pick one very small step, remove distractions for a short block, and focus only on beginning."
        )

    if any(word in lowered for word in ["exam", "study", "revision", "prepare"]):
        return (
            "A simple study plan is to divide your subject into small topics, study the hardest topic first, "
            "use 45-minute focus sessions, and leave 15 minutes at the end to review what you learned."
        )

    if any(word in lowered for word in ["morning", "routine", "daily routine"]):
        return (
            "A good morning routine can be simple: wake up at the same time, avoid your phone for the first 20 minutes, "
            "list your top 3 priorities, and begin the hardest task early."
        )

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
            "The best place to start is with one task that is both important and easy to begin. "
            "Finish or make progress on that first, then move to urgent items, and keep less important tasks for later."
        )

    if any(word in lowered for word in ["hello", "hi", "hey"]):
        return (
            "Hello! You can ask me real-life questions like how to plan your day, study better, stop procrastinating, or organize your tasks."
        )

    return (
        "I can help you turn that into a clearer action plan. Try asking for next steps, a study schedule, "
        "a task breakdown, or a short productivity strategy."
    )

@app.get("/")
def root():
    return {"status": "running"}

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


@app.post("/plan-tasks")
async def plan_tasks(data: PlannerRequest):
    content = data.content.strip()
    if not content:
        return {"days": [], "summary": "Please paste some content so I can divide it into daily tasks."}

    plan = build_day_wise_plan(content, data.days)
    total_tasks = sum(len(day["tasks"]) for day in plan)

    return {
        "days": plan,
        "summary": f"I created a {len(plan)} day plan with {total_tasks} tasks.",
    }

