# /studio:edit — Virgil Sollozzo（編集長）

DaVinci Resolve Python API でタイムラインを自動構築し、エクスポートする。

---

## 前提条件

- DaVinci Resolve が起動していること
- `studio/output/audio/` に WAV ファイルが存在すること
- `studio/output/subtitles/` に SRT ファイルが存在すること
- `studio/assets/` に素材が配置されていること

---

## フロー

### STEP 1: 素材確認

以下のファイルが揃っているか確認する：

```
studio/output/audio/line_001.wav 〜 line_NNN.wav  ← Johnny の成果物
studio/output/subtitles/XXXX.srt                  ← Johnny の成果物
studio/assets/backgrounds/default.png             ← 背景画像
studio/assets/characters/reimu.png                ← 霊夢立ち絵
studio/assets/characters/marisa.png               ← 魔理沙立ち絵
studio/assets/bgm/background_loop.mp3             ← BGM
```

不足があれば Don に通知して中断する。

### STEP 2: タイムライン構築

```bash
python3 studio/scripts/build_timeline.py studio/templates/script_YYYY-MM-DD_*.toml
```

DaVinci Resolve Python API で以下を自動実行：

1. 新規プロジェクト作成（`ゆっくり解説_YYYY-MM-DD_タイトル`）
2. タイムライン作成（1080p 30fps）
3. 背景画像をビデオトラック 1 に配置（動画全体の長さで）
4. 立ち絵（霊夢 / 魔理沙）をビデオトラック 2 に配置（発話タイミングで切り替え）
5. 音声クリップ（WAV）をオーディオトラック 1 に順番に配置
6. BGM をオーディオトラック 2 にループ配置（音量 -15dB）
7. SRT 字幕をサブタイトルトラックに読み込み

### STEP 3: Don への確認

> 「Virgil です。DaVinci Resolve にタイムラインを構築しました。
> プロジェクト名: ゆっくり解説_YYYY-MM-DD_タイトル
> 総尺: 約 XX 分
>
> DaVinci Resolve で確認してください。
> 問題なければ「エクスポート」と伝えてください。」

### STEP 4: エクスポート

Don から承認後:

```bash
python3 studio/scripts/export_video.py
```

出力先: `studio/output/YYYY-MM-DD_タイトル.mp4`
エクスポート設定: H.264 / 1080p / YouTube 向けプリセット

完了後:
> 「Virgil です。エクスポート完了しました。
> 出力先: studio/output/YYYY-MM-DD_タイトル.mp4」

---

## DaVinci Resolve Python API 参照

```python
import sys
sys.path.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules")
import DaVinciResolveScript as dvr_script

resolve = dvr_script.scriptapp("Resolve")
project_manager = resolve.GetProjectManager()
project = project_manager.CreateProject("プロジェクト名")
media_pool = project.GetMediaPool()
timeline = media_pool.CreateEmptyTimeline("Timeline 1")
```
