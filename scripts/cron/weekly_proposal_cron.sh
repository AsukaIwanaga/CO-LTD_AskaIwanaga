#!/bin/bash
# 週次提案報告 — cron ラッパー（毎週月曜 04:30）

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
PYTHON="/opt/anaconda3/bin/python3"
LOG="$PROJECT_DIR/drafts/weekly_proposal_$(date +%Y-%m-%d).log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] weekly_proposal 開始" >> "$LOG"
cd "$PROJECT_DIR"
"$PYTHON" "$PROJECT_DIR/scripts/agents/weekly_proposal.py" >> "$LOG" 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] weekly_proposal 完了 (exit: $?)" >> "$LOG"
