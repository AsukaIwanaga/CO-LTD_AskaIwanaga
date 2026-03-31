# Don's Task List

タスク一覧を Google Tasks と同期した最新状態で表示する。

## フロー

### STEP 1: 同期

```bash
python3 scripts/agents/task_sync_runner.py
```

を実行し、Google Tasks ↔ tasks.json を同期する。

### STEP 2: 表示

`data/tasks.json` を読み込み、以下のフォーマットで表示する。

**分類ルール:**
- overdue: 期限が今日より前
- today: 期限が今日
- future: 期限が明日以降
- no limit: 期限なし
- completed: 完了済み（直近5件のみ表示）

**命名規則:**
```
GROUP_CATEGORY_TITLE
  GROUP:    WRK(仕事) / PRV(プライベート)
  CATEGORY: mngt(管理), rsvt(予約), pchs(買い物), kpcl(家事), fnnc(金融), evnt(イベント), misc(その他)
```

**表示フォーマット:**
```
DON'S TASKS  (YYYY-MM-DD HH:MM synced)

overdue (X件)
status  deadline    grp  cat   title                          notes
--------------------------------------------------------------------------------
🔲      MM-DD (ddd) WRK  mngt  タスク名...                    メモ...
🔲      MM-DD (ddd) PRV  rsvt  タスク名...

today (X件)
--------------------------------------------------------------------------------
🔲      MM-DD (ddd) WRK  mngt  タスク名...

future (X件)
--------------------------------------------------------------------------------
🔲      MM-DD (ddd) PRV  fnnc  タスク名...

no limit (X件)
--------------------------------------------------------------------------------
🔲      -           WRK  mngt  タスク名...

completed (直近5件)
--------------------------------------------------------------------------------
✅      MM-DD       WRK  mngt  タスク名...
```

**表示ルール:**
- 各グループ内は deadline 昇順、WRK → PRV の順
- GROUP/CATEGORY は命名規則から抽出。規則なしの場合は grp=WRK, cat=misc
- notes があれば行末に短縮表示（30文字まで）
- 🔗 マークは不要（全件 Google 同期済みのため）

### STEP 3: アクション確認

表示後、以下を確認する：

1. 「完了にするタスクはありますか？（番号 or タスク名）」
   → あれば `task_sync.complete_task()` で Google + ローカル両方を完了
2. 「追加するタスクはありますか？」
   → あれば `task_sync.add_task()` で Google + ローカル両方に追加
   → 命名規則は自動適用される
3. 「削除するタスクはありますか？」
   → あれば確認の上 `google_api.tasks_delete()` + ローカル削除
