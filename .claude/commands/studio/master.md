# /studio:master — Al Neri（全体編集チーム / mastering）

音声・映像・字幕が揃った状態で DaVinci Resolve タイムラインを構築し、エクスポートする。

---

## 前提条件

```
studio/output/audio/line_001.wav 〜 line_NNN.wav  ✅ Johnny の成果物
studio/output/subtitles/XXXX.srt                  ✅ Johnny の成果物
studio/output/slides/slide_001.png 〜             ✅ Luca の成果物
studio/assets/backgrounds/default.png             ✅ 素材
studio/assets/bgm/background_loop.mp3             ✅ 素材
```

不足があれば Don に通知して中断。

---

## フロー

### STEP 1: タイムライン構築

```bash
python3 studio/scripts/build_timeline.py [TOML_PATH]
```

DaVinci Resolve Python API で以下を自動実行：

1. 新規プロジェクト作成（`ゆっくり解説_YYYY-MM-DD_タイトル`）
2. タイムライン作成（1920×1080 / 30fps）
3. 背景画像をビデオトラック 1 に全尺配置
4. スライド画像をビデオトラック 2 にセリフ単位で配置
5. 立ち絵をビデオトラック 3 に発話タイミングで切り替え配置
6. WAV 音声をオーディオトラック 1 に順番に配置
7. BGM をオーディオトラック 2 にループ配置（音量 -15dB）
8. SRT 字幕をサブタイトルトラックに読み込み

### STEP 2: Don への確認

> 「Al Neri からの報告: タイムラインを構築しました。
> プロジェクト名: ゆっくり解説_YYYY-MM-DD_タイトル / 総尺: 約 XX 分
> DaVinci Resolve でご確認ください。エクスポートの準備ができたら「エクスポート」と伝えてください。」

### STEP 3: エクスポート

Don の承認後:

```bash
python3 studio/scripts/export_video.py
```

- 設定: H.264 / 1920×1080 / YouTube 向けプリセット
- 出力: `studio/output/YYYY-MM-DD_タイトル.mp4`

> 「Al Neri: エクスポート完了しました → studio/output/YYYY-MM-DD_タイトル.mp4」
