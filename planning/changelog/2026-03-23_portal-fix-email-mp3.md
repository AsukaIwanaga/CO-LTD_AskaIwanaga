# 2026-03-23 セッション変更記録

## 変更ファイル

- `scripts/portal.py`
  - `DETAIL_DAYS`: 7 → 14日に拡張
  - `extract_schedules()` 追加：タイトル・本文・PDFから日付情報を抽出
  - `upsert_notices_db()` 追加：`portal_notices.json` への永続upsert
  - MM/DD 正規表現バグ修正：`(?<!\d)(\d{1,2})/(\d{1,2})(?!\d|/)` — YYYY/MM/DD内の誤マッチ防止
  - description 改善：ボイラープレート本文の場合はタイトルを使用
  - upsert ロジック修正：body/pdfsが空でもスケジュールは常に再抽出

- `scripts/tts_morning.py`
  - `to_mp3()` 関数追加：ffmpegでWAV→MP3変換
  - iCloudへMP3（WAVではなく）をコピーするよう変更

- `scripts/email_morning.py` （新規作成）
  - ブリーフィング本文 + MP3添付のmultipart/mixed MIMEメッセージを生成
  - private（asuka.ctn1@gmail.com）/ work（asuka.iwanaga@skylark.co.jp）の両方に対応
  - stdout に JSON形式で base64url MIME を出力 → Claude が mcp__gmail__send_message に渡す

- `.claude/commands/morning.md`
  - STEP 7（メール送信）追加：email_morning.py 実行 → Gmail MCP で送信
  - STEP 8（締め）に番号変更
  - STEP 6 の音声生成説明を更新（WAV→MP3変換の記載追加）

- `.claude/commands/consigliere.md`
  - 変更記録義務のセクション追加

- `README.md`
  - 全面更新：スキル一覧・データ構造・自動化設定・スキルファイル構成・変更履歴を整備

- `/LIFE/robco-terminal/data/portal_notices.json` （新規作成）
  - 29件の通達を初期投入（schedules・body・pdfs含む）

## 変更理由

- Don からの指示：ポータル通達の内容を14日間・詳細要約・PDF解析・日時抽出で充実化
- 朝のブリーフィング音声をスマホで聴きたい → メールにMP3添付で送信する方式を採用
- YouTube/Podcast等の検討を経て、メール添付が最もシンプルと判断
- README・変更記録管理の整備（今後のセッション引き継ぎのため）

## 動作確認

- portal.py 正規表現修正：✅ 無効日付(2026-26-03)が生成されなくなったことを確認
- portal_notices.json upsert：✅ 29件正常投入確認
- ffmpeg インストール：✅ /usr/local/bin/ffmpeg version 8.1
- tts_morning.py / email_morning.py：未確認（次回 /morning 実行時に検証）
