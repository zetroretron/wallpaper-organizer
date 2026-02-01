"""
Task storage and management module
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import uuid

from config import TASKS_FILE


def _generate_id() -> str:
    """Generate unique task ID"""
    return str(uuid.uuid4())[:8]


def load_tasks() -> List[Dict]:
    """Load all tasks from JSON file"""
    if not TASKS_FILE.exists():
        return []
    
    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("tasks", [])
    except (json.JSONDecodeError, IOError):
        return []


def save_tasks(tasks: List[Dict]) -> bool:
    """Save tasks to JSON file"""
    try:
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"tasks": tasks}, f, indent=2, ensure_ascii=False)
        return True
    except IOError:
        return False


def add_task(title: str, date: str, category: str = "default") -> Dict:
    """
    Add a new task
    
    Args:
        title: Task title/description
        date: Date in YYYY-MM-DD format
        category: Task category (deadline, important, birthday, reminder, default)
    
    Returns:
        The created task dict
    """
    tasks = load_tasks()
    
    new_task = {
        "id": _generate_id(),
        "title": title,
        "date": date,
        "category": category,
        "created_at": datetime.now().isoformat()
    }
    
    tasks.append(new_task)
    save_tasks(tasks)
    
    return new_task


def update_task(task_id: str, updates: Dict) -> Optional[Dict]:
    """
    Update an existing task
    
    Args:
        task_id: ID of task to update
        updates: Dict of fields to update
    
    Returns:
        Updated task or None if not found
    """
    tasks = load_tasks()
    
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            # Don't allow changing ID
            updates.pop("id", None)
            tasks[i].update(updates)
            save_tasks(tasks)
            return tasks[i]
    
    return None


def delete_task(task_id: str) -> bool:
    """
    Delete a task by ID
    
    Returns:
        True if deleted, False if not found
    """
    tasks = load_tasks()
    original_len = len(tasks)
    
    tasks = [t for t in tasks if t["id"] != task_id]
    
    if len(tasks) < original_len:
        save_tasks(tasks)
        return True
    
    return False


def get_tasks_for_month(year: int, month: int) -> List[Dict]:
    """Get all tasks for a specific month"""
    tasks = load_tasks()
    
    result = []
    for task in tasks:
        try:
            task_date = datetime.strptime(task["date"], "%Y-%m-%d")
            if task_date.year == year and task_date.month == month:
                result.append(task)
        except (ValueError, KeyError):
            continue
    
    return result


def get_upcoming_tasks(days: int = 7) -> List[Dict]:
    """Get tasks for the next N days"""
    tasks = load_tasks()
    today = datetime.now().date()
    
    result = []
    for task in tasks:
        try:
            task_date = datetime.strptime(task["date"], "%Y-%m-%d").date()
            delta = (task_date - today).days
            if 0 <= delta <= days:
                result.append(task)
        except (ValueError, KeyError):
            continue
    
    # Sort by date
    result.sort(key=lambda t: t["date"])
    return result


def get_tasks_for_date(date_str: str) -> List[Dict]:
    """Get all tasks for a specific date (YYYY-MM-DD)"""
    tasks = load_tasks()
    return [t for t in tasks if t.get("date") == date_str]
