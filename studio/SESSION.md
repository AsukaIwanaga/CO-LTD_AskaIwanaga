# Studio セットアップ進捗記録

最終更新: 2026-03-26

---

## 前回の続きから再開する方法

新しいセッションで以下を伝えるだけでOK：

> 「studio部門のセットアップの続きをやりたい。SESSION.mdを確認して。」

---

## 現在の状態（2026-03-26 時点）

### ✅ 完了済み

| 項目 | 詳細 |
|---|---|
| studio/ ディレクトリ構成 | 独立部門として設立済み |
| 台本テンプレート | `studio/templates/script_template.toml` |
| サンプル台本 | `studio/templates/script_2026-03-26_gasoline-mitooshi.toml`（62行）|
| 背景画像 | `studio/assets/backgrounds/default.png`（1920×1080 生成済み）|
| Pythonスクリプト6本 | synthesize_voice / build_slides / generate_thumbnail / build_timeline / export_video / analyze_youtube |
| yt-dlp インストール | `pip install yt-dlp` 済み |
| 参考動画・BGM調査 | `studio/references.md` に記録済み |
| DaVinci Resolve 20 | インストール済み（`/Applications/DaVinci Resolve/`）|
| Python API パス設定 | `~/.zprofile` に PYTHONPATH・RESOLVE_SCRIPT_API・RESOLVE_SCRIPT_LIB を追記済み |
| Resolve API 接続方式確定 | macOS では外部ターミナルからの接続不可。`fusion.GetResolve()` を使い Workspace→Scripts から実行する方式に変更 |
| Resolve 内部スクリプト | `studio/resolve_scripts/build_timeline.py` / `export_video.py` 作成・デプロイ済み |
| current_job.json 自動生成 | `synthesize_voice.py` が `studio/output/current_job.json` を生成するよう修正済み |

### 🔲 未完了（次回やること）

| 優先 | 項目 | 内容 |
|---|---|---|
| **1** | **BGM 選定・DL** | `references.md` のBGM候補リストから選んで `studio/assets/bgm/background_loop.mp3` に配置 |
| **2** | **立ち絵素材DL** | BOOTHから reimu.png / marisa.png を DL → `studio/assets/characters/` に配置 |
| **3** | **VOICEVOX インストール** | https://voicevox.hiroshiba.jp/ からmacOS版をインストール |
| **4** | **パイプライン初回テスト** | ガソリン台本でVOICEVOX音声合成 → スライド生成 → DaVinci タイムライン構築まで一通り実行 |

---

## DaVinci Resolve API 接続（次回の手順）

### 環境変数（~/.zprofile に設定済み）

```bash
export RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
export RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
export PYTHONPATH="$PYTHONPATH:$RESOLVE_SCRIPT_API/Modules/"
```

### 接続テスト手順

1. DaVinci Resolve を起動
2. **プロジェクトを1つ開く**（新規でもOK）← これが重要。Project Managerのままだと接続失敗する
3. ターミナルで以下を実行：

```bash
source ~/.zprofile
python3 -c "
import DaVinciResolveScript as dvr
resolve = dvr.scriptapp('Resolve')
if resolve:
    print('接続OK:', resolve.GetVersionString())
else:
    print('接続失敗: プロジェクトが開かれているか確認')
"
```

### 失敗した場合

`config.dat` の Scripting.Mode を確認：
```bash
grep -i script ~/Library/Preferences/Blackmagic\ Design/DaVinci\ Resolve/config.dat
# → System.Scripting.Mode = 1 (コマンドライン許可) であることを確認
```

---

## ファイルパス早見表

| 用途 | パス |
|---|---|
| 台本テンプレート | `studio/templates/script_template.toml` |
| 台本置き場 | `studio/templates/script_YYYY-MM-DD_*.toml` |
| 背景画像 | `studio/assets/backgrounds/default.png` |
| 立ち絵（未配置） | `studio/assets/characters/reimu.png` / `marisa.png` |
| BGM（未配置） | `studio/assets/bgm/background_loop.mp3` |
| 音声出力 | `studio/output/audio/line_001.wav` 〜 |
| スライド出力 | `studio/output/slides/slide_001.png` 〜 |
| 字幕出力 | `studio/output/subtitles/*.srt` |
| 動画出力 | `studio/output/YYYY-MM-DD_タイトル.mp4` |
| 参考動画・BGM候補 | `studio/references.md` |
| スクリプト | `studio/scripts/*.py` |

---

## BGM候補（選択待ち）

`studio/references.md` のBGM候補リストを参照。
おすすめ4曲：

| # | 曲名 | 試聴URL |
|---|---|---|
| A | 2:23 AM（DOVA / ジャズ・落ち着き） | https://youtu.be/16Bj6aPi1A8 |
| C | カナリアスキップ（DOVA / 日常・アコースティック） | https://youtu.be/Ul-ZPV_9jPw |
| H | わくわくクッキングタイム的なBGM（DOVA / 軽快ジャズ） | https://youtu.be/bqIuiphOPYY |
| I | ぐだぐだな感じ（DOVA / コメディー・日常） | https://youtu.be/0VN49iASgxk |

---

## 立ち絵素材（DL待ち）

| 推奨 | サイト | URL |
|---|---|---|
| ⭐最推奨 | ゆっくり霊夢素材本舗（BOOTH）| https://booth.pm/ja/items/3361310 |
| 次点 | 東間式ゆっくり霊夢&魔理沙（BOOTH）| https://booth.pm/ja/items/5488499 |

ZIP解凍後 → `studio/assets/characters/reimu.png` / `marisa.png` に配置
