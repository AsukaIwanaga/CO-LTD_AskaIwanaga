# PROJECT: ポータル通達 自動取得

**起票**: 2026-03-31
**ステータス**: 稼働中
**cron**: `0 2 * * *` (毎日 02:00)
**スクリプト**: scripts/cron/portal_cron.sh → scripts/scrapers/portal.py --headless
**出力**: drafts/portal_latest.json, data/portal_notices.json
**ログ**: drafts/portal_cron_YYYY-MM-DD.log

## 概要
すかいらーくポータルに headless Playwright でログインし、通達一覧・本文・PDFを取得。
portal_notices.json に全履歴を蓄積。

## 監視ポイント
- Google OAuth セッション切れ → パスワード認証で自動切替済み
- headless パスキーチャレンジ → 3回リトライ実装済み
- 作業通達のゼロ幅スペース → _strip_zwsp() で自動除去
- PDFダウンロード → 3段フォールバック（expect_download / 新タブ / URL直接）
