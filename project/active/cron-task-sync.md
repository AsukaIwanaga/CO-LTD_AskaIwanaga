# PROJECT: タスク同期 + 命名規則自動修正

**起票**: 2026-03-31
**ステータス**: 稼働中
**cron**: `0 4 * * *` (毎日 04:00)
**スクリプト**: scripts/cron/task_sync_cron.sh → scripts/agents/task_sync_runner.py
**出力**: data/tasks.json, data/task_report.md, data/task_display.txt
**ログ**: drafts/task_sync_YYYY-MM-DD.log

## 概要
Google Tasks ↔ tasks.json の双方向同期。
命名規則（GROUP_CATEGORY_TITLE）から外れたタスクを自動リネーム。
同期後に task_report.md（データ参照用）と task_display.txt（可読性表示用）を生成。

## 関連
- project/active/task-naming-enforcement.md（4月中の命名規則適用プロジェクト）
