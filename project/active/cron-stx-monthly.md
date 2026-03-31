# PROJECT: STX 営業管理表 月次自動取得

**起票**: 2026-03-31
**ステータス**: 稼働中
**cron**: `0 2 15 * *` (毎月15日 02:00)
**スクリプト**: scripts/cron/stx_monthly_cron.sh → scripts/scrapers/stx_kanrihyo.py
**出力**: data/stx_kanrihyo.db
**ログ**: drafts/stx_monthly_YYYY-MM-DD.log
**失敗通知**: drafts/stx_monthly_FAILED.txt

## 概要
毎月15日に前月+当月の両店舗（017807 保土ヶ谷 / 018974 みなとみらい）のSTXデータを取得しDBに保存。
ポータルは2ヶ月以上前のデータにアクセス不能になるため、月次で確実に取得する。
