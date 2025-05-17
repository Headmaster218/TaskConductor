from flask import Flask, render_template, request, jsonify, send_file, redirect
import json
import os
from datetime import datetime, timedelta
from utils.scheduler import generate_today_schedule

app = Flask(__name__)
DATA_PATH = "tasks.json"
JS_EXPORT_PATH = "static/today_status.js"

# --- 任务数据读写 ---
def load_tasks():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_tasks(data):
    with open(DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- 导出 JS 格式供前端使用 ---
def export_today_as_js(today_list):
    with open(JS_EXPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("const todayStatus = " + json.dumps(today_list, ensure_ascii=False, indent=2) + ";")

# --- 初始化或每天早晨自动构建任务表 ---
def ensure_today_status():
    today_str = datetime.now().strftime("%Y-%m-%d")
    tasks_data = load_tasks()

    if not tasks_data.get("today_status") or tasks_data["today_status"][0]["start_time"][:10] != today_str:
        schedule = generate_today_schedule(tasks_data, today_str)
        tasks_data["today_status"] = schedule
        save_tasks(tasks_data)
        export_today_as_js(schedule)

# === 路由部分 ===

@app.route('/')
def index():
    ensure_today_status()
    tasks_data = load_tasks()
    return render_template("index.html", today_plan=tasks_data["today_status"])

@app.route('/now')
def now_page():
    ensure_today_status()
    return render_template("now.html")

@app.route('/generate', methods=['POST'])
def generate_today():
    tasks_data = load_tasks()
    today = datetime.now().strftime("%Y-%m-%d")
    schedule = generate_today_schedule(tasks_data, today)
    tasks_data["today_status"] = schedule
    save_tasks(tasks_data)
    export_today_as_js(schedule)
    return jsonify({"status": "generated", "tasks": schedule})

@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.json
    task_name = data["task"]
    status = data["status"]
    duration = data.get("duration_min", 0)

    tasks_data = load_tasks()
    log_entry = {
        "task": task_name,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "status": status,
        "duration_min": duration
    }
    tasks_data["task_feedback_log"].append(log_entry)

    for t in tasks_data["core_tasks"]:
        if t["name"] == task_name:
            t.setdefault("history", []).append(log_entry)
            break

    save_tasks(tasks_data)
    return jsonify({"status": "recorded"})

@app.route('/summary')
def summary():
    tasks_data = load_tasks()

    summary_stats = {}

    for task in tasks_data["core_tasks"]:
        name = task["name"]
        records = task.get("history", [])
        total = len(records)
        done = sum(1 for r in records if r["status"] == "done")
        partial = sum(1 for r in records if r["status"] == "partial")
        fail = sum(1 for r in records if r["status"] == "fail")
        duration = sum(r.get("duration_min", 0) for r in records)
        avg_time = duration / total if total > 0 else 0
        summary_stats[name] = {
            "total": total,
            "done": done,
            "partial": partial,
            "fail": fail,
            "avg_time": round(avg_time, 1),
            "rate": round(100 * done / total, 1) if total > 0 else 0
        }

    return render_template("summary.html", stats=summary_stats)

@app.route('/tasks', methods=['GET', 'POST'])
def manage_tasks():
    tasks_data = load_tasks()

    if request.method == 'POST':
        form_type = request.form.get("form_type")

        if form_type == "core":
            # 添加或修改核心任务
            name = request.form['name']
            category = request.form['category']
            due_date = request.form['due_date']
            priority = int(request.form['priority'])

            for task in tasks_data['core_tasks']:
                if task['name'] == name:
                    task['category'] = category
                    task['due_date'] = due_date
                    task['priority'] = priority
                    break
            else:
                tasks_data['core_tasks'].append({
                    "name": name,
                    "category": category,
                    "due_date": due_date,
                    "priority": priority,
                    "history": [],
                    "switch_count": 0
                })

        elif form_type == "one_time_add":
            name = request.form['name']
            start = request.form['start_time']
            end = request.form['end_time']
            tasks_data['one_time_tasks'].append({
                "name": name,
                "start_time": start,
                "end_time": end,
                "completed": False
            })

        elif form_type == "one_time_delete":
            name = request.form['name']
            tasks_data['one_time_tasks'] = [
                t for t in tasks_data['one_time_tasks'] if t["name"] != name
            ]

        save_tasks(tasks_data)
        return redirect('/tasks')
    
@app.route('/finish_task', methods=['POST'])
def finish_task():
    data = request.json
    task_name = data["task"]

    tasks_data = load_tasks()
    for t in tasks_data["core_tasks"]:
        if t["name"] == task_name:
            t["finished"] = True
            break

    save_tasks(tasks_data)
    return jsonify({"status": "marked_as_finished"})


    return render_template("tasks.html",
                           tasks=tasks_data["core_tasks"],
                           one_time=tasks_data["one_time_tasks"])



@app.route('/today_status.js')
def serve_today_js():
    return send_file(JS_EXPORT_PATH, mimetype='application/javascript')

# 启动应用
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
