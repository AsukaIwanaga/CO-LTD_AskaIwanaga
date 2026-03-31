# PROJECT: LINE レシート風ブリーフィング配信

**起票**: 2026-03-31
**ステータス**: 進行中
**担当**: planning (Michael) + agent

---

## 概要

朝のブリーフィングをキッチンプリンター風の画像で生成し、
LINE に自動送信する。テキストメールのフォーマット問題を根本解決。

## 手順

### STEP 1: LINE Developers アカウント作成

1. https://developers.line.biz/ にアクセス
2. LINE アカウントでログイン
3. 「新規プロバイダー」作成（名前: AskaIwanaga）
4. 「Messaging API チャネル」作成
   - チャネル名: ROBCO TERMINAL
   - 説明: Don専用秘書
5. チャネル設定画面で以下を取得:
   - **Channel access token**（長期）
   - **Channel secret**

### STEP 2: LINE 公式アカウントを友だち追加

1. STEP 1 で作成したチャネルの QR コードを表示
2. Don の iPhone で QR コードを読み取り → 友だち追加
3. トーク画面に「友だち追加ありがとう」的なメッセージが来ればOK

### STEP 3: Don の User ID を取得

Webhook で Don の LINE User ID を取得する必要がある。
簡易的には:

1. チャネル設定 → 「あいさつメッセージ」をOFF
2. 「応答メッセージ」をOFF
3. 「Webhook」をON → URL は後で設定（STEP 5）
4. Don がトーク画面で何かメッセージを送る
5. Webhook で受信した userId を .env に保存

または、LINE Developers Console の「Your user ID」欄から取得可能。

### STEP 4: .env に LINE 設定追加

```
LINE_CHANNEL_ACCESS_TOKEN=xxxxx
LINE_CHANNEL_SECRET=xxxxx
LINE_USER_ID=Uxxxxx  (Don の User ID)
```

### STEP 5: 画像送信スクリプト実装

scripts/lib/line_api.py を作成:
- LINE Messaging API で画像を Push 送信
- 画像は Imgur 等にアップロードするか、
  自前サーバーで配信するか、
  または LINE の contentProvider で直接送信

最もシンプルな方法:
- 画像を一時的に公開 URL で配信（ngrok or Imgur API）
- LINE Push Message API で画像 URL を送信

### STEP 6: morning_auto.py に統合

```
情報収集 → Claude Haiku 整形
→ Pillow でレシート画像生成
→ LINE API で Don に Push 送信
→ メールにも添付送信（バックアップ）
```

### STEP 7: cron 登録

morning_auto_cron.sh に LINE 送信を追加。

---

## 必要なもの

| 項目 | 状態 | Don の操作 |
|------|------|-----------|
| LINE Developers アカウント | 未作成 | Don が作成 |
| Messaging API チャネル | 未作成 | Don が作成 |
| Channel access token | 未取得 | Console から取得 |
| Don の User ID | 未取得 | Console から取得 |
| .env 設定 | 未設定 | トークン等を伝える |
| scripts/lib/line_api.py | 未実装 | 自動 |
| 画像ホスティング | 未決定 | Imgur API or ngrok |

---

## 画像ホスティング方式の比較

| 方式 | コスト | 安定性 | 実装 |
|------|--------|--------|------|
| Imgur API | 無料 | ○ | 簡単 |
| ngrok + ローカル | 無料 | △ Mac起動必要 | 中 |
| Cloudflare R2 | ほぼ無料 | ◎ | 中 |
| LINE Blob | 無料 | ◎ | 簡単 |

推奨: LINE Messaging API の Blob アップロードが最もシンプル。
