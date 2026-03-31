#!/usr/bin/env python3
"""
resas_flow.py — みなとみらいエリア来訪者データ × GTみなとみらい客数 相関分析

【調査結果サマリー】
RESAS API は 2025-03-24 をもってサービス終了済み。日次人流データは提供外だった。
国交省 PPP 人流オープンデータ（geospatial.jp）も月次粒度かつ 2021年で更新停止。
現時点で無料・日次・API の三条件を満たす公的人流データは存在しない。

→ 推奨アプローチ: イベント来場者数・気象・曜日・祝日フラグをプロキシ変数として
  stx_kanrihyo.db の guest_actual との重回帰分析を行う。

将来的に商用人流データ（NTTドコモ モバイル空間統計 / AGOOP）を契約した場合は
fetch_flow_api() を実装することで差し替えられる構造にしている。

Usage:
    python3 scripts/resas_flow.py --summary         # 相関サマリーを表示
    python3 scripts/resas_flow.py --summary --plot  # 散布図も出力（matplotlib 要）
    python3 scripts/resas_flow.py --month 2026-03   # 対象月を指定
    python3 scripts/resas_flow.py --export          # 分析用 CSV を出力

【将来追加予定】
    --fetch-flow  外部 API から人流データを取得して flow_data テーブルへ保存
"""

import argparse
import csv
import json
import os
import sqlite3
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent / "../.env")
except ImportError:
    pass  # python-dotenv 未インストール時はスキップ

# ─── 設定 ─────────────────────────────────────────────────────────────────────

DB_PATH    = Path("/Users/askaiwanaga/CO-LTD_AskaIwanaga/data/stx_kanrihyo.db")
STORE_CODE = "018974"
STORE_NAME = "GTみなとみらい"

# 将来使う想定の人流 API 設定（現時点では未実装）
RESAS_API_KEY  = os.getenv("RESAS_API_KEY", "")    # RESAS は終了済みだが変数名を保持
FLOW_API_KEY   = os.getenv("FLOW_API_KEY", "")     # 将来の商用 API キー（未定）
FLOW_API_URL   = os.getenv("FLOW_API_URL", "")     # 将来の商用 API エンドポイント（未定）

# みなとみらいエリア座標（1km メッシュの中心近傍）
MINATO_MIRAI_LAT = 35.4560
MINATO_MIRAI_LON = 139.6323

# 横浜市・みなとみらいエリアコード（RESAS / 国交省 PPP 用）
PREF_CODE  = "14"       # 神奈川県
CITY_CODE  = "14103"    # 横浜市西区（みなとみらい所在）
CITY_CODE2 = "14101"    # 横浜市中区（みなとみらい一部）

# 祝日判定（内閣府公開データをキャッシュした簡易版）
# 不完全なリストなので用途に合わせて拡充すること
HOLIDAYS_2026 = {
    "2026-01-01", "2026-01-12",  # 元日・成人の日
    "2026-02-11", "2026-02-23",  # 建国記念日・天皇誕生日
    "2026-03-20",                # 春分の日
    "2026-04-29", "2026-05-03", "2026-05-04", "2026-05-05", "2026-05-06",
    "2026-07-20", "2026-08-11",
    "2026-09-21", "2026-09-22", "2026-09-23",
    "2026-10-12", "2026-11-03", "2026-11-23",
}

# ─── DB 初期化（flow_data テーブル: 将来の人流データ格納用） ────────────────

def init_db(conn: sqlite3.Connection):
    """
    flow_data テーブルを作成（将来の人流 API データ格納用）。
    商用人流 API（モバイル空間統計など）を契約した際に使用する。
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flow_data (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT    NOT NULL,   -- YYYY-MM-DD
            area_code   TEXT    NOT NULL,   -- エリアコード（メッシュ / 駅 / 市区町村）
            area_name   TEXT,
            visitor_cnt INTEGER,           -- 来訪者数（推計）
            source      TEXT,              -- データソース名
            fetched_at  TEXT,
            UNIQUE(date, area_code, source)
        )
    """)
    conn.commit()


# ─── [将来実装] 人流 API からデータ取得 ───────────────────────────────────────

def fetch_flow_api(target_date: str) -> list[dict]:
    """
    外部人流 API からみなとみらいエリアの日次来訪者数を取得する。

    【現状】
    利用可能な無料・日次・API の三条件を満たす公的人流データは存在しないため
    本関数は未実装（空リストを返す）。

    【将来の実装候補】
    - NTTドコモ モバイル空間統計 (https://mobaku.jp/)
      - 250m メッシュ / 1時間単位 / 日次集計
      - 商用サービス（要契約）
      - AWS/Tableau 連携、CSV 配信

    - AGOOP 流動人口データ / マチレポ (https://www.agoop.co.jp/)
      - GPS ビッグデータ / スマートフォンベース
      - 商用サービス（要問合せ）

    - 横浜市営地下鉄 日別乗降客数（非公開）
      - 現在は月次・年次データのみ公表
      - 情報公開請求で日次データ入手の可能性あり

    Args:
        target_date: YYYY-MM-DD 形式の対象日

    Returns:
        [{"date": "YYYY-MM-DD", "area_code": str, "area_name": str,
          "visitor_cnt": int, "source": str}]
    """
    if not FLOW_API_KEY or not FLOW_API_URL:
        # API キー未設定 → 空リストを返す（エラーにしない）
        return []

    # --- 実装例（将来） ---
    # import urllib.parse
    # params = urllib.parse.urlencode({
    #     "date":    target_date,
    #     "lat":     MINATO_MIRAI_LAT,
    #     "lon":     MINATO_MIRAI_LON,
    #     "apikey":  FLOW_API_KEY,
    # })
    # url = f"{FLOW_API_URL}/daily?{params}"
    # with urllib.request.urlopen(url, timeout=15) as resp:
    #     data = json.loads(resp.read().decode())
    # return data.get("records", [])

    return []


def save_flow_data(records: list[dict]) -> int:
    """取得した人流データを flow_data テーブルへ upsert。"""
    if not records:
        return 0

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    fetched_at = datetime.now().isoformat()

    upserted = 0
    for r in records:
        conn.execute("""
            INSERT INTO flow_data (date, area_code, area_name, visitor_cnt, source, fetched_at)
            VALUES (:date, :area_code, :area_name, :visitor_cnt, :source, :fetched_at)
            ON CONFLICT(date, area_code, source) DO UPDATE SET
                visitor_cnt = excluded.visitor_cnt,
                fetched_at  = excluded.fetched_at
        """, {**r, "fetched_at": fetched_at})
        upserted += 1

    conn.commit()
    conn.close()
    return upserted


# ─── DB から売上データ取得 ─────────────────────────────────────────────────────

def load_sales_data(year_month: str | None = None) -> list[dict]:
    """
    stx_kanrihyo.db の daily_sales から GTみなとみらい の日次データを取得。

    Args:
        year_month: YYYY-MM 形式（None の場合は全期間）

    Returns:
        行データのリスト（dict 形式）
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    if year_month:
        rows = conn.execute(
            """SELECT date, day_of_week, guest_actual, guest_plan, guest_rate,
                      total_actual, total_plan, total_rate
               FROM daily_sales
               WHERE store_code = ? AND year_month = ? AND guest_actual > 0
               ORDER BY date ASC""",
            (STORE_CODE, year_month),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT date, day_of_week, guest_actual, guest_plan, guest_rate,
                      total_actual, total_plan, total_rate
               FROM daily_sales
               WHERE store_code = ? AND guest_actual > 0
               ORDER BY date ASC""",
            (STORE_CODE,),
        ).fetchall()

    conn.close()
    return [dict(r) for r in rows]


# ─── プロキシ変数の計算 ────────────────────────────────────────────────────────

def calc_proxy_features(rows: list[dict]) -> list[dict]:
    """
    人流データが取得できない間の代替説明変数（プロキシ変数）を計算して付加する。

    追加フィールド:
        - is_holiday    : 祝日フラグ（0/1）
        - is_weekend    : 土日フラグ（0/1）
        - month         : 月（季節性）
        - week_of_month : 月内週番号（1-5）
        - day_of_week_n : 曜日を数値化（月=0 〜 日=6）
        - guest_vs_plan : 実績/計画比（達成率）

    将来、人流 API が利用可能になった場合は flow_data テーブルを JOIN して
    visitor_cnt フィールドを追加する。
    """
    DOW_MAP = {"月": 0, "火": 1, "水": 2, "木": 3, "金": 4, "土": 5, "日": 6}

    enriched = []
    for r in rows:
        d = r["date"]
        dow = r.get("day_of_week", "")

        dow_n = DOW_MAP.get(dow, -1)
        is_weekend  = 1 if dow_n in (5, 6) else 0
        is_holiday  = 1 if d in HOLIDAYS_2026 else 0

        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            week_of_month = (dt.day - 1) // 7 + 1
            month = dt.month
        except ValueError:
            week_of_month = 0
            month = 0

        guest_vs_plan = (
            r["guest_actual"] / r["guest_plan"]
            if r["guest_plan"] and r["guest_plan"] > 0
            else None
        )

        enriched.append({
            **r,
            "is_holiday":     is_holiday,
            "is_weekend":     is_weekend,
            "month":          month,
            "week_of_month":  week_of_month,
            "day_of_week_n":  dow_n,
            "guest_vs_plan":  guest_vs_plan,
        })

    return enriched


# ─── 相関係数計算 ─────────────────────────────────────────────────────────────

def pearson_r(xs: list[float], ys: list[float]) -> tuple[float, int] | None:
    """
    Pearson 相関係数を計算（stdlib のみ、scipy 不要）。

    Returns:
        (r, n) または None（データ不足時）
    """
    n = len(xs)
    if n < 3:
        return None

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    cov   = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    std_x = (sum((x - mean_x) ** 2 for x in xs) ** 0.5)
    std_y = (sum((y - mean_y) ** 2 for y in ys) ** 0.5)

    if std_x == 0 or std_y == 0:
        return None

    r = cov / (std_x * std_y)
    return round(r, 4), n


def compute_correlations(rows: list[dict]) -> dict:
    """
    guest_actual と各プロキシ変数・将来の visitor_cnt との相関係数を計算。

    Returns:
        {変数名: {"r": float, "n": int, "note": str}}
    """
    results = {}

    guest = [r["guest_actual"] for r in rows if r.get("guest_actual")]

    # 各プロキシ変数との相関
    proxy_vars = {
        "is_weekend":     "土日フラグ（0/1）",
        "is_holiday":     "祝日フラグ（0/1）",
        "day_of_week_n":  "曜日（月=0〜日=6）",
        "month":          "月（季節性）",
        "week_of_month":  "月内週番号",
        "guest_plan":     "計画客数（予算）",
    }

    for col, note in proxy_vars.items():
        pairs = [(r.get(col), r.get("guest_actual"))
                 for r in rows
                 if r.get(col) is not None and r.get("guest_actual")]
        if len(pairs) < 3:
            results[col] = {"r": None, "n": len(pairs), "note": note}
            continue
        xs, ys = zip(*pairs)
        res = pearson_r(list(xs), list(ys))
        if res:
            r, n = res
            results[col] = {"r": r, "n": n, "note": note}

    # 将来: visitor_cnt（人流 API データ）との相関
    flow_pairs = [(r.get("visitor_cnt"), r.get("guest_actual"))
                  for r in rows
                  if r.get("visitor_cnt") is not None and r.get("guest_actual")]
    if flow_pairs:
        xs, ys = zip(*flow_pairs)
        res = pearson_r(list(xs), list(ys))
        if res:
            r, n = res
            results["visitor_cnt"] = {
                "r": r, "n": n,
                "note": "人流 API 来訪者数（外部データ）"
            }
    else:
        results["visitor_cnt"] = {
            "r": None, "n": 0,
            "note": "人流 API 来訪者数（未取得 — fetch_flow_api() を実装すること）"
        }

    return results


# ─── サマリー表示 ─────────────────────────────────────────────────────────────

def print_summary(year_month: str | None, plot: bool = False):
    """相関分析サマリーを表示する。"""
    print(f"{'=' * 60}")
    print(f"相関分析: {STORE_NAME} × みなとみらいエリア来訪者")
    if year_month:
        print(f"対象月: {year_month}")
    else:
        print("対象月: 全期間")
    print(f"{'=' * 60}")

    sales_rows = load_sales_data(year_month)
    if not sales_rows:
        print("⚠ 分析対象データが 0 件です。")
        print("  → stx_kanrihyo.py を実行してデータを取得してください。")
        return

    rows = calc_proxy_features(sales_rows)

    # 将来: flow_data から visitor_cnt を結合
    # （現時点では flow_data テーブルにデータがないため JOIN は省略）

    print(f"\nデータ件数: {len(rows)} 日分（guest_actual > 0 のみ）")
    print(f"期間: {rows[0]['date']} 〜 {rows[-1]['date']}\n")

    guest_vals = [r["guest_actual"] for r in rows]
    avg  = sum(guest_vals) / len(guest_vals)
    mx   = max(guest_vals)
    mn   = min(guest_vals)
    print(f"guest_actual  平均: {avg:,.0f}  最大: {mx:,}  最小: {mn:,}")
    print()

    # 相関係数
    corr = compute_correlations(rows)
    W = 22
    print(f"{'変数':<{W}}  {'r':>8}   {'n':>4}  メモ")
    print("-" * 70)
    for col, v in corr.items():
        r_str = f"{v['r']:+.4f}" if v["r"] is not None else "  N/A  "
        print(f"{col:<{W}}  {r_str:>8}   {v['n']:>4}  {v['note']}")

    print()
    print("【解釈ガイド】")
    print("  |r| > 0.7 : 強い相関   |r| > 0.4 : 中程度   |r| < 0.2 : ほぼ無相関")
    print()
    print("【人流データ取得状況】")

    if FLOW_API_KEY and FLOW_API_URL:
        print(f"  FLOW_API_KEY: 設定済み")
        print(f"  FLOW_API_URL: {FLOW_API_URL}")
    else:
        print("  ⚠ 人流 API キー未設定（.env に FLOW_API_KEY / FLOW_API_URL を追加）")
        print("  → 現状はプロキシ変数（曜日・祝日・イベントフラグ）のみで分析")
        print()
        print("  【推奨データソース（要検討）】")
        print("  - NTTドコモ モバイル空間統計 https://mobaku.jp/")
        print("    250m メッシュ / 日次 / 有料（要契約）")
        print("  - AGOOP 流動人口データ https://www.agoop.co.jp/")
        print("    GPS ビッグデータ / 有料（要問合せ）")

    if plot:
        _plot_scatter(rows)


def _plot_scatter(rows: list[dict]):
    """散布図を出力（matplotlib が必要）。"""
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.rcParams["font.family"] = "Hiragino Sans"
    except ImportError:
        print("⚠ matplotlib 未インストール。pip install matplotlib で追加してください。")
        return

    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    fig.suptitle(f"{STORE_NAME} guest_actual 相関分析", fontsize=14)

    plot_vars = [
        ("guest_plan",    "計画客数"),
        ("day_of_week_n", "曜日（月=0〜日=6）"),
        ("is_weekend",    "土日フラグ"),
        ("is_holiday",    "祝日フラグ"),
        ("week_of_month", "月内週番号"),
        ("month",         "月"),
    ]

    for ax, (col, label) in zip(axes.flat, plot_vars):
        xs = [r[col] for r in rows if r.get(col) is not None]
        ys = [r["guest_actual"] for r in rows if r.get(col) is not None]
        ax.scatter(xs, ys, alpha=0.6, s=40)
        ax.set_xlabel(label, fontsize=9)
        ax.set_ylabel("guest_actual", fontsize=9)

        res = pearson_r(xs, ys)
        r_str = f"r={res[0]:+.3f}" if res else "r=N/A"
        ax.set_title(f"{col}  ({r_str})", fontsize=9)

    plt.tight_layout()
    out_path = Path(__file__).parent / f"../../drafts/resas_flow_scatter_{date.today().isoformat()}.png"
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    print(f"  散布図を保存: {out_path.resolve()}")
    plt.close()


# ─── CSV エクスポート ─────────────────────────────────────────────────────────

def export_csv(year_month: str | None):
    """分析用 CSV を drafts/ に出力する。"""
    sales_rows = load_sales_data(year_month)
    if not sales_rows:
        print("⚠ エクスポート対象データが 0 件です。")
        return

    rows = calc_proxy_features(sales_rows)

    suffix  = year_month or "all"
    out_path = Path(__file__).parent / f"../../drafts/resas_flow_{suffix}.csv"

    fields = [
        "date", "day_of_week", "guest_actual", "guest_plan", "guest_rate",
        "total_actual", "total_plan", "total_rate",
        "is_holiday", "is_weekend", "day_of_week_n",
        "month", "week_of_month", "guest_vs_plan",
    ]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ CSV エクスポート: {out_path.resolve()}  ({len(rows)} 行)")


# ─── メイン ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="みなとみらいエリア来訪者データ × GTみなとみらい客数 相関分析"
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="相関分析サマリーを表示"
    )
    parser.add_argument(
        "--plot", action="store_true",
        help="散布図を出力（--summary と併用）"
    )
    parser.add_argument(
        "--month", default=None,
        help="対象月 YYYY-MM（デフォルト: 全期間）"
    )
    parser.add_argument(
        "--export", action="store_true",
        help="分析用 CSV を drafts/ に出力"
    )
    parser.add_argument(
        "--fetch-flow", action="store_true",
        help="人流 API からデータを取得して flow_data テーブルへ保存（要 API キー設定）"
    )
    args = parser.parse_args()

    if args.fetch_flow:
        target = args.month or date.today().isoformat()[:7]
        print(f"人流データ取得: {target}")
        if not FLOW_API_KEY:
            print("⚠ .env に FLOW_API_KEY が設定されていません。")
            print("  人流 API の選定・契約後に FLOW_API_KEY / FLOW_API_URL を設定してください。")
            sys.exit(1)
        # 月の全日付に対して fetch
        from datetime import timedelta
        import calendar
        year, month_n = map(int, target.split("-"))
        _, last_day = calendar.monthrange(year, month_n)
        total_saved = 0
        for day in range(1, last_day + 1):
            d_str = f"{year:04d}-{month_n:02d}-{day:02d}"
            records = fetch_flow_api(d_str)
            total_saved += save_flow_data(records)
        print(f"✓ 保存: {total_saved} 件")
        return

    if args.export:
        export_csv(args.month)
        return

    if args.summary:
        print_summary(args.month, plot=args.plot)
        return

    # デフォルト: --summary と同等
    print_summary(args.month, plot=args.plot)


if __name__ == "__main__":
    main()
