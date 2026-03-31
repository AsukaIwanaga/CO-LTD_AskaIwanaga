# 朝のブリーフィング

Don の1日を始めるための総合ブリーフィングを行います。
複数部門の情報を集約して表示し、必要なアップデートを順番に確認します。

## フロー

### STEP 1: 情報収集（並行して取得）

以下を同時に取得する：

- **天気**（Open-Meteo API — `precipitation_probability_max` を追加）
  ```
  https://api.open-meteo.com/v1/forecast?latitude=35.4437&longitude=139.6380&current=temperature_2m,weathercode,windspeed_10m&daily=temperature_2m_max,temperature_2m_min,weathercode,precipitation_probability_max&timezone=Asia%2FTokyo&forecast_days=1
  ```
- **すかいらーくポータル通達**（`/general:portal` を呼び出す — STEP 3 のアクション確認はスキップ）
- **今日の予定**（MCP `gcal_list_events` で本日分を取得 — `primary` と `asuka.iwanaga@skylark.co.jp` の両カレンダーを取得し、時刻順にマージする）
- **未完了タスク（ローカル）**（`/Users/askaiwanaga/CO-LTD_AskaIwanaga/data/tasks.json` を読み込み、未完了のものを抽出）
- **Google Tasks**（MCP `gtasks` で全タスクリストを取得し、未完了タスクを抽出）
- **習慣状況**（`habits.json` + `habit_log.json` を読み込み、今日のチェック状況を確認）
- **財務状態**（`/finance:financial` を呼び出す — 残高・ローン・クレジット残高を取得）
- **株価**（Yahoo Finance v8 API で以下のティッカーを取得 — DoD/WoW/YoY の3期間比較）
  - `^N225`（NIKKEI）、`^DJI`（DOW）、`^IXIC`（NASDAQ）、`^GSPC`（SP500）、`3197.T`（すかいらーく）
  - 為替: `USDJPY=X`（¥/$）、`TWDJPY=X`（¥/TWD）
  - WoW は `range=5d`、YoY は `range=1y` で取得し最初と最後を比較する
- **営業状況（GTみなとみらい）**（`python3 scripts/scrapers/stx_kanrihyo.py --summary` を実行）
- **営業状況（GT保土ヶ谷駅前）**（`stx_kanrihyo.py` が単一店舗対応のため現時点では取得不可 — 「取得不可」と表示）
- **未読メール（private）**（`mcp__gmail__list_messages` で `q: "is:unread in:inbox"` を指定し、最新5件を取得。件名・送信者・本文を取得して要約）
- **未読メール（work）**（`mcp__claude_ai_Gmail__gmail_search_messages` で `asuka.iwanaga@skylark.co.jp` の未読受信トレイを取得、最新5件）
- **未読メール（store）**: 現在見送り（018974@skylark.co.jp — MCP 未接続）
- **店舗周辺イベント**（`python3 scripts/scrapers/area_events.py --format json` を実行）
  - Kアリーナ横浜・ぴあアリーナMM・Zepp横浜 の当日・直近イベントを取得
  - 特殊イベント（ピカチュウ大行進・花火など）、気象警報、鉄道遅延情報も含む
  - 徒歩圏のイベント来場者数はGTみなとみらいの客数変動に直結する
- **らくしふシフト同期**（`python3 scripts/scrapers/rakushifu_sync.py --confirm-shifts --headless` を実行）
  - 未確認シフトを自動で確認済みにする（`--confirm-shifts`）
  - `drafts/rakushifu_shifts_YYYY-MM.json` に最新シフトを取得
  - `drafts/rakushifu_diff_YYYY-MM-DD.json` が生成された場合（差分あり）、MCP `gcal_create_event` で Google Calendar（`primary`）に反映する
    - イベント形式: `summary: "🏪 シフト勤務"`, `description: "らくしふ自動同期"`, `colorId: "6"` (Tangerine)
    - 重複チェック: 同日に `gcal_list_events(q="シフト勤務")` で既存イベントを確認してから追加
    - 削除分: 該当日の既存シフトイベントを `gcal_delete_event` で削除してから再登録
  - スクリプトが失敗した場合はスキップして次のステップへ

### STEP 2: ブリーフィング表示（ターミナル / PC幅）

以下のフォーマットで一気に表示する（モノスペース・テキストベース）。
**このフォーマットはターミナル表示専用。メール送信時は STEP 7-0 で iPhone テンプレートに変換する。**

**⚠ 厳守事項**
- **Markdownヘッダー（`#` `##` `###`）は絶対に使わない。** セクション名はプレーンテキストのみ。
- テンプレートの**表記（大文字・小文字・記号・インデント・スペース）を正確に再現**すること。
- メールは**必ず `title/content` 上・`from` 下のテーブル形式**で表示する（箇条書き不可）。
- 財務状況に**「純資産」行は含めない**。テンプレートにない行を追加しない。
- 未記録チェックは `□` スタイルで表示する（`- [ ]` 不可）。

```
MORNING BREAFING  MM dd (ddd)

天気
location        weather         temp            rain
--------------------------------------------------------------------------------
yokohama        str...          ##℃ / ##℃       ##%



予定
time            event
--------------------------------------------------------------------------------
HH:mm           str...
                str...
HH:mm           str...



タスク
status      date        grp  indx  title
--------------------------------------------------------------------------------
> overdue   MM-dd (ddd) wrk  ????  str...
                  (ddd)      ????  str...
                  (ddd) prv  ????  str...
            MM-dd (ddd) prv  ????  str...

> today     MM-dd (ddd) wrk  ????  str...
                  (ddd)      ????  str...
                  (ddd) prv  ????  str...
                  (ddd)      ????  str...
                  (ddd)      ????  str...

> non-lmt   MM-dd (ddd) wrk  ????  str...
                  (ddd)      ????  str...
                  (ddd) prv  ????  str...
                  (ddd)      ????  str...
                  (ddd)      ????  str...

> future    MM-dd (ddd) wrk  ????  str...
                  (ddd)      ????  str...
                  (ddd) prv  ????  str...
            MM-dd (ddd) wrk  ????  str...
                  (ddd)      ????  str...


group       date        indx       title
--------------------------------------------------------------------------------
> work      MM-dd (ddd) ????      str...
                  (ddd) ????      str...
            MM-dd (ddd) ????      str...

> private   MM-dd (ddd) ????      str...
                  (ddd) ????      str...

// タスクはローカル tasks.json + Google Tasks をマージして表示。
// さらにポータル通達・メールから読み取れる期限付きアクションも追加する。
// overdue = 今日より前の期限、today = 今日期限、non-lmt = 期限なし、future = 明日以降
// GoogleタスクのタイトルルールはGROUP_index_title形式。grp=wrk/prv、indxは右詰。
// 表示順: work > private、overdue > today > non-lmt > future


営業状況報告
@GTみなとみらい
time       index       target        actual    diff%    comp%
--------------------------------------------------------------------------------
today      amt         ###,###
           t/c             ###
           a/c           #,###
           lbr%          ##.##

MM-DD      amt         ###,###      ###,###   ±##.#%   ±##.#%
           t/c         ###,###          ###   ±##.#%   ±##.#%
           a/c         ###,###        #,###   ±##.#%   ±##.#%
           lbr%          ##.##        ##.##   ±##.#%

2M avg     amt         ###,###            -   ±##.#%   ±##.#%
           t/c         ###,###            -   ±##.#%   ±##.#%
           a/c         ###,###        #,###   ±##.#%   ±##.#%
           lbr%          ##.##        ##.##   ±##.#%

this-M     amt     ###,###,###  ##,###,###   ±##.#%   ±##.#%
           t/c         ###,###       ##,###   ±##.#%   ±##.#%
           a/c         ###,###        #,###   ±##.#%   ±##.#%
           lbr%          ##.##        ##.##   ±##.#%


@GT保土ヶ谷駅前
time       index       target        actual    diff%    comp%
--------------------------------------------------------------------------------
today      amt         ###,###
           t/c             ###
           a/c           #,###
           lbr%          ##.##

MM-DD      amt         ###,###      ###,###   ±##.#%   ±##.#%
           t/c         ###,###          ###   ±##.#%   ±##.#%
           a/c         ###,###        #,###   ±##.#%   ±##.#%
           lbr%          ##.##        ##.##   ±##.#%

2M avg     amt         ###,###            -   ±##.#%   ±##.#%
           t/c         ###,###            -   ±##.#%   ±##.#%
           a/c         ###,###        #,###   ±##.#%   ±##.#%
           lbr%          ##.##        ##.##   ±##.#%

this-M     amt     ###,###,###  ##,###,###   ±##.#%   ±##.#%
           t/c         ###,###       ##,###   ±##.#%   ±##.#%
           a/c         ###,###        #,###   ±##.#%   ±##.#%
           lbr%          ##.##        ##.##   ±##.#%


通達
--------------------------------------------------------------------------------

> now campaign
period         title
--------------------------------------------------------------------------------
MM-dd - MM-dd  str...
MM-dd - MM-dd  str...
MM-dd - MM-dd  str...

> thisweek campaign
[ ] str...                                                               ~ MM/dd
[ ] str...                                                               ~ MM/dd
[ ] str...                                                               ~ MM/dd

  未読通達
  ------------------------------------------------------------------------------
  - title                                                               -- MM/dd
    - period    : MM/dd ~ MM/dd
    - deadline  :       ~ MM/dd  task_title...
    -                  ~ MM/dd  task_title...
    - descr     : str...
                  ...
                  ...
                  ...
                  ...

  ※ 通達の詳細データは `portal_notices.json` に蓄積されており、過去の通達もいつでも参照可能。
     詳細確認が必要な通達は STEP 4 後に「詳細を確認しますか？」と聞く。


メール
PRIVATE
asuka.ctn1@gmail.com
title               content
from
--------------------------------------------------------------------------------
str...              str...
str...              ...
                    ...
                    ...
                    ...
                    ...

str...              str...
str...              ...
                    ...
                    ...
                    ...
                    ...


WORK_ACCOUNT
asuka.iwanaga@skylark.co.jp
title               content
from
--------------------------------------------------------------------------------
str...              str...
str...              ...
                    ...
                    ...
                    ...
                    ...


STORE_ACCOUNT
018974@skylark.co.jp
title               content
from
--------------------------------------------------------------------------------
str...              str...
str...              ...
                    ...
                    ...
                    ...
                    ...


習慣
index                   MM/dd  MM/dd  MM/dd  MM/dd  MM/dd  MM/dd  MM/dd   rate
--------------------------------------------------------------------------------
ランニング              [ ]    [ ]    [ ]    [ ]    [ ]    [ ]    [ ]      ##%
ログ入力                [ ]    [ ]    [ ]    [ ]    [ ]    [ ]    [ ]      ##%
ENG (IELTS)             [ ]    [ ]    [ ]    [ ]    [ ]    [ ]    [ ]      ##%
一箇所4S                [ ]    [ ]    [ ]    [ ]    [ ]    [ ]    [ ]      ##%
financial log入力       [ ]    [ ]    [ ]    [ ]    [ ]    [ ]    [ ]      ##%
ゲーム・動画は2h以内    [ ]    [ ]    [ ]    [ ]    [ ]    [ ]    [ ]      ##%

// 列は今日を含む直近7日分（左が古い、右が今日）
// index列は半角24幅（=全角12）に統一。各習慣名の表示幅を計算し半角スペースで補填する
//   ランニング(10)+14sp / ログ入力(8)+16sp / ENG (IELTS)(11)+13sp
//   一箇所4S(8)+16sp / financial log入力(17)+7sp / ゲーム・動画は2h以内(18)+6sp
// habit_log.json を参照し、チェック済みの日は [x]、未チェックは [ ] で表示
// rate = 直近7日間の達成率（チェック数/7）
// 習慣名が変わった場合は表示幅を再計算してパディングを更新すること


財務状況
label     amt
--------------------------------------------------------------------------------
CASH      ¥###,###,###   // ゆうちょ銀行の残高
LOAN      ¥###,###,###   // 借りている金額の合計値
CREDIT    ¥###,###,###   // クレジットカードの残り使用可能金額

  支払い・引落とし予定
  date               amt   from      to
  ------------------------------------------------------------------------------
  MM-dd (ddd)   ¥###,###   str...    str...
                ¥###,###   str...    str...
  MM-dd (ddd)   ¥###,###   str...    str...


株価・取引
field     index         now          DoD        WoW        YoY
--------------------------------------------------------------------------------
stock     nikkei        ¥###,### ↕   ±¥###,###  ±¥###,###  ±¥###,###
          dow           $###,### ↕   ±$###,###  ±$###,###  ±$###,###
          nasdaq        $###,### ↕   ±$###,###  ±$###,###  ±$###,###
          sp500         $###,### ↕   ±$###,###  ±$###,###  ±$###,###
          skylark       ¥###,### ↕   ±¥###,###  ±¥###,###  ±¥###,###

fx-rate   ¥ vs $        ###.## ↕     ±###.##    ±###.##    ±###.##
          ¥ vs TWD      ###.## ↕     ±###.##    ±###.##    ±###.##

petol     yokohama_avg  ¥###.## ↕    ±¥###.##   ±¥###.##   ±¥###.##


店舗周辺イベント
date  venue           event_title                 guest_amt       effort(b/a)
                      artist/grup                 time            time   +number
--------------------------------------------------------------------------------
TODAY
MM-dd K-ARENA         str...                      ###,###         HH:mm +###,###
                      str...                      HH:mm - HH:mm   HH:mm +###,###

      PIA-ARENA        str...                      ###,###         HH:mm +###,###
                      str...                      HH:mm - HH:mm   HH:mm +###,###

      ZEPP_yokohama   str...                      ###,###         HH:mm +###,###
                      str...                      HH:mm - HH:mm   HH:mm +###,###

      other           str...                      ###,###         HH:mm +###,###
                      str...                      HH:mm - HH:mm   HH:mm +###,###


FUTURE
MM-dd K-ARENA         str...                      ###,###         HH:mm +###,###
                      str...                      HH:mm - HH:mm   HH:mm +###,###

      PIA-ARENA        str...                      ###,###         HH:mm +###,###
                      str...                      HH:mm - HH:mm   HH:mm +###,###

      ZEPP_yokohama   str...                      ###,###         HH:mm +###,###
                      str...                      HH:mm - HH:mm   HH:mm +###,###

      other           str...                      ###,###         HH:mm +###,###
                      str...                      HH:mm - HH:mm   HH:mm +###,###
```

// 店舗周辺イベント表示ルール:
// - `python3 scripts/scrapers/area_events.py --format json` の結果を使用
// - TODAY: 当日開催のイベント（K-ARENA / PIA-ARENA / ZEPP_yokohama / other）
// - FUTURE: 翌日以降のイベント（直近3日分程度）
// - guest_amt: 来場者数（チケット販売数・動員実績）
// - effort(b/a): before=開場前の影響時刻+客数増、after=開催後の影響時刻+客数増
// - イベントなし会場は行を省略してよい
// - special_events（DuckDuckGo）は other 行に含める

**表示ルール**
- weathercode から天気の日本語説明への変換: 0=快晴, 1=晴れ, 2=晴れ時々曇り, 3=曇り, 45/48=霧, 51-67=雨, 71-77=雪, 80-82=にわか雨, 95=雷雨
- タスクの日付フォーマット: `MM-dd (ddd)` （例: `03-24 (Tue)`）。同一日付が連続する場合は2行目以降の日付は省略
- 株価 DoD/WoW/YoY: Yahoo Finance API で DoD は `range=1d`、WoW は `range=5d`（5営業日前との比較）、YoY は `range=1y`（1年前との比較）で取得
- ↕ は上昇なら ↑、下降なら ↓ に置換
- 支払い・引落とし予定: `budget.json` の `expenses` から今後7日以内の予定や、財務メモから読み取れる引落とし情報を表示（データなければセクションごと省略）

### STEP 3: 未記録チェック

STEP 1 の情報をもとに、以下の「昨日・直近の漏れ」を確認する：

- **ログ漏れ**: `logs.json` の最新エントリの日付を確認。昨日（YYYY-MM-DD）のログがなければ通知する
- **習慣ログ漏れ**: `habit_log.json` を確認。昨日チェックされていない習慣があれば通知する
- **financial ログ漏れ**: `financial.json` の最新エントリが2日以上前であれば通知する
- **営業データ漏れ**: `python3 scripts/scrapers/stx_kanrihyo.py --summary` の結果で「本日分データなし」が表示された場合は通知する（DB未取得の可能性）

漏れがあれば以下のように表示する：

```
⚠️ 未記録の項目があります
  □ 昨日のログ（MM/DD分）が未入力です
  □ 昨日の習慣チェックが未完了です（ランニング、ログ入力）
  □ 残高記録が X日間 更新されていません
```

### STEP 4: アップデート確認

未記録チェックの後、以下を順番に確認する：

1. **昨日分の漏れ対応**（漏れがある場合のみ）
   「昨日分を今から記録しますか？」
   → 「はい」であれば該当スキルへルーティングする

2. **習慣チェック**
   「今朝チェックできた習慣はありますか？番号または名前で教えてください。（スキップは「なし」）」
   → 回答があれば `habit_log.json` に追記する

3. **タスクの更新**
   「完了したタスクや、新しく追加するタスクはありますか？（なければスキップ）」
   → 完了があれば `tasks.json` を更新、追加があれば追記する

4. **その他の記録**
   「他に記録・確認したいことは？（なければスキップ）」

### STEP 5: レポート保存

全アップデートが完了したら、ブリーフィング内容をMarkdownファイルとして保存する。

- 保存先: `./drafts/morning_report_MM-dd_HH-mm.md`（例: `morning_report_03-19_07-30.md`）
- 内容: STEP 2 のブリーフィング表示内容 + STEP 3 の未記録チェック結果をそのまま記載
- ※ファイル名のコロンはハイフンに置換（OS互換のため）

### STEP 6: 音声報告

レポート保存後、ブリーフィング内容を VOICEVOX で音声化して再生・保存する。

#### STEP 6-1: 読み上げ文の生成（文章化）

STEP 2 のブリーフィング内容をもとに、**自然な日本語話し言葉**の読み上げ文を生成する。

変換ルール：
- 全体を「おはようございます、ドン。本日〇月〇日〜のブリーフィングをお伝えします。」で始める
- 天気 → 現在気温・天気・最高最低・降水確率をすべて読み上げる
- 予定 → 件名・時刻・詳細（場所・持ち物など）を読み上げる
- タスク → **全カテゴリ（overdue / today / non-lmt / future）を詳しく読み上げる**
  - overdue: 各タスク名・期限日・内容を1件ずつ丁寧に伝える。件数も冒頭で告げる
  - future: 期限が近いものは特に「〜までに〜が必要です」と強調する
- 通達 → **NOW_CAMPAIGN・THIS_WEEK_TASK・未読通達をそれぞれ詳しく読み上げる**
  - 未読通達は件名・期間・内容要約・期限付きタスクをすべて読み上げる
  - 緊急通達は「緊急です」と冒頭で強調する
- 営業 → TODAY目標・最終実績・月累計をすべて読み上げる
- メール → 送信者・件名・本文要約を読み上げる。重要なものは「重要です」と添える
- 財務 → 残高・ローン・クレジットを読み上げる。引落とし予定があれば告げる
- 習慣 → 「本日の習慣チェックをお願いします。」に続けて全習慣名を列挙する
- 株価 → 主要指数の現在値・前日比・週間変化を読み上げる
- 英数字・記号は読み上げに適した形に変換（`%` → 「パーセント」、`AMT` → 「セールス」、`T/C` → 「ティーシー」、`A/C` → 「エーシー」、`LBR%` → 「レーバー」など）
- **読み上げ文は完全な一続きの文章として生成する**（箇条書き・記号・改行コードは使わない）
- 最後に「準備は整いました。良い一日を、ドン。」で締める

#### STEP 6-2: VOICEVOX で音声合成

生成した読み上げ文を `scripts/tools/tts_morning.py` に渡して音声化する（VOICEVOX エンジンが起動している必要があります）：

```bash
python3 scripts/tools/tts_morning.py "読み上げ文テキスト"
# または stdin 経由
echo "読み上げ文テキスト" | python3 scripts/tools/tts_morning.py -
```

テキストの確認だけしたい場合（VOICEVOX 不要）：
```bash
python3 scripts/tools/tts_morning.py --text-only "テキスト"
```

このスクリプトは：
1. VOICEVOX API（声: 青山龍星 ノーマル、speaker ID: 13）で wav 生成
2. WAV → MP3 変換（ffmpeg、`drafts/morning_audio_YYYY-MM-DD.mp3`）
3. iCloud Drive にコピー（`~/Library/Mobile Documents/com~apple~CloudDocs/morning_reports/`）
4. macOS で即時再生（`afplay`）

VOICEVOX が起動していない場合は STEP 6 をスキップして STEP 7 に進む。

### STEP 7: メール送信

#### STEP 7-0: メール本文を iPhone テンプレートに変換

STEP 2 のブリーフィングで取得した各データを、
`.claude/letterbox/morning-breafing-template-iphone` のフォーマットに当てはめ直す。

**変換ルール:**
- STEP 2 と同じデータ・数値を使用する（再取得不要）
- 表示フォーマットのみ iPhone テンプレートに従う
- セクション区切りは `================================` / `-----` / `===== @店舗名 =====`
- 数値はすべて右揃え（ラベル左寄せ・値右寄せの固定幅カラム）
- 営業状況: TGT/ACT ブロック → DIFF%/COMP% ブロックの2段構成
- 株価: 1銘柄3行（NOW → DoD/WoW → YoY）
- メール: FROM/SUBJ の縦積み形式
- 習慣: 直近3日分のみ表示
- ヘッダー行（`location weather temp rain` 等のカラム名）は省略

この iPhone フォーマット済みテキストを `IPHONE_BODY` として以下のステップで使用する。

#### STEP 7-1: スクリプト実行

ブリーフィング内容をメール送信する。MP3 が生成済みであれば添付する。

```bash
# MP3 あり
python3 scripts/tools/email_morning.py "$IPHONE_BODY" drafts/morning_audio_YYYY-MM-DD.mp3
# MP3 なし（VOICEVOX スキップ時）
python3 scripts/tools/email_morning.py "$IPHONE_BODY"
```

このスクリプトは `{"private": "...", "work": "..."}` を JSON で出力する。
出力した `private` と `work` の値をそれぞれ `mcp__gmail__send_message` の `raw` パラメータに渡して送信する：

- **private**: `asuka.ctn1@gmail.com` 宛（全文）
- **work**: `asuka.iwanaga@skylark.co.jp` 宛（全文）

件名: `朝のブリーフィング YYYY/MM/DD (曜日)`

**STORE_ACCOUNT メール読み取りについて**
`018974@skylark.co.jp` の受信メールは現在 MCP 未接続（OAuth 設定が必要）。
接続方法: `.mcp.json` に `018974@skylark.co.jp` 用の Gmail MCP サーバーを追加する。
認証情報は `.env` の `STORE_EMAIL` / `STORE_PASSWORD` を参照。

### STEP 8: 締め

メール送信後、以下で締める：
> 「Don、準備は整いました。良い一日を。」
