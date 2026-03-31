#!/bin/bash
# STX 営業管理表 月次自動取得 — cronから呼ばれるラッパー
# 毎月15日に前月+当月の両店舗分を取得してDBに保存する

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
PYTHON="/opt/anaconda3/bin/python3"
STX="$PROJECT_DIR/scripts/scrapers/stx_kanrihyo.py"
LOG="$PROJECT_DIR/drafts/stx_monthly_$(date +%Y-%m-%d).log"

# 前月を計算（例: 4月実行 → 3月分）
PREV_MONTH=$(date -v-1m +%Y-%m)
CURR_MONTH=$(date +%Y-%m)

echo "[$(date '+%Y-%m-%d %H:%M:%S')] STX月次取得 開始" >> "$LOG"
cd "$PROJECT_DIR"

# 保土ヶ谷駅前(017807) - 前月
echo "--- 017807 前月($PREV_MONTH) ---" >> "$LOG"
"$PYTHON" "$STX" --store 017807 --month "$PREV_MONTH" --headless >> "$LOG" 2>&1

# 保土ヶ谷駅前(017807) - 当月
echo "--- 017807 当月($CURR_MONTH) ---" >> "$LOG"
"$PYTHON" "$STX" --store 017807 --month "$CURR_MONTH" --headless >> "$LOG" 2>&1

# みなとみらい(018974) - 前月
echo "--- 018974 前月($PREV_MONTH) ---" >> "$LOG"
"$PYTHON" "$STX" --store 018974 --month "$PREV_MONTH" --headless >> "$LOG" 2>&1

# みなとみらい(018974) - 当月
echo "--- 018974 当月($CURR_MONTH) ---" >> "$LOG"
"$PYTHON" "$STX" --store 018974 --month "$CURR_MONTH" --headless >> "$LOG" 2>&1

EXIT_CODE=$?
echo "[$(date '+%Y-%m-%d %H:%M:%S')] STX月次取得 完了 (exit: $EXIT_CODE)" >> "$LOG"

# 失敗時に通知用ファイルを残す
if [ $EXIT_CODE -ne 0 ]; then
    echo "STX月次取得に失敗しました。手動で実行してください。" > "$PROJECT_DIR/drafts/stx_monthly_FAILED.txt"
fi
