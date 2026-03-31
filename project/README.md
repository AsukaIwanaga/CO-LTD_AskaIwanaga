# Projects

## ディレクトリ構成

| ディレクトリ | 用途 | 管理 |
|-------------|------|------|
| **will/** | 今後やりたい・やるべき提案（企画部門が随時追加OK） | 毎週月曜に Don へ提案報告 |
| **active/** | 現在進行中のプロジェクト | 随時更新 |
| **done/** | 完了したプロジェクト | 完了時に active/ から移動 |
| **archive/** | 完了後アーカイブ（稼働中 cron 等の運用記録） | active/ の運用が安定したら移動 |

## Will（提案・企画）

| プロジェクト | 概要 | 起票 |
|-------------|------|------|
| （企画部門が随時追加） | | |

## Active（進行中）

| プロジェクト | 概要 | cron |
|-------------|------|------|
| [system-migration](active/system-migration.md) | 自動化基盤構築（Phase 1B〜2） | - |
| [task-naming-enforcement](active/task-naming-enforcement.md) | タスク命名規則の自動適用（4月中） | - |
| [weekly-proposal](active/weekly-proposal.md) | 毎週月曜の提案報告 | 毎週月曜 04:30 |
| [cron-portal](active/cron-portal.md) | ポータル通達 自動取得 | 毎日 02:00 |
| [cron-rakushifu](active/cron-rakushifu.md) | らくしふシフト 自動同期 | 毎日 01:00 |
| [cron-stx-monthly](active/cron-stx-monthly.md) | STX 営業管理表 月次取得 | 毎月15日 02:00 |
| [cron-task-sync](active/cron-task-sync.md) | タスク同期 + 命名規則修正 | 毎日 04:00 |

## Done（完了）

| プロジェクト | 概要 | 完了日 |
|-------------|------|--------|
| [repo-restructure](done/repo-restructure.md) | リポジトリ構造移行 | 2026-03-31 |

## Archive（アーカイブ）

| プロジェクト | 概要 | アーカイブ日 |
|-------------|------|-------------|
| （安定稼働後に active/ から移動） | | |
