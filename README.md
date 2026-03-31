# 株式会社 AskaIwanaga

Claude Code による個人業務・生活管理の統合指揮系統。
すかいらーく店舗運営・個人資産管理・習慣管理・情報収集を一元自動化する。

---

## 事業・業務概要

### 本業：すかいらーく店舗運営（GTみなとみらい / GT保土ヶ谷駅前）
- 営業管理表の自動取得・分析（STX連携）
- ポータル通達の自動取得・要約
- シフト管理（らくしふ → Google Calendar 連携）
- 店舗周辺イベント情報・客数影響分析

### 個人ライフマネジメント
- 日次ブリーフィング（天気 / 予定 / タスク / 株価 / メール）
- 習慣管理・ランニング記録
- 資産・財務状況管理（ゆうちょ / ローン / クレジット）
- 予算・支出管理

### 副業・プロジェクト（進行中）
- **YouTube チャンネル**：ゆっくり解説形式・社会系企業解説ジャンル（Claude Codeで台本生成・自動編集）
- **RESAS/来訪者データ分析**：店舗客数と周辺人流の相関分析

---

## 起動方法

```
/consigliere
```

日本語で話しかけるだけで、担当者が自動的に対応します。

---

## スキル一覧

### /morning（朝のブリーフィング）
毎朝 5:30 に launchd で自動実行。1日の始まりに全情報を集約して表示。

**収集情報：** 天気 / カレンダー / タスク（ローカル＋Google Tasks）/ 習慣 / 財務 / 株価 / ガソリン価格 / ポータル通達 / 営業状況（2店舗）/ 未読メール（private＋work＋store）/ 店舗周辺イベント

**出力：**
- ターミナルにブリーフィング表示
- `drafts/morning_report_MM-DD_HH-mm.md` に保存
- VOICEVOX で音声化 → MP3変換 → iCloud同期 + 即時再生
- MP3添付メール送信（`asuka.ctn1@gmail.com` / `asuka.iwanaga@skylark.co.jp`）

### /evening（夜のブリーフィング）
1日の振り返り・翌日の準備。

### /consigliere（全指示の入口）
何でもここから。自然な日本語で話しかけると担当者へルーティング。

---

## 部門別スキル

### sales — Sonny 担当
| コマンド | 内容 |
|---|---|
| `/sales:gmail` | Gmail の確認・送受信 |
| `/sales:calendar` | Google Calendar の確認・予定追加 |
| `/sales:task` | タスクの確認・追加・完了 |
| `/sales:daily-report` | 日報の自動生成 |
| `/sales:youtube` | YouTube 台本生成 → 動画制作パイプライン実行 |

### finance — Tom 担当
| コマンド | 内容 |
|---|---|
| `/finance:budget` | 月次予算・支出の管理 |
| `/finance:financial` | 残高・資産スナップショット |
| `/finance:stocks` | 株価ウォッチリスト（Yahoo Finance API） |

### general — Clemenza 担当
| コマンド | 内容 |
|---|---|
| `/general:log` | 日誌の作成・保存 |
| `/general:memo` | メモの作成・閲覧 |
| `/general:news` | 最新ニュースの確認 |
| `/general:weather` | 天気予報（横浜） |
| `/general:quote` | 今日の名言（日付ベースで決定論的に選出） |
| `/general:portal` | すかいらーくポータル通達取得・表示 |

### hr — Connie 担当
| コマンド | 内容 |
|---|---|
| `/hr:habit` | 習慣のチェック・確認 |
| `/hr:running` | ランニング記録の追加・確認 |

### studio — sales 部門傘下・動画制作部署
| コマンド | 担当 | チーム | 内容 |
|---|---|---|---|
| `/studio:produce` | Jack Woltz | producer | 台本生成〜全工程統括（入口） |
| `/studio:direct` | Virgil Sollozzo | director | PHASE 2〜3 一括実行（編集統括） |
| `/studio:voice` | Johnny Fontane | sound | VOICEVOX音声合成・BGM・SRT字幕 |
| `/studio:animate` | Luca Brasi | animation | スライド・立ち絵・サムネイル生成 |
| `/studio:master` | Al Neri | mastering | DaVinci タイムライン構築・エクスポート |
| `/studio:analyze` | Moe Greene | analyzer | YouTube 再生数・CTR 分析・改善提案 |

設計思想・詳細: `sales/studio/README.md`

### planning — Michael 担当
システム開発・改修・データ分析。変更記録は `planning/changelog/` に蓄積。

---

## データ保存先

### データ（`data/`）

| ファイル | 内容 |
|---|---|
| `logs.json` | 日誌 |
| `memos.json` | メモ |
| `habits.json` | 習慣定義 |
| `habit_log.json` | 習慣チェックログ |
| `financial.json` | 資産スナップショット |
| `budget.json` | 予算・支出 |
| `running_log.json` | ランニング記録 |
| `tasks.json` | タスク |
| `stx_kanrihyo.db` | 営業管理表 SQLite DB |
| `portal_notices.json` | ポータル通達DB（本文・PDF・スケジュール永続保存） |

### プロジェクト内

| パス | 内容 |
|---|---|
| `drafts/` | 朝のレポート・ポータルキャッシュ・音声ファイル（一時） |
| `planning/changelog/` | システム変更記録（セッション単位） |
| `.claude/letterbox/` | Donからのテンプレート・指示書の受け取りボックス |

---

## スクリプト一覧（`scripts/`）

| スクリプト | 内容 |
|---|---|
| `scripts/scrapers/portal.py` | ポータル通達スクレイパー（Playwright + PDF解析） |
| `scripts/auth/portal_login.py` | ポータルセッション再ログイン |
| `scripts/scrapers/stx_kanrihyo.py` | 営業管理表取得・SQLite保存・サマリー出力 |
| `scripts/auth/stx_login.py` | STXセッション再ログイン |
| `scripts/tools/tts_morning.py` | VOICEVOX音声合成 → MP3変換 → iCloud同期 |
| `scripts/tools/email_morning.py` | 朝のブリーフィングMP3添付メール送信用MIME生成 |
| `scripts/scrapers/area_events.py` | 店舗周辺イベント取得（Kアリーナ・ぴあMM・Zepp＋DuckDuckGo） |
| `scripts/scrapers/mf_balance.py` | マネーフォワードから残高取得 |
| `scripts/tools/resas_flow.py` | 来訪者データ取得・客数相関分析 |
| `scripts/tools/record_event_outcome.py` | イベント後の実績記録 |
| `scripts/scrapers/rakushifu_sync.py` | らくしふ → Google Calendar シフト同期 |

---

## 自動化

### launchd（macOS）
- **設定ファイル**: `~/Library/LaunchAgents/com.askaiwanaga.morning.plist`
- **実行スクリプト**: `~/.claude/morning_auto.sh`
- **スケジュール**: 毎日 5:30（`--dangerously-skip-permissions` で無人実行）
- **ログ**: `~/.claude/morning_auto.log`

再設定が必要な場合：
```bash
launchctl load ~/Library/LaunchAgents/com.askaiwanaga.morning.plist
```

---

## スキルファイル構成（`.claude/commands/`）

```
commands/
├── morning.md          # 朝のブリーフィング（STEP 1〜8）
├── evening.md          # 夜のブリーフィング
├── consigliere.md      # 全指示の受付・ルーティング
├── finance/
│   ├── budget.md
│   ├── financial.md
│   └── stocks.md
├── general/
│   ├── log.md
│   ├── memo.md
│   ├── news.md
│   ├── portal.md       # すかいらーくポータル通達
│   ├── quote.md
│   └── weather.md
├── hr/
│   ├── habit.md
│   └── running.md
└── sales/
    ├── calendar.md
    ├── daily-report.md
    ├── gmail.md
    └── task.md
```

---

## 変更履歴

変更記録は `planning/changelog/YYYY-MM-DD_セッション名.md` に蓄積。
Consigliere がセッション中の主要な変更を自動記録する。
