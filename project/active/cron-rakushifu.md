# PROJECT: らくしふシフト 自動同期

**起票**: 2026-03-31
**ステータス**: 稼働中
**cron**: `0 1 * * *` (毎日 01:00)
**スクリプト**: scripts/cron/rakushifu_sync_cron.sh → scripts/scrapers/rakushifu_sync.py --headless
**出力**: drafts/rakushifu_shifts_YYYY-MM.json, drafts/rakushifu_diff_YYYY-MM-DD.json
**ログ**: drafts/rakushifu_sync_YYYY-MM-DD.log

## 概要
らくしふに headless Playwright でログインし、未確認シフトを自動確認。
差分検知時は Google Calendar に自動反映。
