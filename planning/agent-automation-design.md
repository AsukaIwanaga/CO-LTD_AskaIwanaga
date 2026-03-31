# エージェント自動化システム 設計書

## 概要

CO-LTD_AskaIwanaga に4つの自動化機能を追加する。
Phase 1（Feature 1/2/3）は Claude API + cron、Phase 2（Feature 6）は LINE Bot + Agent SDK。

---

## 全体アーキテクチャ

```
                       ┌────────────────────────────────────────┐
                       │            crontab (macOS)             │
                       │  01:00  rakushifu_sync_cron.sh    (既存)│
                       │  02:00  portal_cron.sh            (既存)│
                       │  02:00 15日 stx_monthly_cron.sh   (既存)│
                       │  02:30  portal_analysis_cron.sh   (新規)│
                       │  05:00  morning_auto_cron.sh      (新規)│
                       │  23:00  stx_analysis_cron.sh      (新規)│
                       └──────────┬─────────────────────────────┘
                                  │
        ┌─────────────────────────▼──────────────────────────────┐
        │                 Python スクリプト層                      │
        │  Feature 1: scripts/morning_auto.py                     │
        │  Feature 2: scripts/portal_analysis.py                  │
        │  Feature 3: scripts/stx_analysis.py                     │
        │  Feature 6: scripts/line_bot/app.py  (Phase 2)          │
        └────────┬──────────┬──────────┬─────────────────────────┘
                 │          │          │
        ┌────────▼──────────▼──────────▼─────────────────────────┐
        │             scripts/lib/ (共通モジュール)                │
        │  config.py       ... .env/パス定数/店舗設定             │
        │  google_api.py   ... Gmail/Calendar/Tasks API直接呼出  │
        │  claude_client.py... Anthropic SDK (Haiku/Sonnet)      │
        │  mailer.py       ... MIME構築 + Gmail API送信          │
        │  notifier.py     ... エラー通知 (メール+ログ)           │
        │  data_loader.py  ... tasks.json等ローカルJSON読み書き  │
        │  collectors.py   ... 天気/株価/外部API/subprocess収集  │
        └────────┬──────────┬──────────┬─────────────────────────┘
                 │          │          │
  ┌──────────────▼──┐ ┌────▼────┐ ┌───▼──────────────────────┐
  │ 既存スクリプト    │ │外部 API │ │ ローカルデータ            │
  │ portal.py        │ │Open-Meteo│ │ data/tasks.json          │
  │ stx_kanrihyo.py  │ │Yahoo Fin│ │ data/portal_notices.json  │
  │ area_events.py   │ │Claude AI│ │ data/stx_kanrihyo.db     │
  │ rakushifu_sync.py│ │Google   │ │ data/financial.json      │
  │ tts_morning.py   │ │Gmail API│ │ data/habits.json         │
  │ email_morning.py │ │GCal API │ │ data/habit_log.json      │
  └──────────────────┘ └─────────┘ └──────────────────────────┘
```

---

## 共通モジュール設計 (scripts/lib/)

### config.py
- PROJECT_DIR / DATA_DIR / DRAFTS_DIR / SCRIPTS_DIR のパス定数
- .env 読み込み（SKYLARK_*, ANTHROPIC_API_KEY）
- メール宛先: TO_PRIVATE / TO_WORK
- 店舗マップ: STORES = {"017807": "GT保土ヶ谷駅前", ...}
- Claude モデル定数: CLAUDE_HAIKU / CLAUDE_SONNET

### google_api.py
MCP は cron 環境で使えないため、Google API を直接呼ぶ。
- GoogleAuth クラス: OAuth トークン管理（private / work 2インスタンス）
  - gcp-oauth.keys.json + drafts/gcp_token_{private,work}.json
  - スコープ: gmail.readonly, gmail.send, calendar.readonly, tasks.readonly
- gmail_list_unread(account, max_results) → list[dict]
- gmail_send_raw(raw_base64, account) → dict
- calendar_list_events(date, calendar_ids) → list[dict]
- tasks_list_incomplete() → list[dict]
- 初回セットアップ: google_auth_setup.py で OAuth 認証フロー実行（手動）

### claude_client.py
- ClaudeClient クラス: anthropic SDK ラッパー
- generate(prompt, system, model, max_tokens) → str
- generate_briefing_text(data) → str  ... iPhone テンプレート形式
- generate_tts_script(data) → str      ... 読み上げ文生成
- analyze_notices(notices) → dict       ... 通達分析
- analyze_sales(sales_data, history) → dict  ... 営業分析
- デフォルト Haiku、必要時のみ Sonnet

### mailer.py
- build_mime(to, subject, body, attachments) → str (base64url)
- send_email(subject, body, to_private, to_work, attachments) → dict
- send_error_notification(feature, error, traceback) → None

### notifier.py
- notify_error(feature_name, error) → None
  - drafts/{feature}_error_{date}.log にトレースバック保存
  - mailer 経由でメール通知

### data_loader.py
- load_json / save_json
- load_tasks / save_tasks / load_habits / load_habit_log / load_financial / load_portal_notices

### collectors.py
外部データ収集。既存スクリプトは subprocess で呼ぶ。
- fetch_weather() → dict          ... Open-Meteo API
- fetch_stocks() → dict           ... Yahoo Finance v8 API
- run_portal_headless() → list    ... portal.py --headless
- run_stx_summary() → dict       ... stx_kanrihyo.py --summary
- run_area_events() → list        ... area_events.py --format json
- run_rakushifu_sync() → dict     ... rakushifu_sync.py --headless

---

## Feature 1: 完全自律型モーニングブリーフィング

### ファイル
- scripts/morning_auto.py
- scripts/morning_auto_cron.sh

### フロー
```
05:00 cron
  ├─ VOICEVOX 起動（cron.sh内で open -a → sleep 10）
  │
  ├─ STEP 1: 情報収集（逐次実行、安定性優先）
  │   ├─ fetch_weather()           → Open-Meteo
  │   ├─ fetch_stocks()            → Yahoo Finance
  │   ├─ load_portal_notices()     → portal_notices.json（02:00に更新済み）
  │   ├─ run_stx_summary()         → stx_kanrihyo.py
  │   ├─ run_area_events()         → area_events.py
  │   ├─ run_rakushifu_sync()      → rakushifu_sync.py
  │   ├─ gmail_list_unread()       → Gmail API (private + work)
  │   ├─ calendar_list_events()    → Calendar API
  │   ├─ tasks_list_incomplete()   → Tasks API
  │   ├─ load_tasks()              → tasks.json
  │   ├─ load_habits/habit_log()   → habits.json + habit_log.json
  │   └─ load_financial()          → financial.json
  │
  ├─ STEP 2-3: Claude Haiku でブリーフィング生成 + 未記録チェック
  │   ├─ generate_briefing_text(data) → iPhone テンプレート形式
  │   └─ check_missing_records(data)  → 未記録項目の検出
  │
  ├─ STEP 5: レポート保存
  │   └─ drafts/morning_report_MM-dd_HH-mm.md
  │
  ├─ STEP 6: 音声化
  │   └─ tts_morning.py --no-play → drafts/morning_audio_YYYY-MM-DD.mp3
  │   （VOICEVOX未起動時はスキップ）
  │
  └─ STEP 7: メール送信
      └─ Gmail API send (private + work、MP3添付)
```

### STEP 4（対話）は省略
自律実行のため Don との対話ステップはスキップ。
未記録チェック結果はブリーフィング本文に含めて通知。

### Claude Haiku プロンプト
- system: iPhone テンプレート (.claude/letterbox/morning-breafing-template-iphone) を埋め込み
- user: 全収集データを JSON で渡す
- コスト: ~$0.02/日

---

## Feature 2: ポータル通達 自動分析・全件通知

### ファイル
- scripts/portal_analysis.py
- scripts/portal_analysis_cron.sh
- data/portal_analyzed.json（分析済みID一覧）

### フロー
```
02:30 cron（portal_cron.sh の30分後）
  │
  ├─ portal_latest.json を読む
  ├─ portal_analyzed.json で既分析IDを除外
  ├─ 新規通達を Claude Haiku で分析
  │   ├─ 重要度判定: 緊急 / 要対応 / 情報周知
  │   ├─ 各通達の要約生成
  │   └─ 期限付きタスク抽出
  │
  ├─ タスク自動追加 → tasks.json
  │   └─ quest_id = 通達ID でリンク
  │
  ├─ 全件通知メール送信（重要度順）
  │   ├─ 🔴 緊急
  │   ├─ 🟡 要対応
  │   └─ 🔵 情報周知
  │
  └─ portal_analyzed.json 更新
```

### コスト: ~$0.01/日

---

## Feature 3: STX 営業データ 自動分析・アラート

### ファイル
- scripts/stx_analysis.py
- scripts/stx_analysis_cron.sh
- data/stx_alert_thresholds.json（アラート閾値）

### アラート閾値
```json
{
  "guest_drop_pct": -15.0,    // 客数前日比 -15% 以下
  "labor_rate_max": 35.0,     // 人件費率 35% 超過
  "sales_drop_pct": -20.0,    // 売上前日比 -20% 以下
  "cum_rate_warning": 95.0    // 月累計達成率 95% 未満
}
```

### フロー
```
23:00 cron（当日データ確定後）
  │
  ├─ stx_kanrihyo.db から最新データ取得
  │   ├─ 最新日の全店舗データ
  │   ├─ 前日データ
  │   ├─ 月累計
  │   └─ 直近2ヶ月平均
  │
  ├─ 閾値ベース異常値検知
  │   ├─ 客数急減 / 売上急減
  │   ├─ 人件費率超過
  │   └─ 月累計達成率低下
  │
  ├─ Claude Haiku でトレンド分析
  │
  ├─ アラートあり → メール通知
  │
  └─ 月末 → 月次トレンドレポートも生成・送信
```

### コスト: ~$0.005/日

---

## Feature 6: 秘書エージェント LINE Bot（Phase 2 概要設計）

### アーキテクチャ
```
LINE → Webhook → Flask/FastAPI → Claude Agent SDK → lib/ のツール群
```

### ファイル構成（Phase 2）
```
scripts/line_bot/
  app.py           # Flask + LINE Webhook
  agent.py         # Claude Agent SDK エージェント定義
  tools.py         # エージェントツール（lib/ をラップ）
  line_client.py   # LINE Messaging API
```

### エージェントツール
get_weather / get_stocks / get_tasks / add_task / get_sales /
get_notices / get_calendar / check_habit / run_briefing / get_financial

### 前提条件
- LINE Developers アカウント作成（未所持）
- Webhook ホスティング（Mac 常時起動 or VPS）
- Claude Agent SDK (claude-agent-sdk)
- 対話時は Sonnet 使用（~$0.02/対話）

---

## 実装順序

### Phase 1A: 共通基盤（1-2日）
1. .env に ANTHROPIC_API_KEY 追加
2. scripts/lib/ 作成（config → google_api → data_loader → claude_client → collectors → mailer → notifier）
3. Google OAuth 再認証（Gmail/Calendar/Tasks スコープ追加、private + work）

### Phase 1B: Feature 1 モーニングブリーフィング（2-3日）
4. morning_auto.py 実装
5. Claude プロンプト調整（iPhone テンプレート）
6. テスト → cron 登録（0 5 * * *）
7. 2-3日モニタリング

### Phase 1C: Feature 2 通達分析（1-2日）
8. portal_analysis.py 実装
9. テスト → cron 登録（30 2 * * *）

### Phase 1D: Feature 3 STX 分析（1-2日）
10. stx_analysis.py + stx_alert_thresholds.json 実装
11. テスト → cron 登録（0 23 * * *）

### Phase 2: Feature 6 LINE Bot（Phase 1 安定後）
12. LINE Developers セットアップ
13. line_bot/ 実装
14. テスト → デプロイ

---

## 最終 crontab

```
# 既存
0  1  *  * *  rakushifu_sync_cron.sh
0  2  *  * *  portal_cron.sh
0  2  15 * *  stx_monthly_cron.sh

# 新規
30 2  *  * *  portal_analysis_cron.sh    ← portal 取得の30分後
0  5  *  * *  morning_auto_cron.sh       ← 毎朝5時
0  23 *  * *  stx_analysis_cron.sh       ← 毎晩23時
```

---

## コスト見積もり（月額）

| Feature | モデル | 日額 | 月額 |
|---------|--------|------|------|
| 1 モーニング | Haiku | ~$0.02 | ~$0.60 |
| 2 通達分析 | Haiku | ~$0.01 | ~$0.30 |
| 3 STX分析 | Haiku | ~$0.005 | ~$0.15 |
| 6 LINE Bot | Sonnet | ~$0.02/対話 | ~$2-5 |
| **Phase 1 合計** | | | **~$1.05/月** |

---

## 注意事項

- **Google OAuth**: 現在のトークンスコープ不足。gmail.send/calendar.readonly/tasks.readonly を追加する再認証が初回のみ必要
- **VOICEVOX**: Mac スリープ時は起動不可。TTS失敗時は本文のみメール送信（フォールバック）
- **Playwright**: 既存 cron で headless 動作確認済み。同じ Python パスを使用
- **work メール送信**: asuka.iwanaga@skylark.co.jp 用の別トークンが必要（初回セットアップ時に取得）
