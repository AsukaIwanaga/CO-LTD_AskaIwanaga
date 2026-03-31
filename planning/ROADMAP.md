# 開発ロードマップ

> 優先度: 🔴 High / 🟡 Medium / 🟢 Low
> ステータス: `[ ]` 未着手 / `[~]` 実装中 / `[x]` 完了

---

## area_events.py — 周辺イベント影響予測 精度向上

### 短期（すぐ実装可）

- [x] **午後/夜開演フラグの分離**
  開演 16:00 以前 = afternoon（来客流出リスク ⚠）、16:00 以降 = evening（プラス効果）
  実績: K-Arena 午後公演(13:30) → -16.6pp。2026-03-24 実装済み。

- [x] **実績ベース影響係数の導入**
  `sales/event_impact.json` に 2026-03 実績 20 日分を蓄積。
  PIA-ARENA 夜: 0.8% / K-ARENA 夜: 0.5% / ZEPP 夜: 1.5%。2026-03-24 実装済み。

- [~] **🔴 天気補正係数の追加**
  Open-Meteo 実績APIで過去の降水量を取得し、売上との相関を計算。
  雨天日は来客率が低下する補正係数を impact_rate に乗算する。
  → `scripts/area_events.py` の `get_impact_rate()` に weather_factor 引数を追加。
  実装予定: 2026-03-24

### 中期

- [x] **🔴 イベント時刻の自動取得精度向上**
  DuckDuckGo 失敗時に e+ (eplus.jp) / チケットぴあ (t.pia.jp) へ fallback。
  `_ddg_search()` + `_extract_times()` に分離して3段階検索。2026-03-24 実装済み。
  ※ 調査結果: eplus.jp は JS 動的注入（静的 HTML 取得不可）、t.pia.jp はリダイレクト問題あり。
    直接スクレイピングは不可。DuckDuckGo site: 検索（キャッシュ経由）が現実的な上限。
    さらに精度を上げるには Puppeteer 等のヘッドレスブラウザが必要（長期課題へ移行）。

- [x] **🔴 実績フィードバックループ**
  イベント翌日に「昨日の実績 vs 予測」を `event_impact.json` へ自動記録。
  `scripts/record_event_outcome.py` で STX DB → pp 計算 → 係数再計算。2026-03-24 実装済み。

- [x] **🟡 イベントジャンル × 客層の細分化**
  10ジャンル（female_idol / male_idol / band_rock / anime_seiyuu / dance / fanmeet /
  festival / sports / talk_comedy / graduation）で impact_rate に乗数適用。2026-03-24 実装済み。

- [x] **🟡 複数会場同日イベントの加算 vs 競合モデル**
  `calc_multiday_totals()` で同日複数会場の重複補正（n=2: ×0.85, n=3: ×0.75）を適用。
  MULTI-VENUE TOTAL 行としてテンプレートに表示。2026-03-24 実装済み。

### 長期

- [ ] **🟢 曜日ベースラインの充実**
  現状: 火・土・日のイベントなし日がゼロ（全日イベントあり）。
  4月以降に自然蓄積。目標: 各曜日 n≥5。

- [x] **🟢 イベント時刻取得の Playwright 対応**
  `_playwright_search_time()` を追加。eplus.jp → t.pia.jp の順に Chromium で JS レンダリング後に時刻取得。
  DuckDuckGo 3段階 fallback の最終手段として動作。2026-03-24 実装済み。
  ※ イベントが両サイトに未登録の場合（FC限定販売等）は取得不可。

- [ ] **🟢 スカイラーク近隣比較店との差分分析**
  近隣同業態との売上差分でイベント以外の外部要因を除去。
  要: 他店データへのアクセス権限確認。

---

## morning.md — 朝のブリーフィング

- [ ] **🟡 STEP 1 並列実行の高速化**
  現状は各取得がシーケンシャル。Python `threading` や MCP の並列呼び出しで高速化。

- [ ] **🟡 GT保土ヶ谷駅前 営業データ取得**
  `stx_kanrihyo.py` の多店舗対応後に有効化。
  店舗コード: 要確認（STORE2_CODE として .env に追加）。

- [ ] **🟢 018974@skylark.co.jp メール読み取り**
  `.mcp.json` に store アカウント用 Gmail MCP を追加。
  認証: `.env` の `STORE_EMAIL` / `STORE_PASSWORD` を参照。

---

## その他

- [ ] **🟡 portal.py セッション自動更新**
  現状: セッション切れ時に手動再ログインが必要。
  自動的に `portal_login.py` を呼び出して再認証する仕組みを追加。

---

_最終更新: 2026-03-24 (複数会場合算モデル・e+fallback 追加)_
