#!/usr/bin/env python3
"""
record_event_outcome.py — イベント × 売上実績を記録し、影響係数を自動更新する

使い方:
  python3 scripts/record_event_outcome.py           # 昨日分を自動記録
  python3 scripts/record_event_outcome.py --date 2026-03-19  # 指定日

フロー:
  1. event_impact.json から対象日のイベントを特定
  2. stx_kanrihyo.db から当日の売上実績(rate%, yoy%)を取得
  3. 曜日別ベースラインと比較して影響度(pp)を算出
  4. events[] に outcome を追記
  5. 会場別の平均影響係数を再計算して venue_impact_rates を更新
"""

import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT       = Path(__file__).parent.parent
IMPACT_JSON = ROOT / "sales" / "event_impact.json"
STX_DB      = Path("/Users/askaiwanaga/CO-LTD_AskaIwanaga/data/stx_kanrihyo.db")
STORE_CODE  = "018974"


def load_impact() -> dict:
    if IMPACT_JSON.exists():
        return json.loads(IMPACT_JSON.read_text())
    return {"venue_impact_rates": {}, "events": []}


def save_impact(data: dict) -> None:
    IMPACT_JSON.parent.mkdir(parents=True, exist_ok=True)
    IMPACT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def get_sales(target: date) -> dict | None:
    """STX DB から当日実績を取得する。"""
    if not STX_DB.exists():
        return None
    conn = sqlite3.connect(STX_DB)
    cur  = conn.cursor()
    cur.execute("""
        SELECT date, day_of_week, total_plan, total_actual, total_rate, total_yoy,
               guest_plan, guest_actual, guest_rate
        FROM daily_sales
        WHERE date = ? AND store_code = ? AND total_actual > 0
    """, (target.isoformat(), STORE_CODE))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "date": row[0], "dow": row[1],
        "plan": row[2], "actual": row[3],
        "rate": row[4], "yoy": row[5],
        "g_plan": row[6], "g_actual": row[7], "g_rate": row[8],
    }


def calc_pp(rate: float, dow: str, baselines: dict) -> float | None:
    """曜日ベースライン比の pp 差を返す。ベースラインがなければ None。"""
    if dow not in baselines:
        return None
    return round(rate - baselines[dow], 1)


def recalc_impact_rates(data: dict) -> None:
    """
    events[] の記録済み rate_pp からベースライン補正済み pp を集計し、
    会場別・セッション別の impact_rate（来場者数に対する割合）を更新する。

    impact_rate = (pp / 100 * avg_plan) / (capacity * fill_rate) / 来場者影響率換算
    簡易版: impact_rate = (avg pp uplift / 100 * avg_plan_k * 1000) / capacity / avg_check
      avg_plan_k : 千円単位の平均日次計画売上
      avg_check  : A/C（客単価） 〜 1,100 円
    """
    from collections import defaultdict

    # area_events.py の venue_key と統一（ZEPP → ZEPP_yokohama）
    VENUE_CAPACITY = {
        "K-ARENA":       20033,
        "PIA-ARENA":     10000,
        "ZEPP":          2506,
        "ZEPP_yokohama": 2506,
    }
    VENUE_KEY_MAP = {"ZEPP": "ZEPP_yokohama"}  # JSON 内のキーを正規化
    AVG_PLAN  = 540   # 千円
    AVG_CHECK = 1100  # 円

    baselines = data.get("day_of_week_baseline_rate", {})

    # 実績 pp がある events を集計
    venue_session_pps: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for ev in data.get("events", []):
        if ev.get("rate_pp") is None:
            continue
        vk      = ev["venue"]
        session = ev.get("session", "evening")
        venue_session_pps[vk][session].append(ev["rate_pp"])

    updated_rates: dict[str, dict] = {}
    for vk_raw, sessions in venue_session_pps.items():
        vk  = VENUE_KEY_MAP.get(vk_raw, vk_raw)   # キー正規化
        cap = VENUE_CAPACITY.get(vk_raw) or VENUE_CAPACITY.get(vk)
        if not cap:
            continue
        updated_rates[vk] = {}
        for session, pps in sessions.items():
            if not pps:
                continue
            avg_pp = sum(pps) / len(pps)
            # pp uplift → 売上増分 → 追加来客数 → impact_rate
            additional_sales  = avg_pp / 100 * AVG_PLAN * 1000   # 円
            additional_guests = additional_sales / AVG_CHECK
            # fill_rate は 0.80 で近似
            impact_rate = round(additional_guests / (cap * 0.80), 4)
            updated_rates[vk][session] = impact_rate
            print(f"  [{vk}][{session}] avg_pp={avg_pp:+.1f}pp n={len(pps)} → impact_rate={impact_rate:.4f}")

    # 既存値とマージ（実績がないセッションは既存値を保持）
    existing = data.get("venue_impact_rates", {})
    for vk, sessions in updated_rates.items():
        if vk not in existing:
            existing[vk] = {}
        existing[vk].update(sessions)
    data["venue_impact_rates"] = existing


def record_outcome(target: date) -> None:
    data    = load_impact()
    sales   = get_sales(target)
    baselines = data.get("day_of_week_baseline_rate", {})

    if not sales:
        print(f"[WARN] {target} の売上データが見つかりません（未記録 or 休業日）", file=sys.stderr)
        return

    # 対象日のイベント一覧を取得
    target_events = [ev for ev in data.get("events", []) if ev["date"] == target.isoformat()]
    if not target_events:
        print(f"[INFO] {target} のイベント記録なし。スキップします。")
        return

    pp = calc_pp(sales["rate"], sales["dow"], baselines)
    print(f"\n{target} ({sales['dow']})  plan={sales['plan']}千円  actual={sales['actual']}千円")
    print(f"  rate={sales['rate']:.1f}%  yoy={sales['yoy'] or 0:.1f}%  ベースライン差={pp:+.1f}pp" if pp is not None else
          f"  rate={sales['rate']:.1f}%  yoy={sales['yoy'] or 0:.1f}%  (ベースライン不足)")

    # 各イベントに outcome を書き込む
    updated = 0
    for ev in data["events"]:
        if ev["date"] != target.isoformat():
            continue
        if ev.get("rate_pp") is not None:
            print(f"  [{ev['venue']}] 既に記録済み (rate_pp={ev['rate_pp']:+.1f}pp) — スキップ")
            continue
        ev["rate_pp"] = pp
        ev["actual_rate"] = sales["rate"]
        ev["actual_yoy"]  = sales["yoy"]
        pp_str = f"{pp:+.1f}" if pp is not None else "不明"
        print(f"  [{ev['venue']}] {ev['event'][:40]} → rate_pp={pp_str}pp 記録")
        updated += 1

    if updated > 0:
        # 係数再計算
        print("\n影響係数を再計算中...")
        recalc_impact_rates(data)
        data["_last_updated"] = target.isoformat()
        save_impact(data)
        print(f"\n✅ {IMPACT_JSON} を更新しました。")
    else:
        print("更新なし。")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="イベント実績フィードバック記録")
    parser.add_argument("--date", default=None, help="対象日 YYYY-MM-DD（デフォルト: 昨日）")
    args = parser.parse_args()

    target = date.fromisoformat(args.date) if args.date else date.today() - timedelta(days=1)
    print(f"[INFO] {target} の実績を記録します...")
    record_outcome(target)


if __name__ == "__main__":
    main()
