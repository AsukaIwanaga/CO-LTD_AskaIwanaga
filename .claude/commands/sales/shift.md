# シフト管理（営業部 — Sonny）

らくしふのシフトデータを確認・管理します。

## フロー

### STEP 1: 最新シフト確認

`drafts/rakushifu_shifts_YYYY-MM.json` を読み込み、今月のシフトを表示。

差分ファイル `drafts/rakushifu_diff_YYYY-MM-DD.json` があれば変更点も表示。

### STEP 2: 表示

```
シフト（YYYY年MM月）
date        day   time              hours
--------------------------------------------------------------------------------
MM-DD       Mon   09:00 - 17:00    8.0h
MM-DD       Tue   16:00 - 23:30    7.5h
...

今月合計: XXX.Xh
```

### STEP 3: カレンダー反映（オプション）

差分がある場合：
「Google Calendar に反映しますか？」
→ はい: MCP `gcal_create_event` で `primary` に登録
  - summary: "🏪 シフト勤務"
  - colorId: "6" (Tangerine)

### データソース
- シフトJSON: `drafts/rakushifu_shifts_YYYY-MM.json`
- 差分JSON: `drafts/rakushifu_diff_YYYY-MM-DD.json`
- 同期スクリプト: `scripts/scrapers/rakushifu_sync.py`
- cron: 毎日 01:00 自動同期
