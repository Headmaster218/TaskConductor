valid_time_ranges = [
    ("08:00", "12:00"),
    ("14:00", "18:00"),
    ("20:00", "22:00")
]


def generate_today_schedule(tasks_json, date_str, block_duration_min=45):
    from datetime import datetime as dt, timedelta

    core_tasks = tasks_json["core_tasks"]
    core_tasks = [t for t in core_tasks if not t.get("finished", False)]
    one_time_tasks = tasks_json["one_time_tasks"]

    valid_ranges = [("08:00", "12:00"), ("14:00", "18:00"), ("20:00", "22:00")]

    available_blocks = generate_free_blocks(
        date_str, valid_ranges, one_time_tasks, block_duration_min
    )

    task_scores = sorted([
        {"name": t["name"], "score": calculate_score(t, date_str)}
        for t in core_tasks
    ], key=lambda x: -x["score"])

    schedule = []
    for i, block in enumerate(available_blocks):
        task_name = task_scores[i % len(task_scores)]["name"]
        schedule.append({
            "task": task_name,
            "start_time": block["start"],
            "end_time": block["end"]
        })

    return schedule


# ✅ Step 3 补充：调度辅助函数

def calculate_score(task, today_str):
    from datetime import datetime as dt

    due = dt.strptime(task["due_date"], "%Y-%m-%d")
    today = dt.strptime(today_str, "%Y-%m-%d")
    days_left = (due - today).days
    if days_left <= 0:
        days_left = 1  # 防止除0

    recent_history = task.get("history", [])[-5:]  # 最近五次记录
    incomplete_count = sum(1 for r in recent_history if r["status"] != "done")
    completion_factor = 1 + incomplete_count / max(1, len(recent_history))

    return task["priority"] * completion_factor / days_left

def generate_free_blocks(date_str, valid_ranges, one_time_tasks, block_min=45):
    from datetime import datetime as dt, timedelta

    date = dt.strptime(date_str, "%Y-%m-%d")
    busy_periods = []

    for t in one_time_tasks:
        if date_str in t["start_time"]:
            s = dt.fromisoformat(t["start_time"])
            e = dt.fromisoformat(t["end_time"])
            busy_periods.append((s, e))

    blocks = []
    for start_str, end_str in valid_ranges:
        start = dt.combine(date, dt.strptime(start_str, "%H:%M").time())
        end = dt.combine(date, dt.strptime(end_str, "%H:%M").time())

        cursor = start
        while cursor + timedelta(minutes=block_min) <= end:
            block_start = cursor
            block_end = cursor + timedelta(minutes=block_min)

            if not any(bs <= block_start < be or bs < block_end <= be for bs, be in busy_periods):
                blocks.append({
                    "start": block_start.isoformat(),
                    "end": block_end.isoformat()
                })
            cursor += timedelta(minutes=block_min)

    return blocks

