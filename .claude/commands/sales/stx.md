# STX 営業データ確認（営業部 — Sonny）

店舗の営業管理表データを確認・分析します。

## フロー

### STEP 1: データ取得

```bash
python3 scripts/scrapers/stx_kanrihyo.py --summary
```

を実行し、最新の営業データサマリーを取得する。

### STEP 2: 表示

取得したデータを以下の形式で表示：

```
@GT保土ヶ谷駅前 (017807)
time       index       target        actual    diff%    comp%
--------------------------------------------------------------------------------
today      amt         ###,###
           t/c             ###
           a/c           #,###
           lbr%          ##.##

yesterday  amt         ###,###      ###,###   ±##.#%   ±##.#%
           ...

this-M     amt     ###,###,###  ##,###,###   ±##.#%   ±##.#%
           ...
```

### STEP 3: 分析（オプション）

Don から「分析して」「どう思う？」等の指示があれば：
- 前日比の変動要因を推測
- 月累計の進捗評価
- 人件費率の評価
- 改善提案

### データソース
- SQLite DB: `data/stx_kanrihyo.db`
- スクリプト: `scripts/scrapers/stx_kanrihyo.py`
