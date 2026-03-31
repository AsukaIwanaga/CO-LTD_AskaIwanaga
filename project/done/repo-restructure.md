# PROJECT: リポジトリ構造移行

**起票**: 2026-03-31
**親プロジェクト**: system-migration.md
**ステータス**: 実行中

---

## 1. 移行内容

### A. ディレクトリ移動

| # | 現在 | 移動先 | 理由 |
|---|------|--------|------|
| A1 | dev/ | planning/ | 経営企画部に改称 |
| A2 | .claude/commands/dev/ | .claude/commands/planning/ | スキル定義の同期 |
| A3 | sample/ | drafts/sample/ | 一時ファイルは drafts/ に集約 |

### B. scripts/ サブディレクトリ化

| # | ファイル | 移動先 | 分類 |
|---|---------|--------|------|
| B1 | scripts/portal.py | scripts/scrapers/ | スクレイピング |
| B2 | scripts/stx_kanrihyo.py | scripts/scrapers/ | スクレイピング |
| B3 | scripts/rakushifu_sync.py | scripts/scrapers/ | スクレイピング |
| B4 | scripts/area_events.py | scripts/scrapers/ | スクレイピング |
| B5 | scripts/mf_balance.py | scripts/scrapers/ | スクレイピング |
| B6 | scripts/tts_morning.py | scripts/tools/ | ユーティリティ |
| B7 | scripts/email_morning.py | scripts/tools/ | ユーティリティ |
| B8 | scripts/record_event_outcome.py | scripts/tools/ | ユーティリティ |
| B9 | scripts/resas_flow.py | scripts/tools/ | 分析ツール |
| B10 | scripts/portal_login.py | scripts/auth/ | 認証 |
| B11 | scripts/stx_login.py | scripts/auth/ | 認証 |
| B12 | scripts/mf_login.py | scripts/auth/ | 認証 |
| B13 | scripts/portal_inspect.py | scripts/auth/ | デバッグ |
| B14 | scripts/*_cron.sh (3本) | scripts/cron/ | cron ラッパー |

### C. スクリプト内パス修正（相対パス `../` → `../../`）

| # | ファイル | 修正対象 |
|---|---------|---------|
| C1 | portal.py | `load_dotenv`, `OUTPUT_PATH`, `NOTICES_DB_PATH` |
| C2 | stx_kanrihyo.py | `load_dotenv`, `STATE_PATH` |
| C3 | rakushifu_sync.py | `DRAFTS_DIR` |
| C4 | area_events.py | `event_impact.json` パス |
| C5 | mf_balance.py | `SESSION_PATH`, `FINANCIAL_PATH` |
| C6 | resas_flow.py | `out_path` (drafts/) |
| C7 | record_event_outcome.py | 要確認 |
| C8 | portal_login.py | `load_dotenv` |
| C9 | stx_login.py | `load_dotenv` |
| C10 | mf_login.py | `load_dotenv` |

### D. cron.sh 内パス修正（SCRIPT_DIR 起点のスクリプト呼出）

| # | ファイル | 修正内容 |
|---|---------|---------|
| D1 | portal_cron.sh | `$SCRIPT_DIR/portal.py` → `$SCRIPT_DIR/../scrapers/portal.py` |
| D2 | rakushifu_sync_cron.sh | `$SCRIPT_DIR/rakushifu_sync.py` → `$SCRIPT_DIR/../scrapers/rakushifu_sync.py` |
| D3 | stx_monthly_cron.sh | `$SCRIPT_DIR/stx_kanrihyo.py` → `$SCRIPT_DIR/../scrapers/stx_kanrihyo.py` |

### E. lib/collectors.py のスクリプト呼出パス修正

| # | 関数 | 修正内容 |
|---|------|---------|
| E1 | _run_script | `SCRIPTS_DIR / script_name` → サブディレクトリ対応に変更 |
| E2 | run_portal_headless | `"portal.py"` → `"scrapers/portal.py"` |
| E3 | run_stx_summary | `"stx_kanrihyo.py"` → `"scrapers/stx_kanrihyo.py"` |
| E4 | run_area_events | `"area_events.py"` → `"scrapers/area_events.py"` |
| E5 | run_rakushifu_sync | `"rakushifu_sync.py"` → `"scrapers/rakushifu_sync.py"` |

### F. ドキュメント更新

| # | ファイル | 更新内容 |
|---|---------|---------|
| F1 | CLAUDE.md | スクリプトパス更新 + dev→planning + 担当者マッピング更新 |
| F2 | README.md | スクリプト一覧更新 + dev→planning |
| F3 | SESSION.md | dev→planning のパス参照更新 |
| F4 | .claude/commands/morning.md | スクリプト実行パス更新 |
| F5 | .claude/commands/general/portal.md | portal.py パス更新 |
| F6 | .claude/commands/consigliere.md | dev→planning 更新 |
| F7 | project/system-migration.md | 構造変更を反映 |
| F8 | planning/agent-automation-design.md | スクリプトパス更新（移動後） |

### G. 設定ファイル更新

| # | ファイル | 更新内容 |
|---|---------|---------|
| G1 | .claude/settings.local.json | portal.py の許可パス更新 |
| G2 | crontab | 絶対パスを scripts/cron/ に更新 |

### H. 部門 CLAUDE.md の旧参照削除

| # | ファイル | 更新内容 |
|---|---------|---------|
| H1 | sales/CLAUDE.md | /LIFE/robco-terminal 旧パス削除 + 正パス明記 |
| H2 | finance/CLAUDE.md | 同上 |
| H3 | general/CLAUDE.md | 同上 |
| H4 | hr/CLAUDE.md | 同上 |

---

## 2. MECE チェック

### 対象ファイル網羅性

- [x] scripts/ 直下の全 .py ファイル（13本）→ 全てサブディレクトリに分類済み
- [x] scripts/ 直下の全 .sh ファイル（3本）→ scripts/cron/ に移動
- [x] scripts/lib/ → 移動なし（E1-E5 でパス修正のみ）
- [x] dev/ 配下の全ファイル → planning/ に移動
- [x] .claude/commands/ 全スキル → dev→planning 改称のみ
- [x] data/ → 移動なし
- [x] drafts/ → 移動なし（sample/ を受け入れ）
- [x] 各部門フォルダ → 移動なし（CLAUDE.md のパス修正のみ）
- [x] ルート設定ファイル (.env, .mcp.json, .gitignore) → 変更なし
- [x] crontab → 絶対パス更新

### 分類の排他性

- scrapers/: 外部サイトにアクセスしてデータを取得するスクリプト
- tools/: ローカル処理のユーティリティ（TTS, メール, 分析）
- auth/: ログイン検証・セッション管理
- cron/: cron ラッパーシェルスクリプト
- agents/: 自律実行エージェント（Phase 1B以降で追加）
- lib/: 共通モジュール

→ 全スクリプトが1カテゴリにのみ属する ✅

---

## 3. 実行順序

1. ディレクトリ作成（scripts/scrapers/, tools/, auth/, cron/, agents/, planning/）
2. ファイル移動（A1-A3, B1-B14）
3. スクリプト内パス修正（C1-C10）
4. cron.sh パス修正（D1-D3）
5. lib/collectors.py 修正（E1-E5）
6. ドキュメント更新（F1-F8）
7. 設定ファイル更新（G1-G2）
8. 部門 CLAUDE.md 更新（H1-H4）
9. 動作確認
10. 旧ディレクトリ削除
