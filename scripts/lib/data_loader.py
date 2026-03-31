"""ローカル JSON データの読み書き"""

import json
from pathlib import Path
from .config import DATA_DIR


def load_json(path: Path) -> list | dict:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_tasks() -> list[dict]:
    return load_json(DATA_DIR / "tasks.json")


def save_tasks(tasks: list[dict]) -> None:
    save_json(DATA_DIR / "tasks.json", tasks)


def load_habits() -> list[dict]:
    return load_json(DATA_DIR / "habits.json")


def load_habit_log() -> list[dict]:
    return load_json(DATA_DIR / "habit_log.json")


def load_financial() -> list[dict]:
    return load_json(DATA_DIR / "financial.json")


def load_portal_notices() -> list[dict]:
    return load_json(DATA_DIR / "portal_notices.json")


def load_logs() -> list[dict]:
    return load_json(DATA_DIR / "logs.json")
