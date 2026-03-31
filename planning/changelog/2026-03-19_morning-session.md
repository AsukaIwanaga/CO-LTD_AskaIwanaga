# 指示記録 — 2026-03-19 朝セッション

## 概要

朝のブリーフィング（`/morning`）実施後に発生した改修・整理の記録。

---

## 1. ポータル通達スクリプトの本文・PDF対応

**経緯**
`portal.py` が取得していたのはタイトル・カテゴリ・日付・発行部門のみだった。
通達の本文を確認するためにはポータルに直接ログインする必要があり非効率。

**対応内容**
`scripts/portal.py` を全面改修。

- 直近 `DETAIL_DAYS`（デフォルト7日）以内の通達に対し、詳細ページをクリックして**本文テキストを取得**
- 詳細ページ内の **PDF リンクを自動検出**（`href` / `onclick` 両対応）
- PDF をダウンロード → テキスト抽出 → 削除
  - 通常テキスト抽出: `pdfplumber` → `fitz (PyMuPDF)` → `pypdf` の順で試行
  - **イラスト主体のPDF（テキスト抽出が50文字未満）**: `fitz` でページを PNG 画像化（2x解像度）→ Claude Vision API（`claude-haiku-4-5`）で OCR
  - PDF種別を自動判別: `manual`（手順書・マニュアル）/ `detail`（通達詳細）
- 保存形式（各通達に追記）:
  ```json
  {
    "body": "本文テキスト",
    "pdfs": [
      { "filename": "example.pdf", "type": "manual", "text": "..." }
    ]
  }
  ```

---

## 2. 朝のブリーフィング自動化の廃止

**経緯**
自動起動（cron + スクリプト）は廃止し、VSCode のチャットから手動で `/morning` または「朝のレポートを出して」と伝える運用に変更。

**対応内容**

- `scripts/check_morning.sh` を削除（毎分起動・時刻チェックスクリプト）
- `scripts/launch_morning.sh` を削除（Terminal 起動・音声挨拶・Claude Code 起動スクリプト）
- `CLAUDE.md` から「朝の起動時刻設定ルール」セクションを削除

---

## 3. モーニングレポートのファイル保存

**経緯**
ブリーフィング内容をチャット表示だけでなくファイルとして残したい。

**対応内容**
`.claude/commands/morning.md` に **STEP 5: レポート保存** を追加。

- 保存先: `./drafts/morning_report_MM-dd_HH-mm.md`
- 内容: STEP 2 のブリーフィング表示 + STEP 3 の未記録チェック結果
- ファイル名のコロンはハイフンに置換（OS互換のため `HH:mm` → `HH-mm`）

---

## 4. CLAUDE.md への朝の確認ルール追記

**経緯**
`--dangerously-skip-permissions` での実行時に、不要なツール確認はスキップしつつ、
Don I. への確認が必要なインタラクションを確実に実施させたい。

**対応内容**
`CLAUDE.md` に「朝のブリーフィング確認ルール」セクションを追加。

| 区分 | 内容 |
|---|---|
| 自動実行OK | 天気・株価・ポータル取得、ファイル読み取り、画面表示 |
| 必ず確認 | 習慣チェック回答・タスク更新・ログ漏れ対応・各種JSON書き込み前 |

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `scripts/portal.py` | 全面改修（本文・PDF・Vision OCR対応） |
| `scripts/check_morning.sh` | 削除 |
| `scripts/launch_morning.sh` | 削除 |
| `.claude/commands/morning.md` | STEP 5（レポート保存）追加・STEP 6に締め繰り下げ |
| `CLAUDE.md` | 朝の確認ルール追加・起動時刻設定ルール削除 |
