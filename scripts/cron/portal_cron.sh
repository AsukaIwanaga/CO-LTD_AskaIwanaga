#!/bin/bash
# ポータル通達取得 — cronから呼ばれるラッパー（深夜2時 毎日実行）

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
PYTHON="/opt/anaconda3/bin/python3"
LOG="$PROJECT_DIR/drafts/portal_cron_$(date +%Y-%m-%d).log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ポータル通達取得 開始" >> "$LOG"
cd "$PROJECT_DIR"
"$PYTHON" "$PROJECT_DIR/scripts/scrapers/portal.py" --headless >> "$LOG" 2>&1
EXIT_CODE=$?
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ポータル通達取得 完了 (exit: $EXIT_CODE)" >> "$LOG"
