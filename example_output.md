# Codebase Export: `my_project`

## 🤖 AI-Generated Project Overview

**Project Purpose**
This is a lightweight Flask REST API for managing a to-do list. It exposes CRUD endpoints for tasks and persists data using SQLite.

**Main Components/Modules**
- `app.py` — Application entry point; registers blueprints and initializes the database
- `models.py` — SQLAlchemy `Task` model with `id`, `title`, `done`, and `created_at` fields
- `routes/tasks.py` — Blueprint with GET, POST, PUT, DELETE handlers for `/api/tasks`
- `utils/validators.py` — Input validation helpers used by the route handlers
- `requirements.txt` — Flask, Flask-SQLAlchemy, and Marshmallow dependencies

**Technologies Used**
Python 3.11, Flask 3.x, SQLAlchemy, SQLite, Marshmallow

**Architecture Overview**
Standard MVC pattern with a single-file entry point, a models layer, and a routes blueprint. All state is stored in a local SQLite database (`tasks.db`).

**Notable Patterns**
Uses the application factory pattern (`create_app()`) to allow easy test configuration overrides.

---

# Codebase Export: `my_project`

## Project Overview

| Field | Value |
|-------|-------|
| **Root folder** | `my_project` |
| **Files included** | 6 |
| **Files excluded** | 3 |
| **Generated at** | 2025-06-01 14:32:00 |

---

## Table of Contents

1. [Folder Structure](#folder-structure)
2. [File Contents](#file-contents)
   - [`app.py`](#app-py)
   - [`models.py`](#models-py)
   - [`routes/tasks.py`](#routes-tasks-py)
   - [`utils/validators.py`](#utils-validators-py)
   - [`requirements.txt`](#requirements-txt)
   - [`README.md`](#readme-md)

---

## Folder Structure

```
my_project/
├── app.py
├── models.py
├── requirements.txt
├── README.md
├── routes/
│   └── tasks.py
└── utils/
    └── validators.py
```

---

## File Contents

<a id="app-py"></a>
### 📄 `app.py`

> **Size:** 612 B &nbsp;|&nbsp; **Last modified:** 2025-05-30 10:12:00

```python
from flask import Flask
from models import db
from routes.tasks import tasks_bp

def create_app(config=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tasks.db"
    if config:
        app.config.update(config)
    db.init_app(app)
    app.register_blueprint(tasks_bp, url_prefix="/api")
    with app.app_context():
        db.create_all()
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
```

<a id="models-py"></a>
### 📄 `models.py`

> **Size:** 340 B &nbsp;|&nbsp; **Last modified:** 2025-05-28 09:00:00

```python
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    done = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

<a id="routes-tasks-py"></a>
### 📄 `routes/tasks.py`

> **Size:** 890 B &nbsp;|&nbsp; **Last modified:** 2025-05-29 11:45:00

```python
from flask import Blueprint, jsonify, request
from models import db, Task
from utils.validators import validate_task

tasks_bp = Blueprint("tasks", __name__)

@tasks_bp.route("/tasks", methods=["GET"])
def get_tasks():
    tasks = Task.query.all()
    return jsonify([{"id": t.id, "title": t.title, "done": t.done} for t in tasks])

@tasks_bp.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json()
    err = validate_task(data)
    if err:
        return jsonify({"error": err}), 400
    task = Task(title=data["title"])
    db.session.add(task)
    db.session.commit()
    return jsonify({"id": task.id}), 201
```

<a id="utils-validators-py"></a>
### 📄 `utils/validators.py`

> **Size:** 180 B &nbsp;|&nbsp; **Last modified:** 2025-05-27 08:30:00

```python
def validate_task(data: dict) -> str | None:
    if not data or "title" not in data:
        return "title is required"
    if not isinstance(data["title"], str) or not data["title"].strip():
        return "title must be a non-empty string"
    return None
```

<a id="requirements-txt"></a>
### 📄 `requirements.txt`

> **Size:** 62 B &nbsp;|&nbsp; **Last modified:** 2025-05-25 14:00:00

```text
flask>=3.0
flask-sqlalchemy>=3.1
marshmallow>=3.20
```

<a id="readme-md"></a>
### 📄 `README.md`

> **Size:** 210 B &nbsp;|&nbsp; **Last modified:** 2025-05-25 14:05:00

```markdown
# my_project

A simple Flask REST API for managing tasks.

## Run

```bash
python app.py
```

## Endpoints

- `GET  /api/tasks`
- `POST /api/tasks`
```

---

## 🚫 Excluded Files

| File | Reason |
|------|--------|
| `tasks.db` | unsupported extension (.db) |
| `__pycache__/app.cpython-311.pyc` | unsupported extension (.pyc) |
| `assets/logo.png` | unsupported extension (.png) |
