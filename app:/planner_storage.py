# planner_storage.py

from pathlib import Path
import json

DATA_FILE = Path("planner_data.json")


def load_data():
    """Load planner data from JSON file, or return defaults."""
    if not DATA_FILE.exists():
        return {
            "tasks": [],
            "groups": ["General", "Study", "Business", "Fitness", "Personal"],
            "future_me": {},  # per-day notes
        }

    try:
        raw = DATA_FILE.read_text()
        data = json.loads(raw)
    except json.JSONDecodeError:
        # If file gets corrupted, start fresh
        data = {
            "tasks": [],
            "groups": ["General", "Study", "Business", "Fitness", "Personal"],
            "future_me": {},
        }

    # Make sure keys exist even if older file
    data.setdefault("tasks", [])
    data.setdefault("groups", ["General", "Study", "Business", "Fitness", "Personal"])
    data.setdefault("future_me", {})

    return data


def save_data(data):
    """Save planner data back to JSON with nice formatting."""
    DATA_FILE.write_text(json.dumps(data, indent=2))
