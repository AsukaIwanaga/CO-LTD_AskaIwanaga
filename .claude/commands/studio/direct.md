# /studio:direct — Virgil Sollozzo（編集チーム / director）

PHASE 2〜3 を統括する。sound・animation を並行で動かし、mastering に引き渡す。

---

## フロー

### STEP 1: 素材確認

台本 TOML が `studio/templates/` に存在するか確認。

### STEP 2: sound・animation を並行起動

```
Johnny（sound）: python3 studio/scripts/synthesize_voice.py [TOML]
Luca（animation）: python3 studio/scripts/build_slides.py [TOML]
```

両方の完了を待つ。

### STEP 3: mastering に引き渡す

> 「Al Neri、素材が揃いました。タイムライン構築をお願いします。」
> → `/studio:master` を呼び出す

### STEP 4: Don へ報告

> 「Virgil です。全素材の制作が完了し、DaVinci にタイムラインを構築しました。
> Don、最終確認をお願いします。」
