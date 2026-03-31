# ログ作成（開発部）

ROBCO TERMINAL のログ（日誌）を作成・保存します。

## フロー

### 1. 現在のログを確認
`/Users/askaiwanaga/LIFE/robco-terminal/data/logs.json` を読み込み、最後のエントリの `id` を取得して次の ID を計算する。

### 2. 下書きファイルを作成
`./drafts/log-{YYYY-MM-DD}.md` を作成する。同日に既にファイルが存在する場合は `log-{YYYY-MM-DD}-2.md` とする。

ファイルの内容は以下のテンプレートとする：
```
# LOG — {YYYY-MM-DD}

（ここに記録を書いてください）
```

### 3. ファイルを開く
```bash
open ./drafts/log-{YYYY-MM-DD}.md
```

ファイルを開いたら、ユーザーに以下を伝える：
> ファイルを開きました。書き終わったら「保存して」と伝えてください。

### 4. 保存処理（ユーザーが「保存して」と言ったら実行）

1. `./drafts/log-{YYYY-MM-DD}.md` を読み込む
2. ヘッダー行（`# LOG — ...`）と空行を除いた本文を取得する
3. 本文が空の場合は保存せずユーザーに確認する
4. `/Users/askaiwanaga/LIFE/robco-terminal/data/logs.json` を読み込む
5. 以下の形式で新しいエントリを末尾に追加する：
   ```json
   {
     "id": "{次のID}",
     "text": "{本文（改行は\\nで表現）}",
     "timestamp": "{現在時刻 ISO 8601形式}"
   }
   ```
6. `logs.json` を上書き保存する
7. 「ログを保存しました（ID: {ID}）」と伝える
8. 下書きファイルを削除する
