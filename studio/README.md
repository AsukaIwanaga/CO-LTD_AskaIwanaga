# Studio 部署 — 映像制作部門
### sales 部門傘下 / Sonny 管轄

---

## 設計思想

> "Leave the gun. Take the cannoli."
> 必要なものだけを持ち、余計な作業は捨てる。

**Don が題材を伝えるだけで、完成動画が手元に届く。**

台本生成・音声収録・映像制作・タイムライン構築はすべてスクリプトと Claude Code が担う。
Don の作業は「台本の確認」と「最終チェック」の2点のみ。
各チームが役割分担して連携する。

---

## 組織図

```
sales 部門（Sonny）
└── studio 部署
    │
    ├── 企画チーム  [producer]  — Jack Woltz
    │     台本生成・企画立案・全工程の進行管理
    │
    └── 編集チーム  [director]  — Virgil Sollozzo
          │
          ├── 音声チーム      [sound]      — Johnny Fontane
          │     VOICEVOX 音声合成・BGM・SE・SRT 字幕生成
          │
          ├── アニメ映像チーム [animation]  — Luca Brasi
          │     立ち絵・背景スライド・サムネイル画像生成
          │
          ├── 全体編集チーム  [mastering]  — Al Neri
          │     DaVinci Resolve タイムライン構築・最終仕上げ・エクスポート
          │
          └── 分析チーム      [analyzer]   — Moe Greene
                YouTube 再生数・CTR・視聴維持率の分析・改善提案
```

---

## 担当者プロフィール

| 担当者 | チーム | 役割 | スキル |
|---|---|---|---|
| **Jack Woltz** | producer | プロデューサー。台本生成・企画・工程管理 | `/studio:produce` |
| **Virgil Sollozzo** | director | 編集統括。各チームへの指示・品質管理 | `/studio:direct` |
| **Johnny Fontane** | sound | 音声合成・BGM・SE・SRT 字幕 | `/studio:voice` |
| **Luca Brasi** | animation | 立ち絵・スライド・サムネイル生成 | `/studio:animate` |
| **Al Neri** | mastering | DaVinci タイムライン・最終編集・エクスポート | `/studio:master` |
| **Moe Greene** | analyzer | 再生数・CTR・視聴分析・改善提案 | `/studio:analyze` |

### キャラクター原典（ゴッドファーザーより）

| 担当者 | 原典 |
|---|---|
| Jack Woltz | ハリウッドの大物映画プロデューサー。制作全体を支配する |
| Virgil Sollozzo | "The Turk"。緻密な戦略と実行力を持つ編集統括 |
| Johnny Fontane | コルレオーネ家と縁の深い歌手・俳優。声と音楽のプロ |
| Luca Brasi | ドンの最も信頼する実行役。細部まで忠実・職人気質 |
| Al Neri | コルレオーネ家の執行部隊長。冷静・完璧主義・最後の仕上げを担う |
| Moe Greene | ラスベガスのホテル王。数字とビジネスに精通した分析家 |

---

## 制作フロー

```
[ Don ] 題材・尺・重点ポイントを伝える
    ↓  /studio:produce
═══════════════════════════════════════════════════════
  PHASE 1  企画  [producer / Jack Woltz]
═══════════════════════════════════════════════════════
    ・台本 TOML 生成（霊夢・魔理沙の掛け合い形式）
    ・タイトル・サムネイル文言の決定
    ・▶ Don の確認・承認

    ↓（承認後）

═══════════════════════════════════════════════════════
  PHASE 2  素材制作  [director / Virgil Sollozzo 統括]
═══════════════════════════════════════════════════════

  [sound / Johnny Fontane]           [animation / Luca Brasi]
  ・VOICEVOX で全セリフ WAV 生成     ・スライド画像生成（Pillow）
  ・BGM・SE をシーンに割り当て       ・立ち絵の発話切り替えマップ作成
  ・SRT 字幕ファイル生成             ・サムネイル PNG 生成
            └──────── 並行実行 ────────┘

    ↓（素材完成後）

═══════════════════════════════════════════════════════
  PHASE 3  編集・仕上げ  [mastering / Al Neri]
═══════════════════════════════════════════════════════
    ・DaVinci Resolve Python API でタイムライン構築
    ・音声・映像・字幕・BGM の自動配置
    ・▶ Don の最終確認（微調整があれば指示）
    ・MP4 エクスポート

    ↓（公開後）

═══════════════════════════════════════════════════════
  PHASE 4  分析  [analyzer / Moe Greene]
═══════════════════════════════════════════════════════
    ・再生数・CTR・視聴維持率を YouTube Data API で取得
    ・改善点を Don に報告
    ・次回企画へのフィードバックを Jack に渡す
```

---

## スキル一覧

| コマンド | 担当 | 内容 |
|---|---|---|
| `/studio:produce` | Jack | 全工程統括の入口。題材を受け取り台本生成〜完成まで仕切る |
| `/studio:direct` | Virgil | PHASE 2〜3 を一括実行（素材制作→編集→エクスポート） |
| `/studio:voice` | Johnny | 音声合成・BGM・SE・SRT 字幕の単体実行 |
| `/studio:animate` | Luca | スライド・立ち絵・サムネイルの単体実行 |
| `/studio:master` | Al Neri | DaVinci タイムライン構築・エクスポートの単体実行 |
| `/studio:analyze` | Moe Greene | YouTube 分析レポートの生成 |

---

## 自動化スコープ

| 工程 | 自動化率 | 担当 |
|---|---|---|
| 台本生成 | 100% | Jack |
| 音声合成（全セリフ） | 100% | Johnny |
| BGM・SE 割り当て | 80% | Johnny |
| SRT 字幕生成 | 100% | Johnny |
| スライド画像生成 | 90% | Luca |
| サムネイル生成 | 90% | Luca |
| タイムライン構築 | 90% | Al Neri |
| エクスポート | 100% | Al Neri |
| 再生数データ取得 | 100% | Moe Greene |
| **台本確認** | **0%（Don）** | — |
| **最終チェック** | **0%（Don）** | — |

**Don の実作業: 台本確認 + 最終確認の 2 ステップのみ**

---

## 技術スタック

| ツール | 用途 | チーム |
|---|---|---|
| VOICEVOX（macOS版） | 音声合成エンジン | sound |
| DaVinci Resolve + Python API | タイムライン構築・エクスポート | mastering |
| Pillow | スライド・サムネイル画像生成 | animation |
| MoviePy | 音声結合・プレビュー生成 | mastering |
| pydub | WAV 長さ計測・変換 | sound |
| YouTube Data API v3 | 再生数・CTR 取得 | analyzer |

---

## ディレクトリ構造

```
studio/
├── README.md
├── producer/                  ← 企画チーム作業領域
├── director/                  ← 編集チーム作業領域
│   ├── sound/
│   ├── animation/
│   ├── mastering/
│   └── analyzer/
├── templates/                 ← 台本 TOML ファイル
│   ├── script_template.toml
│   └── script_2026-03-26_gasoline-mitooshi.toml
├── assets/
│   ├── backgrounds/           ← 背景画像（PNG）
│   ├── characters/            ← 立ち絵素材（霊夢・魔理沙等 PNG）
│   ├── bgm/                   ← BGM（MP3/WAV）
│   └── se/                    ← SE 効果音
├── scripts/                   ← 自動化スクリプト群
│   ├── synthesize_voice.py    ← Johnny 担当
│   ├── build_slides.py        ← Luca 担当
│   ├── build_timeline.py      ← Al Neri 担当
│   ├── export_video.py        ← Al Neri 担当
│   ├── generate_thumbnail.py  ← Luca 担当
│   ├── analyze_youtube.py     ← Moe Greene 担当
│   └── requirements.txt
└── output/                    ← 生成物（.gitignore 対象）
    ├── audio/
    ├── slides/
    ├── subtitles/
    ├── thumbnails/
    └── *.mp4
```

---

## 前回の続きから再開する

> 「studio部門のセットアップの続きをやりたい。SESSION.mdを確認して。」
> と伝えるだけで即再開できる。

詳細な進捗・手順・ファイルパス早見表は **`studio/SESSION.md`** を参照。

---

## セットアップ

```bash
# Python ライブラリ
pip install pillow requests yt-dlp

# VOICEVOX エンジン起動確認
curl -s http://localhost:50021/version

# DaVinci Resolve Python API 確認（DaVinci でプロジェクトを開いた後）
source ~/.zprofile
python3 -c "
import DaVinciResolveScript as dvr
resolve = dvr.scriptapp('Resolve')
print('接続OK:', resolve.GetVersionString()) if resolve else print('接続失敗')
"
```

### 環境変数（~/.zprofile に設定済み）

```bash
export RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
export RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
export PYTHONPATH="$PYTHONPATH:$RESOLVE_SCRIPT_API/Modules/"
```

---

## 制作実績

| 日付 | タイトル | 尺 | 状態 |
|---|---|---|---|
| 2026-03-26 | ガソリン代はこれからどうなる？ | 10分 | 台本完成 |

---

## 運用ルール

1. **台本は Don が確認してから音声合成へ進む**（誤情報防止）
2. **完成動画は `output/` に保存、YouTube アップは Don が手動実行**
3. **企業批判・個人誹謗中傷は台本生成時にブロック**
4. **素材は著作権フリー・商用利用可のもののみ使用**
5. **分析結果は次回の台本生成に必ずフィードバックする**
