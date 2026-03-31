#!/usr/bin/env python3
"""タスク同期 + 命名規則自動修正 + レポート生成 — cron から毎日実行"""

import sys
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.task_sync import sync_tasks
from lib.data_loader import load_tasks
from lib.config import DATA_DIR

DAYS = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{now}] task_sync 開始")
    result = sync_tasks()
    print(f"[{now}] task_sync 完了: {result}")

    if result.get("renamed", 0) > 0:
        print(f"  → {result['renamed']}件の命名規則修正を実施")

    generate_report(now)
    generate_display(now)
    print(f"  → task_report.md / task_display.txt 更新完了")


def generate_report(synced_at: str):
    """data/task_report.md を最新状態で書き出す"""
    tasks = load_tasks()
    today_str = date.today().isoformat()

    incomplete = [t for t in tasks if not t["completed"]]
    completed = [t for t in tasks if t["completed"]]

    overdue = [t for t in incomplete if t.get("deadline") and t["deadline"] < today_str]
    today_t = [t for t in incomplete if t.get("deadline") == today_str]
    future = [t for t in incomplete if t.get("deadline") and t["deadline"] > today_str]
    no_limit = [t for t in incomplete if not t.get("deadline")]

    def sort_key(t):
        grp, _, _ = parse_task(t)
        return (t.get("deadline", "") or "9999", 0 if grp == "WRK" else 1)

    lines = [f"# DON'S TASKS ({synced_at} synced)", ""]

    def write_section(group, label):
        group.sort(key=sort_key)
        lines.append(f"## {label} ({len(group)}件)")
        lines.append("")
        if not group:
            lines.append("なし")
            lines.append("")
            return
        lines.append("| # | deadline | grp | cat | title | notes |")
        lines.append("|---|----------|-----|-----|-------|-------|")
        for i, t in enumerate(group, 1):
            grp, cat, title = parse_task(t)
            dl = fmt_date(t.get("deadline", ""))
            notes = t.get("notes", "").replace("\n", " ")[:40]
            lines.append(f"| {i} | {dl} | {grp} | {cat} | {title} | {notes} |")
        lines.append("")

    write_section(overdue, "overdue")
    write_section(today_t, "today")
    write_section(future, "future")
    write_section(no_limit, "no limit")

    # completed（直近5件）
    recent = sorted(completed, key=lambda t: t.get("timestamp", ""), reverse=True)[:5]
    lines.append(f"## completed (直近{len(recent)}件)")
    lines.append("")
    if recent:
        lines.append("| # | title |")
        lines.append("|---|-------|")
        for i, t in enumerate(recent, 1):
            lines.append(f"| {i} | ✅ {t['name']} |")
    else:
        lines.append("なし")
    lines.append("")

    report_path = DATA_DIR / "task_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")


def generate_display(synced_at: str):
    """data/task_display.txt を可読性の高いフォーマットで書き出す"""
    tasks = load_tasks()
    today_str = date.today().isoformat()
    today_fmt = date.today().strftime("%Y-%m-%d")
    time_fmt = synced_at.split(" ")[-1] if " " in synced_at else synced_at

    incomplete = [t for t in tasks if not t["completed"]]
    completed = [t for t in tasks if t["completed"]]

    overdue = sorted(
        [t for t in incomplete if t.get("deadline") and t["deadline"] < today_str],
        key=lambda t: (t.get("deadline", ""), 0 if parse_task(t)[0] == "WRK" else 1),
    )
    today_t = sorted(
        [t for t in incomplete if t.get("deadline") == today_str],
        key=lambda t: (0 if parse_task(t)[0] == "WRK" else 1),
    )
    future = sorted(
        [t for t in incomplete if t.get("deadline") and t["deadline"] > today_str],
        key=lambda t: (t.get("deadline", ""), 0 if parse_task(t)[0] == "WRK" else 1),
    )
    no_limit = sorted(
        [t for t in incomplete if not t.get("deadline")],
        key=lambda t: (0 if parse_task(t)[0] == "WRK" else 1),
    )
    recent_done = sorted(completed, key=lambda t: t.get("timestamp", ""), reverse=True)[:5]

    W = 30  # iPhone 30文字幅対応

    def _clean_notes(notes_raw: str) -> str:
        """notes から [WRK/mngt] タグ行を除去"""
        import re
        lines = notes_raw.split("\n")
        cleaned = [l for l in lines if not re.match(r"^\[(WRK|PRV)/\w+\]$", l.strip())]
        return " ".join(cleaned).strip()

    def row(t):
        grp, cat, title = parse_task(t)
        dl = fmt_date(t.get("deadline", ""))
        notes = _clean_notes(t.get("notes", ""))
        lines = [f"□ {dl}"]
        lines.append(f"  [{grp}] {cat} {title[:22]}")
        if notes:
            lines.append(f"  {notes[:28]}")
        return lines

    def done_row(t):
        grp, cat, title = parse_task(t)
        return f"■ [{grp}] {cat} {title[:20]}"

    def section(label, items, count):
        lines = [f"{label}  ({count})", f"{'─' * W}"]
        if not items:
            lines.append("(なし)")
        else:
            for t in items:
                lines += row(t)
                lines.append("")
        return lines

    out = []
    out.append(f"DON'S TASKS")
    out.append(f"{today_fmt}  {time_fmt} synced")
    out.append(f"{'━' * W}")
    out.append("")

    out += section("OVERDUE", overdue, len(overdue))
    out += section("TODAY", today_t, len(today_t))
    out += section("FUTURE", future, len(future))
    out += section("NO LIMIT", no_limit, len(no_limit))

    out.append(f"{'─' * W}")
    out.append(f"COMPLETED  (直近{len(recent_done)}件)")
    out.append(f"{'─' * W}")
    if recent_done:
        for t in recent_done:
            out.append(done_row(t))
    else:
        out.append("(なし)")
    out.append("")
    out.append(f"{'━' * W}")

    display_path = DATA_DIR / "task_display.txt"
    display_path.write_text("\n".join(out), encoding="utf-8")


def parse_task(task: dict) -> tuple:
    """タスクから (group, cat, title) を抽出。notes の [GROUP/CAT] を優先"""
    import re
    notes = task.get("notes", "") or ""
    name = task.get("name", "")

    # notes から [WRK/mngt] 形式を抽出
    match = re.match(r"\[(WRK|PRV)/(\w+)\]", notes)
    if match:
        return match.group(1), match.group(2), name

    # title にプレフィックスが残っている場合
    parts = name.split("_", 2)
    if len(parts) >= 3 and parts[0] in ("WRK", "PRV"):
        return parts[0], parts[1], parts[2]

    return "WRK", "misc", name


def fmt_date(d: str) -> str:
    if not d:
        return "-"
    try:
        dt = date.fromisoformat(d[:10])
        return f"{dt.strftime('%m-%d')} ({DAYS[dt.weekday()]})"
    except Exception:
        return d[:10]


if __name__ == "__main__":
    main()
