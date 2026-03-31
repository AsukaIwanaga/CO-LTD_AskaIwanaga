# 日報生成（営業部）

今日のデータを集約して日報を自動生成します。

## 生成フロー

以下の順に情報を収集して日報を生成してください：

### 1. 天気を取得
Open-Meteo API で横浜の天気を取得する：
```
https://api.open-meteo.com/v1/forecast?latitude=35.4437&longitude=139.6380&current=temperature_2m,weathercode,windspeed_10m&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=Asia%2FTokyo&forecast_days=1
```

### 2. 今日の予定を取得
MCP `gcal_list_events` で本日の予定を取得する。

### 3. 未完了タスクを取得
`/Users/askaiwanaga/LIFE/robco-terminal/data/tasks.json` を読み込み、未完了かつ期限が今日以前のタスクを抽出する。

### 4. 習慣の達成状況を確認
`/Users/askaiwanaga/LIFE/robco-terminal/data/habits.json` と `habit_log.json` を読み込み、今日チェック済みの習慣を確認する。

### 5. 日報を生成
以下のフォーマットで出力する：

```
╔══════════════════════════════════════╗
║     DAILY REPORT — YYYY-MM-DD (曜日)  ║
╚══════════════════════════════════════╝

🌤 天気（横浜）
  現在: XX°C / 天気
  今日: 最高XX°C / 最低XX°C

📅 今日の予定
  HH:MM — [予定名]
  （予定なし）

📋 本日期限のタスク
  ❗ [タスク名] [HIGH]
  • [タスク名] [MEDIUM]
  （なし）

✅ 習慣チェック状況
  ■ ランニング（完了）
  □ ログ入力（未完了）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
