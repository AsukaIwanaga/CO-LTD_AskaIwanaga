## 現在の状態（2026-03-31 21:30）

### ✅ 本日完了（全量）

**朝のルーティン**
- /morning STEP 1〜8 完了（ブリーフィング・音声・メール送信）
- 下書きメール2通送信（private + work）

**店舗移動対応**
- stx_kanrihyo.py / area_events.py / .env を GT保土ヶ谷駅前(017807)に全面切替
- STX保土ヶ谷駅前 2月・3月分データ取得・DB保存
- portal.py の店舗選択を保土ヶ谷に変更

**portal.py 全面修正**
- 本文取得: JS evaluate → Playwright locator.click() に変更
- フレーム検出: STRViewNotice パターン追加 + 既知フレーム除外
- 作業通達: category（親通達名）でのマッチング追加
- PDFダウンロード: 3段フォールバック（expect_download / 新タブ / URL直接）
- UI要素除去: _clean_notice_body() で「主旨」「内容」以降のみ抽出
- headless対応 + パスキーチャレンジ3回リトライ

**Phase 1A: 共通基盤構築**
- .env に ANTHROPIC_API_KEY 追加
- scripts/lib/ モジュール群作成
  - config.py / data_loader.py / claude_client.py / collectors.py
  - google_api.py / mailer.py / notifier.py / google_auth_setup.py
  - line_api.py / task_sync.py / text_utils.py
- Google OAuth 再認証（private + work、Gmail/Calendar/Tasks スコープ）
- GCP Console で work アカウントをテストユーザーに追加
- anthropic SDK インストール

**リポジトリ構造移行**
- scripts/ サブディレクトリ化（scrapers/ tools/ auth/ cron/ agents/ lib/）
- dev/ → planning/ 改称（経営企画部）
- .claude/commands/dev/ → .claude/commands/planning/
- 全スクリプト・ドキュメントのパス参照更新
- crontab パス更新
- 各部門 CLAUDE.md の旧パス（/LIFE/robco-terminal）修正

**タスク管理統合**
- Google Tasks ↔ tasks.json 双方向同期（task_sync.py）
- 命名規則自動タグ付け（title → 素名、notes → [WRK/mngt] タグ）
- 定期タスク自動再生成（完了履歴パターン検知）
- Google Tasks に tasks_create / tasks_complete / tasks_delete 実装
- tasks.json スキーマ拡張（google_task_id / google_list_id / notes）
- task_report.md + task_display.txt 自動生成
- DonsTask スキル（/consigliere:DonsTask）を動的スキルに改修
- overdue 13件完了処理

**部門スキル再編**
- sales = 店舗営業（stx / portal / events / shift / daily-report）
- general = 秘書庶務（gmail / calendar / log / memo / news / weather / quote）
- consigliere = タスク管理（DonsTask）
- studio に youtube 移管
- CLAUDE.md / consigliere.md / 各部門 CLAUDE.md 更新

**プロジェクト管理体制**
- project/ に will / active / done / archive 構成
- project/README.md にインデックス作成
- 週次提案報告の自動化（weekly_proposal.py → 毎週月曜 04:30 cron）
- will/ に3件の提案を起票・報告済み
- 部門再編プロジェクト → done
- cron 系4件 → active にプロジェクト化

**LINE Messaging API**
- LINE Developers チャネル作成・接続
- テキスト送信 + 画像送信（catbox.moe 経由）確認済み
- レシート風ブリーフィング画像 v16 確定
  - Menlo + ヒラギノ W3 フォント
  - 固定幅グリッド描画（65カラム、全角2セル）
  - Retina 3x 解像度（1685px幅）
  - 右寄せ数値、3行セクション間空白
  - sales: plan/tgt/act/diff/comp 均等右寄せカラム
  - habits: 固定カラム配置（CJK幅ズレ解消）
  - stocks: ガソリン・食料品価格（米・鶏もも・キャベツ・卵・牛乳）追加
  - 会場名: 日本語化
- LINE フォーマットルール策定（日本語中心・【】タイトル・①②・分割送信）

**メール報告**
- email-format-rules.md 策定（text/plain、33文字幅セパレータ）
- mailer.py を text/plain に確定

**GitHub**
- 2回 push 済み（a6df728, 842c882）

**その他**
- GitHub Actions 2件削除（国際ニュース / 営業関連外部要因情報）
- auじぶん銀行ローン → タスク化（04/05期限）
- Claude Agent SDK の調査・並行実行方式の評価ドキュメント作成
- Google Chat ↔ LINE 連携は見送り（セキュリティリスク）

### 🔲 次にやること（優先順）
1. **再起動後: studio 部門の映像関係処理**
2. **Claude API リセット後（4/1 09:00）**:
   - 画像生成スクリプト本番化（実データ → v16 → LINE送信）
   - Phase 1B: morning_auto.py 実装 + テスト + cron 登録
3. Phase 1C: 通達自動分析
4. Phase 1D: STX分析アラート
5. Phase 2: LINE Bot 秘書エージェント

### ⚠️ 未解決
- Claude API 月間利用制限（4/1 09:00 JST リセット）
- STORE_ACCOUNT メール設定（保留 → will/に提案済み）

### 環境・パス情報
- crontab:
  - 01:00 毎日: scripts/cron/rakushifu_sync_cron.sh
  - 02:00 毎日: scripts/cron/portal_cron.sh
  - 02:00 毎月15日: scripts/cron/stx_monthly_cron.sh
  - 04:00 毎日: scripts/cron/task_sync_cron.sh
  - 04:30 毎週月曜: scripts/cron/weekly_proposal_cron.sh
- LINE API: 接続済み（.env に設定済み）
- レシート画像: v16 確定
- テンプレート: .claude/letterbox/receipt-image-template（65文字幅）
- 設計書: planning/agent-automation-design.md
- 並行実行評価: planning/evaluation-parallel-execution.md
- プロジェクト一覧: project/README.md
- タスク一覧: data/task_display.txt
