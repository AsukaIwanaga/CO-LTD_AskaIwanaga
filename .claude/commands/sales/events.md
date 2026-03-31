# 周辺イベント情報（営業部 — Sonny）

店舗周辺のイベント情報を取得し、営業への影響を確認します。

## フロー

### STEP 1: データ取得

```bash
python3 scripts/scrapers/area_events.py --format json
```

### STEP 2: 表示

```
店舗周辺イベント
date  venue           event_title                 guest_amt       effort(b/a)
                      artist/grup                 time            time   +number
--------------------------------------------------------------------------------
TODAY
MM-dd YOKOHAMA_ARENA  イベント名                   来場者数         影響時刻
                      アーティスト名               開演-終演        影響+客数

FUTURE
MM-dd NISSAN_STADIUM  イベント名                   来場者数         影響時刻
```

### STEP 3: 影響分析（オプション）

Don から分析指示があれば：
- イベント来場者数と過去の客数変動の相関
- 当日のシフト・仕込み量への提案

### 対象会場
- 横浜アリーナ（17,000席）
- 日産スタジアム（72,000席）
- 横浜スタジアム（35,000席）
