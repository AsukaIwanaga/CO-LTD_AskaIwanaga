# YouTube 台本生成（営業部 — Sonny）

ゆっくり実況形式の解説動画台本を生成し、動画制作パイプラインを実行する。

---

## フロー

### STEP 1: 題材・要件の確認

Donから以下を確認する（または引数から取得）：

1. **題材**（例: 「すかいらーくの赤字経営と生存戦略」）
2. **尺**（目安: short=5分 / normal=10分 / long=15分、デフォルト: normal）
3. **重点ポイント**（強調したいデータ・エピソード、任意）

```
「Don、題材と尺を教えてください。（例: 「すかいらーくの赤字経営について、10分尺で」）」
```

### STEP 2: 台本生成

STEP 1 の情報をもとに、`sales/youtube/templates/script_template.toml` の形式で台本を生成する。

**生成ルール:**
- 尺に応じた行数: short=30行 / normal=60行 / long=90行 程度
- 霊夢（reimu）が解説役、魔理沙（marisa）が聞き役
- 構成: intro(3〜5行) → main(本編) → conclusion(3〜5行)
- 1行あたり80〜120文字（VOICEVOX読み上げ時に自然なテンポになる長さ）
- 数字・固有名詞は正確に（実際の業績データ・ニュースを根拠にする）
- 最後の行は必ず「ゆっくりしていってね！」

**サムネイル用テキスト:**
- インパクトのある短いフレーズ（例: 「赤字なのに黒字の謎」「業界の闇」）

### STEP 3: 台本ファイル保存

生成した台本を以下のパスに保存する：

```
sales/youtube/templates/script_YYYY-MM-DD_タイトル略称.toml
```

（例: `script_2026-03-26_skylark-akaji.toml`）

### STEP 4: 動画生成（オプション）

「動画も生成しますか？」と確認する。

**「はい」の場合:**

```bash
# VOICEVOX 起動確認
curl -s http://localhost:50021/version

# 動画生成
python3 sales/youtube/scripts/generate_video.py sales/youtube/templates/script_YYYY-MM-DD_*.toml
```

VOICEVOX が起動していない場合:
> 「VOICEVOX エンジンが起動していません。起動してから再実行してください。台本は保存済みです。」

**生成物:**
- `sales/youtube/output/audio/` — WAV音声ファイル群
- `sales/youtube/output/slides/` — スライド画像群
- `sales/youtube/output/YYYY-MM-DD_タイトル.mp4` — 完成動画

### STEP 5: 締め

台本保存完了後:
> 「Don、台本を保存しました: [ファイルパス]
> 総行数: XX行 / 推定尺: 約XX分
> 動画生成はいつでも `/sales:youtube` で実行できます。」

---

## 参考: VOICEVOX スピーカーID

| キャラ | speaker | ID |
|---|---|---|
| 四国めたん（ノーマル） | metan | 2 |
| ずんだもん（ノーマル） | zundamon | 3 |
| 春日部つむぎ | tsumugi | 8 |
| 波音リツ | ritu | 9 |
| 雨晴はう | hau | 10 |
| 青山龍星（ノーマル） | ryusei | 13 |

ゆっくり解説の定番: 霊夢=めたん(2) / 魔理沙=ずんだもん(3)

---

## 注意事項

- 台本内の企業データ・数字は実際の公開情報を根拠とし、推測で書かない
- 特定個人への批判・誹謗中傷は含めない
- 台本生成後、Don が内容を確認してから動画生成に進む
