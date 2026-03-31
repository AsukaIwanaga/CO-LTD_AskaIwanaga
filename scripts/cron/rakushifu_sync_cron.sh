#!/bin/bash
# らくしふシフト自動同期 — cronから呼ばれるラッパー
# cronはPATHが限定的なため、絶対パスで指定する

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
PYTHON="/opt/anaconda3/bin/python3"
LOG="$PROJECT_DIR/drafts/rakushifu_sync_$(date +%Y-%m-%d).log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 同期開始" >> "$LOG"
cd "$PROJECT_DIR"
"$PYTHON" "$PROJECT_DIR/scripts/scrapers/rakushifu_sync.py" --headless >> "$LOG" 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 同期完了 (exit: $?)" >> "$LOG"
