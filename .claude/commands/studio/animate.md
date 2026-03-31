# /studio:animate — Luca Brasi（アニメ映像チーム / animation）

台本 TOML からスライド画像・立ち絵切り替えマップ・サムネイルを生成する。

---

## フロー

### STEP 1: スライド画像生成

```bash
python3 studio/scripts/build_slides.py [TOML_PATH]
```

- 各セリフに対応したスライド PNG を生成（Pillow）
- 背景: `studio/assets/backgrounds/default.png`
- テキスト: セリフ内容をスライド下部に表示
- 出力: `studio/output/slides/slide_001.png` 〜

### STEP 2: 立ち絵切り替えマップ生成

- speaker（reimu/marisa）に応じて立ち絵を切り替えるタイミングを JSON で出力
- 出力: `studio/output/slides/character_map.json`

### STEP 3: サムネイル生成

```bash
python3 studio/scripts/generate_thumbnail.py [TOML_PATH]
```

- meta.thumbnail_text をベースに 1280×720 PNG を生成
- 出力: `studio/output/thumbnails/thumbnail.png`

### STEP 4: 完了報告

> 「Luca からの報告: スライド XX 枚・サムネイル 1 枚を生成しました。」
