# YouTube チャンネル — ゆっくり解説 × 社会系企業解説

## チャンネルコンセプト

| 項目 | 内容 |
|---|---|
| スタイル | ゆっくり実況形式（霊夢・魔理沙の掛け合い） |
| ジャンル | 社会系企業解説（飲食業界の実態・労働環境・経営戦略） |
| ターゲット | 飲食業界志望者・就活生・業界ウォッチャー |
| 投稿頻度 | 週1〜2本（目標） |
| 尺 | 10〜15分 |
| 声 | VOICEVOX（霊夢: ID=2 / 魔理沙: ID=3） |

---

## 題材例

- 「すかいらーくが赤字でも生き残る理由」
- 「ガストの客単価はなぜ上がり続けるのか」
- 「飲食バイトの実態：時給1,200円の裏側」
- 「ファミレス業界の未来：2030年に残るチェーンは？」
- 「すかいらーく vs サイゼリヤ 経営戦略の違い」

---

## 自動化パイプライン

```
[Claude Code] 台本生成（/sales:youtube）
       ↓ templates/script_YYYY-MM-DD_タイトル.toml
[VOICEVOX API] 音声合成（localhost:50021）
       ↓ output/audio/line_001.wav ... line_NNN.wav
[Pillow] スライド画像生成
       ↓ output/slides/slide_001.png ... slide_NNN.png
[MoviePy + FFmpeg] 動画結合
       ↓ output/YYYY-MM-DD_タイトル.mp4
[YouTube Data API] アップロード（将来実装）
```

実行コマンド:
```bash
# 台本から動画まで一気通貫
python3 scripts/generate_video.py templates/script_YYYY-MM-DD_タイトル.toml

# 台本のみ確認（音声・動画生成なし）
python3 scripts/generate_video.py --dry-run templates/...toml
```

---

## 台本フォーマット（TOML）

```toml
[meta]
title = "動画タイトル"
description = "動画説明文"
tags = ["すかいらーく", "ファミレス", "飲食業界"]
thumbnail_text = "サムネイル用テキスト"

[[lines]]
speaker = "reimu"    # reimu(霊夢) / marisa(魔理沙)
text = "今回はすかいらーくについて解説するよ。"
scene = "intro"      # intro / main / conclusion

[[lines]]
speaker = "marisa"
text = "すかいらーくって何でそんなに有名なんだぜ？"
scene = "main"

# ... 以下繰り返し
```

スピーカーID（VOICEVOX）:

| キャラ | speaker | VOICEVOX ID |
|---|---|---|
| 霊夢 | reimu | 2 |
| 魔理沙 | marisa | 3 |

---

## 要件定義

### 機能要件

| # | 機能 | 優先度 | 実装状況 |
|---|---|---|---|
| F-01 | 台本TOML → VOICEVOX音声合成 | 高 | 🔲 |
| F-02 | 台本TOML → Pillowスライド画像生成 | 高 | 🔲 |
| F-03 | 音声 + 画像 → MoviePy動画結合 | 高 | 🔲 |
| F-04 | Claude Codeによる台本自動生成 | 高 | 🔲 |
| F-05 | サムネイル自動生成（Pillow） | 中 | 🔲 |
| F-06 | YouTube Data APIアップロード | 低 | 🔲 |

### 非機能要件

- macOS対応（Windows不要）
- Python 3.11+
- VOICEVOX エンジン（ローカル起動済み前提）
- FFmpeg インストール済み前提
- 完全無人実行可能（Claude Codeから1コマンド）

---

## ディレクトリ構造

```
sales/youtube/
├── README.md
├── scripts/
│   ├── generate_video.py   # メイン: TOML → MP4
│   ├── generate_slides.py  # Pillow スライド生成
│   ├── synthesize_voice.py # VOICEVOX 音声合成
│   └── requirements.txt
├── templates/
│   ├── script_template.toml  # 空テンプレート
│   └── sample_script.toml    # サンプル台本
├── assets/
│   ├── backgrounds/          # 背景画像（PNG）
│   └── fonts/                # フォント（.ttf）
└── output/                   # 生成物（.gitignore対象）
    ├── audio/
    ├── slides/
    └── *.mp4
```

---

## 参考実装

| 名称 | URL | 用途 |
|---|---|---|
| zuma | https://github.com/CookieBox26/zuma | TOML台本→VOICEVOX→MoviePy 完結パイプライン |
| fm_kaisetsu_maker | https://github.com/rerofumi/fm_kaisetsu_maker | 解説動画自動生成 |
| remotion-voicevox-template | https://github.com/nyanko3141592/remotion-voicevox-template | Remotion + VOICEVOX テンプレート |

---

## セットアップ

```bash
# 依存ライブラリ
pip install -r sales/youtube/scripts/requirements.txt

# VOICEVOX エンジン起動確認
curl http://localhost:50021/version

# FFmpeg 確認
ffmpeg -version
```

---

## 編集サンプル参考

実際に参考にしたい動画のURLをここに記録する:
<!-- TODO: 参考チャンネルのURLをここに追加 -->

```
例:
- https://www.youtube.com/watch?v=XXXX  # 参考: 企業解説ゆっくり系
- https://www.youtube.com/watch?v=XXXX  # 参考: 字幕スタイル
```
