# PROJECT: システム移行・自動化基盤構築

**プロジェクト名**: ROBCO TERMINAL 自動化基盤構築
**起票**: 2026-03-31
**ステータス**: 進行中
**担当**: 経営企画部（旧 dev）

---

## 1. プロジェクト概要

CO-LTD_AskaIwanaga の運用を「Claude Code 手動実行」から「自律型エージェント + 人間の判断」に移行する。
各部門のスキル・データ・自動化を一貫した設計で統合し、Don の意思決定を最大限サポートする体制を構築する。

---

## 2. 部門構成の見直し

### 現行 → 新構成

| 現行 | 担当者 | 新構成 | 変更点 |
|------|--------|--------|--------|
| sales | Sonny | **sales** (営業部) | 変更なし |
| finance | Tom | **finance** (経理部) | 変更なし |
| general | Clemenza | **general** (庶務部) | 変更なし |
| hr | Connie | **hr** (人事部) | 変更なし |
| studio | 複数名 | **studio** (映像制作部) | 変更なし |
| dev | Michael | **planning** (経営企画部) | 改称。システム設計・全体最適化・プロジェクト管理を担当 |
| — | — | **agent** (自動化基盤) | 新設。自律実行スクリプト・共通ライブラリの管理 |

### 経営企画部 (planning) の役割
- 全体のシステム設計・アーキテクチャ見直し
- 部門間連携フローの設計
- 今後の拡張計画の策定
- プロジェクト管理

### 自動化基盤 (agent) の位置づけ
- scripts/lib/ の共通モジュール
- morning_auto.py / portal_analysis.py / stx_analysis.py
- cron ジョブ管理
- Phase 2 の LINE Bot

---

## 3. タスク管理: Google Tasks vs ローカル tasks.json

### 比較

| 観点 | Google Tasks | ローカル tasks.json |
|------|-------------|-------------------|
| **アクセス性** | スマホ・PC どこからでも | Claude Code セッション内のみ |
| **入力の手軽さ** | Google アシスタント、ウィジェット対応 | Claude Code に指示が必要 |
| **API** | REST API（cron から直接アクセス可） | ファイル読み書き |
| **履歴** | 完了済みも保持（2019年〜の履歴あり） | 手動削除しない限り残る |
| **構造** | title / due / notes のみ | priority / tag / regulation 等の拡張フィールド |
| **カテゴリ** | タイトル命名規則（WRK_/PRV_）で疑似分類 | tag フィールド (WORK/PRIVATE) |
| **自動化との相性** | Google API で直接 CRUD 可能 | ファイルロック不要、単純 |
| **Don の利用実態** | 日常的に使っている（18件の未完了タスク） | ほぼ未使用（2件のみ） |

### 推奨: Google Tasks を正（Single Source of Truth）にする

**理由:**
1. Don が日常的に使っている（実態に合わせる）
2. スマホからいつでも追加・確認できる
3. API 経由で cron スクリプトからも読み書き可能
4. Phase 2 の LINE Bot からも操作しやすい

**ローカル tasks.json の扱い:**
- 廃止ではなく「キャッシュ + 拡張メタデータ」として残す
- Google Tasks → tasks.json への同期を定期実行
- priority / tag / quest_id などの拡張情報は tasks.json 側に持つ
- 表示・分析はマージして使う

**同期フロー:**
```
Google Tasks (正)
    │ 定期同期（morning_auto 実行時）
    ▼
tasks.json (キャッシュ + 拡張メタ)
    │ portal_analysis.py がタスク追加 → Google Tasks にも反映
    ▼
ブリーフィング表示（マージ）
```

**必要な対応:**
- google_api.py に tasks_create() / tasks_complete() を追加
- tasks.json のスキーマに google_task_id フィールドを追加
- /sales:task スキルを Google Tasks ベースに改修

---

## 4. スキルと自動化の棲み分け

### 原則

```
自動化 (cron)     = 定型的・繰り返しの情報収集と通知
スキル (Claude Code) = 判断が必要な操作、対話的な確認、アドホックな指示
```

### 棲み分けマトリクス

| 機能 | 自動化 (cron) | スキル (Claude Code) | 関係 |
|------|-------------|---------------------|------|
| **ブリーフィング** | morning_auto.py (05:00) — 情報収集・レポート・メール | /morning — 対話的アップデート (STEP 4)、アドホック実行 | 自動が主、スキルは補完 |
| **通達** | portal_cron.sh (02:00) — 取得、portal_analysis.py (02:30) — 分析・通知 | /general:portal — 詳細確認、タスク化の判断 | 自動が取得+分析、スキルは深掘り |
| **営業データ** | stx_analysis.py (23:00) — 異常値検知・アラート | /sales:daily-report — 日報作成、分析の深掘り | 自動がアラート、スキルは活用 |
| **カレンダー** | morning_auto.py で取得 | /sales:calendar — 予定追加・変更の対話 | 読み取りは自動、書き込みはスキル |
| **メール** | morning_auto.py で取得 | /sales:gmail — 返信・下書き作成の対話 | 読み取りは自動、書き込みはスキル |
| **タスク** | portal_analysis.py でタスク自動追加 | /sales:task — 完了操作・手動追加の対話 | 追加は両方、完了操作はスキル |
| **習慣** | morning_auto.py で状況通知 | /hr:habit — チェック操作の対話 | 表示は自動、記録はスキル |
| **財務** | morning_auto.py で残高通知 | /finance:financial — 残高更新の対話 | 表示は自動、更新はスキル |
| **シフト** | rakushifu_sync_cron.sh (01:00) — 同期 | （なし — 完全自動） | 完全自動 |
| **天気・株価** | morning_auto.py で取得 | /general:weather, /finance:stocks — アドホック確認 | 自動が主、スキルは随時参照 |

### スキル改修方針

| スキル | 改修内容 |
|--------|---------|
| **/morning** | STEP 1-3, 5-7 は morning_auto.py に委譲。スキルは STEP 4（対話的アップデート）+ アドホック再実行に特化 |
| **/general:portal** | 自動分析結果を表示 + 詳細確認の対話に特化。取得は portal_cron.sh に委譲 |
| **/sales:task** | Google Tasks を正とした CRUD に改修。tasks.json は裏で同期 |
| **/sales:daily-report** | stx_analysis.py の分析結果を活用しつつ、日報フォーマット生成に特化 |

---

## 5. MCP vs API 直接呼出

### 比較

| 観点 | MCP (Claude Code 内) | API 直接呼出 (google_api.py) |
|------|---------------------|---------------------------|
| **利用環境** | Claude Code セッション内のみ | どこからでも（cron, LINE Bot 等） |
| **認証** | MCP サーバーが管理 | 自前で OAuth トークン管理 |
| **機能範囲** | MCP サーバーの実装次第 | Google API の全機能が使える |
| **安定性** | MCP サーバーの品質に依存 | 自前制御 |
| **トークン更新** | MCP が自動管理 | google_api.py で自動リフレッシュ |

### 推奨: 併用（用途で使い分け）

```
Claude Code セッション内（対話的操作）
  → MCP を使う（既存のまま）
  → 理由: Claude Code が自然にツール呼出しできる。設定済みで動作確認済み

cron / 自律スクリプト / LINE Bot
  → google_api.py を使う（新規）
  → 理由: MCP はセッション外で使えない。直接 API が唯一の選択肢
```

**同一データへの二重アクセスは問題なし** — Google API は冪等性があり、MCP も API もどちらから読み書きしても同じデータにアクセスする。

**トークン管理の統一は不要** — MCP と google_api.py のトークンは別管理で問題ない。スコープが異なる可能性があるため、むしろ分けた方が安全。

---

## 6. 全体フロー工程表

### Phase 1A: 共通基盤 ✅ 完了（2026-03-31）
- [x] scripts/lib/ モジュール群
- [x] Google OAuth (private + work)
- [x] .env に ANTHROPIC_API_KEY
- [x] 天気/Gmail/Calendar/Tasks API 動作確認

### Phase 1B: Feature 1 モーニングブリーフィング自動化
- [ ] morning_auto.py 実装
- [ ] Claude Haiku プロンプト調整
- [ ] テスト実行
- [ ] morning_auto_cron.sh + crontab 登録 (0 5 * * *)
- [ ] /morning スキルを対話特化に改修
- [ ] 2-3日モニタリング

### Phase 1C: Feature 2 通達自動分析
- [ ] portal_analysis.py 実装
- [ ] portal_analysis_cron.sh + crontab 登録 (30 2 * * *)
- [ ] /general:portal スキルを分析結果表示に改修
- [ ] タスク自動追加 → Google Tasks 連携

### Phase 1D: Feature 3 STX分析アラート
- [ ] stx_analysis.py 実装
- [ ] stx_alert_thresholds.json 作成
- [ ] stx_analysis_cron.sh + crontab 登録 (0 23 * * *)
- [ ] /sales:daily-report との連携

### Phase 1E: タスク管理統合
- [ ] google_api.py に tasks_create/complete 追加
- [ ] tasks.json スキーマ拡張 (google_task_id)
- [ ] 同期ロジック実装
- [ ] /sales:task を Google Tasks ベースに改修
- [ ] 古い Google Tasks の整理（Don の判断で完了/削除）

### Phase 1F: スキル改修
- [ ] /morning を対話特化に改修
- [ ] /general:portal を分析結果表示に改修
- [ ] /sales:task を Google Tasks 連携に改修
- [ ] CLAUDE.md の部門構成更新（dev → planning）
- [ ] planning/ ディレクトリ作成、project/ へのリンク

### Phase 2: Feature 6 LINE Bot 秘書エージェント
- [ ] LINE Developers アカウント作成
- [ ] scripts/line_bot/ 構築
- [ ] Claude Agent SDK 統合
- [ ] テスト → デプロイ

### 最終 crontab（Phase 1 全完了後）

```
01:00  毎日    rakushifu_sync_cron.sh     シフト同期
02:00  毎日    portal_cron.sh             通達取得
02:00  毎月15日 stx_monthly_cron.sh       STX月次データ
02:30  毎日    portal_analysis_cron.sh    通達分析・通知
05:00  毎日    morning_auto_cron.sh       モーニングブリーフィング
23:00  毎日    stx_analysis_cron.sh       営業データ分析
```

---

## 7. 部門間データフロー

```
                    ┌─────────────┐
                    │  Don (判断)  │
                    └──────┬──────┘
                           │ Claude Code / LINE Bot
                    ┌──────▼──────┐
                    │ consigliere │ ルーティング
                    └──────┬──────┘
          ┌────────────────┼────────────────────┐
          │                │                    │
    ┌─────▼─────┐  ┌──────▼──────┐  ┌──────────▼──────────┐
    │  planning  │  │   agent     │  │   各部門スキル       │
    │ (経営企画) │  │ (自動化基盤)│  │ sales/finance/       │
    │            │  │             │  │ general/hr/studio    │
    │ 設計・計画 │  │ cron実行    │  │ 対話的操作           │
    └─────┬─────┘  └──────┬──────┘  └──────────┬──────────┘
          │                │                    │
          │         ┌──────▼──────┐              │
          │         │ scripts/lib │◄─────────────┘
          │         │ 共通モジュール│  全部門が利用
          │         └──────┬──────┘
          │                │
          │    ┌───────────┼───────────┐
          │    │           │           │
          │ ┌──▼──┐  ┌────▼────┐  ┌───▼────┐
          │ │data/│  │Google   │  │外部API │
          │ │JSON │  │API      │  │天気/株 │
          │ │SQLite│  │Gmail    │  │ポータル│
          │ └─────┘  │Calendar │  │STX    │
          │          │Tasks    │  └────────┘
          │          └─────────┘
          │
    ┌─────▼─────┐
    │ project/  │
    │ 計画書    │
    │ 工程管理  │
    └───────────┘
```

---

## 8. リスク・課題

| # | 課題 | 対策 | 担当 |
|---|------|------|------|
| 1 | Claude API 月間制限 | Console で上限確認・調整 | Don |
| 2 | VOICEVOX cron 実行時のスリープ問題 | caffeinate or TTS失敗時フォールバック | agent |
| 3 | Google Tasks の古い残骸（2019年〜） | Don の判断で整理 | sales |
| 4 | MCP トークン期限切れ | 自動再認証フロー（feedback_auth_autofix） | agent |
| 5 | headless Playwright の安定性 | エラー時リトライ + メール通知 | agent |

---

## 変更履歴

| 日付 | 内容 |
|------|------|
| 2026-03-31 | 初版作成。Phase 1A 完了。設計書策定。 |
