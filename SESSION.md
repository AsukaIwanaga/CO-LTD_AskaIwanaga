## 現在の状態（2026-03-31 20:00）

### ✅ 本日完了
- /morning STEP 1〜8 完了
- 店舗移動対応（保土ヶ谷駅前に全面切替）
- portal.py 全面修正（本文・PDF・UI除去・headless）
- Phase 1A: 共通基盤構築（scripts/lib/ + Google OAuth）
- リポジトリ構造移行（scripts/ サブディレクトリ化、dev→planning）
- タスク管理統合（Google Tasks ↔ tasks.json 双方向同期 + 自動リネーム + 定期タスク再生成）
- 部門スキル再編（sales=店舗営業、general=秘書庶務）
- 週次提案報告の自動化（project/will/ → 毎週月曜メール）
- プロジェクト管理体制構築（will/active/done/archive）
- LINE Messaging API 接続（テキスト送信 + 画像送信 確認済み）
- レシート風ブリーフィング画像のプロトタイプ作成
- メール報告ルール策定（text/plain、33文字幅セパレータ）

### 🔲 次にやること（優先順）
1. **Claude API リセット後（4/1 09:00）**:
   - レシート画像生成スクリプト本番版作成（receipt-image-template ベース）
   - Phase 1B: morning_auto.py 実装 + テスト + cron 登録
2. **Phase 1C: 通達自動分析**
3. **Phase 1D: STX分析アラート**
4. **Phase 2: LINE Bot 秘書エージェント**

### ⚠️ 未解決
- Claude API 月間利用制限（4/1 09:00 リセット）
- STORE_ACCOUNT メール設定（保留 → will/に提案済み）

### 環境
- crontab:
  - 01:00 毎日: rakushifu_sync
  - 02:00 毎日: portal
  - 02:00 毎月15日: stx_monthly
  - 04:00 毎日: task_sync + レポート生成
  - 04:30 毎週月曜: weekly_proposal
- LINE API: 接続済み（.env に設定済み）
- テンプレート: .claude/letterbox/receipt-image-template（80文字幅レシート画像用）
- プロジェクト一覧: project/README.md
- タスク一覧: data/task_display.txt
