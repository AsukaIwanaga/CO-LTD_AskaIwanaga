#!/bin/bash
# タスク同期 + 命名規則修正 — cron ラッパー
# crontab: 0 6 * * * (毎朝6時、morning_auto の後)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
PYTHON="/opt/anaconda3/bin/python3"
LOG="$PROJECT_DIR/drafts/task_sync_$(date +%Y-%m-%d).log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] task_sync 開始" >> "$LOG"
cd "$PROJECT_DIR"
"$PYTHON" "$PROJECT_DIR/scripts/agents/task_sync_runner.py" >> "$LOG" 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] task_sync 完了 (exit: $?)" >> "$LOG"
