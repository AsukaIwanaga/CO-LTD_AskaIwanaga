# 習慣管理（開発部）

習慣のチェック・確認を管理します。
データ:
- 習慣定義: `/Users/askaiwanaga/LIFE/robco-terminal/data/habits.json`
- チェックログ: `/Users/askaiwanaga/LIFE/robco-terminal/data/habit_log.json`

## データ構造

habits.json:
```json
[{ "id": "1", "name": "ランニング", "category": "HEALTH", "created_at": "2026-03-15" }]
```

habit_log.json:
```json
[{ "habit_id": "1", "date": "2026-03-18" }]
```

## 操作メニュー

### 1. 今日の習慣チェック状況を表示
両ファイルを読み込み、今日（YYYY-MM-DD）の達成状況を表示する：

```
✅ 習慣チェック — YYYY-MM-DD
─────────────────────────
■ ランニング           [HEALTH]   ✓ 完了
□ ログ入力             [OTHER]    未完了
■ ENG リスニング       [LEARNING] ✓ 完了
□ 一箇所4S            [HEALTH]   未完了
□ financial log入力    [HEALTH]   未完了
□ 営業管理表入力       [WORK]     未完了
─────────────────────────
達成: 2/6 (33%)
```

### 2. 習慣をチェック（完了にする）
チェックしたい習慣をユーザーに選んでもらい、`habit_log.json` に `{ "habit_id": "X", "date": "今日" }` を追記する。
既にチェック済みの場合は「すでに完了しています」と伝える。

### 3. チェックを取り消す
対象を確認してから `habit_log.json` から該当エントリを削除する。

### 4. 今月の達成率を確認
今月の各習慣の達成日数・達成率を表示する。

## 注意事項

- 日付は YYYY-MM-DD 形式で扱う
- 同じ habit_id + date の組み合わせは1件のみ保持する
