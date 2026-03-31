# /studio:voice — Johnny Fontane（サウンドディレクター）

台本 TOML から VOICEVOX で音声を合成し、SRT 字幕を生成する。

---

## フロー

### STEP 1: VOICEVOX 起動確認

```bash
curl -s http://localhost:50021/version
```

失敗した場合:
> 「Johnny です。VOICEVOX エンジンが起動していません。起動してから再実行してください。」
> → 処理中断

### STEP 2: 台本読み込み

引数で指定された TOML ファイルを読み込む。
指定なしの場合は `studio/templates/` の最新ファイルを使用。

### STEP 3: 音声合成実行

```bash
python3 studio/scripts/synthesize_voice.py [TOML_PATH]
```

スピーカー ID マッピング:
- reimu（霊夢） → VOICEVOX ID: 2（四国めたん ノーマル）
- marisa（魔理沙）→ VOICEVOX ID: 3（ずんだもん ノーマル）

出力先: `studio/output/audio/line_001.wav` 〜 `line_NNN.wav`

### STEP 4: SRT 字幕生成

各 WAV の長さを計測し、タイミングを計算して SRT ファイルを生成する。

出力先: `studio/output/subtitles/TOML名.srt`

### STEP 5: 完了報告

> 「Johnny から報告: XX 件の音声ファイルを生成しました。
> 合計尺: 約 XX 分
> 字幕 SRT: studio/output/subtitles/XXXX.srt」
