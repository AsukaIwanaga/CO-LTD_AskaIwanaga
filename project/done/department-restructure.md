# PROJECT: 部門スキル再編

**起票**: 2026-03-31
**元提案**: project/will/will-2026-03-31-department-restructure.md
**ステータス**: 進行中

---

## 概要

sales を店舗営業特化、general を秘書・庶務に再編する。

## 変更一覧

### sales (Sonny) → 店舗営業

| 変更 | スキル | 内容 |
|------|--------|------|
| 残留 | daily-report | 営業日報 |
| 新設 | stx | STX 営業データ確認・分析 |
| 新設 | events | 周辺イベント情報 |
| 新設 | shift | シフト管理（らくしふ） |
| 移管（← general） | portal | ポータル通達 |
| 移管（→ studio） | youtube | YouTube 台本生成 |
| 移管（→ general） | gmail | メール |
| 移管（→ general） | calendar | カレンダー |
| 移管（→ consigliere） | task | タスク管理（DonsTask として統合済み） |

### general (Clemenza) → 秘書・庶務

| 変更 | スキル | 内容 |
|------|--------|------|
| 移管（← sales） | gmail | メール |
| 移管（← sales） | calendar | カレンダー |
| 残留 | log | ログ |
| 残留 | memo | メモ |
| 残留 | news | ニュース |
| 残留 | weather | 天気 |
| 残留 | quote | 名言 |
| 移管（→ sales） | portal | ポータル通達 |

### consigliere

| 変更 | スキル | 内容 |
|------|--------|------|
| 統合済み | DonsTask | タスク管理（sales:task から移管済み） |

### studio

| 変更 | スキル | 内容 |
|------|--------|------|
| 移管（← sales） | youtube | YouTube 台本生成 |

## 実施タスク

- [ ] .claude/commands/sales/gmail.md → .claude/commands/general/gmail.md
- [ ] .claude/commands/sales/calendar.md → .claude/commands/general/calendar.md
- [ ] .claude/commands/sales/youtube.md → .claude/commands/studio/youtube.md
- [ ] .claude/commands/sales/task.md → 削除（DonsTask に統合）
- [ ] .claude/commands/general/portal.md → .claude/commands/sales/portal.md
- [ ] .claude/commands/sales/stx.md 新規作成
- [ ] .claude/commands/sales/events.md 新規作成
- [ ] .claude/commands/sales/shift.md 新規作成
- [ ] sales/CLAUDE.md 更新
- [ ] general/CLAUDE.md 更新
- [ ] CLAUDE.md 担当者マッピング更新
- [ ] README.md 更新
