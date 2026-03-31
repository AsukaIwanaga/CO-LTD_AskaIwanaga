#!/usr/bin/env python3
"""
STX 営業管理表 データ取得スクリプト

- STX にログインして「営業管理表（日別推移）」を取得
- データを SQLite DB（stx_kanrihyo.db）に保存
- デフォルトは当月データ。--month YYYY-MM で対象月を指定可能

Usage:
    python3 stx_kanrihyo.py               # 当月
    python3 stx_kanrihyo.py --month 2026-02  # 指定月
    python3 stx_kanrihyo.py --summary        # 最新データのサマリーのみ表示
"""

import os, sys, json, sqlite3, argparse, re
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

load_dotenv(dotenv_path=Path(__file__).parent / "../../.env")

# ─── 設定 ────────────────────────────────────────────────────────────────────

EMAIL      = os.getenv("SKYLARK_EMAIL", "")
PASSWORD   = os.getenv("SKYLARK_GOOGLE_PASSWORD", "")

# 店舗設定マップ: code -> name
STORES: dict[str, str] = {
    "017807": "GT保土ヶ谷駅前",
    "018974": "GTみなとみらい",
}
_store2_code = os.getenv("STORE2_CODE", "").strip()
_store2_name = os.getenv("STORE2_NAME", "").strip()
if _store2_code and _store2_code not in STORES:
    STORES[_store2_code] = _store2_name or _store2_code

# デフォルト店舗
STORE_CODE = "017807"
STORE_NAME = "GT保土ヶ谷駅前"

STX_INDEX  = "https://sdsr-co.go.akamai-access.com/stx/index.html"
STX_SEARCH = "https://sdsr-co.go.akamai-access.com/stx/stxKanrihyoSearch.do"
# ガスト ブランドコード（index.html でガストをクリックした先のパラメータより）
KAISHA_CD  = "000001"
BRAND_CD   = "010016"

STATE_PATH = (Path(__file__).parent / "../../drafts/stx_storage_state.json").resolve()
DB_PATH    = Path("/Users/askaiwanaga/CO-LTD_AskaIwanaga/data/stx_kanrihyo.db")


# ─── DB 初期化 ────────────────────────────────────────────────────────────────

def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_sales (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            store_code              TEXT    NOT NULL,
            store_name              TEXT,
            date                    TEXT    NOT NULL,   -- YYYY-MM-DD
            year_month              TEXT    NOT NULL,   -- YYYY-MM
            day_of_week             TEXT,

            -- 総売上高
            total_plan              INTEGER,
            total_actual            INTEGER,
            total_diff              INTEGER,
            total_rate              REAL,   -- 達成率(%)
            total_yoy               REAL,   -- 前年比(%)

            -- 総売上高累計
            cum_plan                INTEGER,
            cum_actual              INTEGER,
            cum_diff                INTEGER,
            cum_rate                REAL,
            cum_yoy                 REAL,

            -- EI売上高
            ei_actual               INTEGER,
            ei_yoy                  REAL,

            -- リザーブ
            reserve_actual          INTEGER,
            reserve_yoy             REAL,

            -- 売店売上
            shop_actual             INTEGER,
            shop_yoy                REAL,

            -- 客数
            guest_plan              INTEGER,
            guest_actual            INTEGER,
            guest_rate              REAL,
            guest_yoy               REAL,

            -- EI単価
            ei_unit_actual          INTEGER,

            fetched_at              TEXT,
            UNIQUE(store_code, date)
        )
    """)
    conn.commit()


# ─── Google ログイン ──────────────────────────────────────────────────────────

def complete_google_login(page):
    try:
        page.wait_for_selector("input[type='email']", timeout=10000)
        page.fill("input[type='email']", EMAIL)
        page.click("#identifierNext")
        page.wait_for_timeout(3000)

        if "challenge/pk" in page.url:
            if "presend" in page.url:
                try:
                    page.click("button:has-text('キャンセル')", timeout=3000)
                    page.wait_for_timeout(1500)
                except Exception:
                    pass
            page.evaluate(
                "Array.from(document.querySelectorAll('button'))"
                ".find(b => b.innerText.includes('別の方法'))?.click()"
            )
            page.wait_for_timeout(3000)
            try:
                page.click("[data-challengetype='11']", timeout=3000)
            except Exception:
                try:
                    page.click("li:has-text('パスワード')", timeout=3000)
                except Exception:
                    pass
            page.wait_for_timeout(2000)

        page.wait_for_selector("input[type='password']:visible", timeout=10000)
        page.fill("input[type='password']:visible", PASSWORD)
        page.click("#passwordNext")
        page.wait_for_timeout(3000)
        return True
    except Exception as e:
        print(f"  Google ログインエラー: {e}")
        return False


# ─── セッション確立 ───────────────────────────────────────────────────────────

def get_authenticated_page(playwright):
    """セッション復元 → 失効時は自動再ログイン"""
    launch_args = {
        "headless": False,
        "args": ["--disable-blink-features=AutomationControlled", "--window-size=1200,800"],
    }

    # セッションファイルがあれば復元を試みる
    if STATE_PATH.exists():
        print("  セッション復元中...")
        browser = playwright.chromium.launch(**launch_args)
        context = browser.new_context(storage_state=str(STATE_PATH), ignore_https_errors=True)
        page = context.new_page()
        page.goto(STX_INDEX)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)

        if "accounts.google.com" not in page.url and "akamai-access.com/stx" in page.url:
            print("  ✓ セッション有効")
            return browser, context, page
        else:
            print("  セッション期限切れ → 再ログイン")
            browser.close()

    # 新規ログイン
    browser = playwright.chromium.launch(**launch_args)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.goto(STX_INDEX)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    if "accounts.google.com" in page.url:
        print("  → Google 認証中...")
        if not complete_google_login(page):
            print("⚠ 自動ログイン失敗。手動でログインしてください...")

    try:
        page.wait_for_url(
            lambda url: "akamai-access.com/stx" in url and "accounts.google.com" not in url,
            timeout=120000,
        )
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        context.storage_state(path=str(STATE_PATH))
        print("  ✓ ログイン完了・セッション保存")
    except Exception as e:
        print(f"⚠ ログインタイムアウト: {e}")

    return browser, context, page


# ─── データ取得 ───────────────────────────────────────────────────────────────

def fetch_month_data(page, year_month: str) -> list[dict]:
    """
    指定月の日別推移データを取得して返す。
    year_month: 'YYYY-MM'
    """
    year, month = year_month.split("-")
    term_monthly_value = f"{year}{month.zfill(2)}"  # 例: "202603"

    # 検索条件設定画面へ（ガストブランドで開く）
    search_init_url = (
        f"{STX_SEARCH}?act=init"
        f"&kaishaCd={KAISHA_CD}"
        f"&brandCd={BRAND_CD}"
        f"&referer=index.html"
    )
    print(f"  検索条件画面へ移動: {year_month}")
    page.goto(search_init_url)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    if "accounts.google.com" in page.url:
        print("⚠ セッション切れ。再ログインが必要です。")
        return []

    # ── 期間: 月次（termClass=M）──
    page.click("input[name='termClass'][value='M']")
    page.wait_for_timeout(300)

    # 月次セレクト
    page.select_option("select[name='termMonthly']", term_monthly_value)

    # ── 表示範囲: 店舗（dispRangeClass=6）──
    page.click("input[name='dispRangeClass'][value='6']")
    page.wait_for_timeout(300)

    # 店舗コード: テキスト入力 + hidden フィールドをJSで直接セット
    page.fill("input[name='hibetsuStoreCdName']", STORE_CODE)
    page.evaluate(f"document.querySelector(\"input[name='hibetsuStoreCd']\").value = '{STORE_CODE}'")

    # ── 集計単位: 店舗選択時は自動無効化されるためスキップ ──

    # ── 予算: 月次計画対比（budgetClass=2）──
    page.click("input[name='budgetClass'][value='2']")

    # ── 前年比: 曜日合わせ（prevYearClass=zy）──
    page.click("input[name='prevYearClass'][value='zy']")

    # 検索実行（フォームsubmit）
    print("  検索実行中...")
    page.evaluate("document.querySelector('form').submit()")

    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # テーブル解析
    return parse_table(page, year_month)


def parse_num(s: str):
    """数値文字列をパース。空・'—'・'0.0' などを適切に処理"""
    if not s or s in ("-", "—", "－", "ー", "　", ""):
        return None
    s = s.replace(",", "").replace(" ", "").strip()
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return None


def parse_time_to_hours(s: str):
    """
    "HH:MM" または "HH:MM:SS" 形式の時間文字列を小数時間に変換。
    例: "109:50" → 109.833...
    """
    if not s or s in ("-", "", "0:00", "0:00:00"):
        return None
    try:
        parts = s.strip().split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return round(h + m / 60, 4)
    except Exception:
        return None


def parse_table(page, year_month: str) -> list[dict]:
    """
    結果テーブルをパースして日別データのリストを返す。

    ページは4テーブル構成:
      table[0]: ヘッダラベル（日付/曜日）
      table[1]: カラムヘッダ（大分類・中分類・小分類）
      table[2]: 日付・曜日（31行）
      table[3]: 全数値データ（31行 × 80+列）
    """
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")

    if len(tables) < 4:
        print(f"  ⚠ テーブル数が不足 ({len(tables)}個)。ページタイトル: {page.title()} / URL: {page.url}")
        return []

    # table[2]: 日付・曜日行
    date_rows = []
    for row in tables[2].find_all("tr"):
        cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
        if cells and re.match(r"^\d{2}/\d{2}$", cells[0]):
            date_rows.append(cells)

    # table[3]: 数値データ行（date_rows と同インデックス）
    data_rows = []
    for row in tables[3].find_all("tr"):
        cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
        if cells:
            data_rows.append(cells)

    if not date_rows or not data_rows:
        print("  ⚠ データ行が見つかりません")
        return []

    if len(date_rows) != len(data_rows):
        print(f"  ⚠ 行数不一致: 日付{len(date_rows)}行 vs データ{len(data_rows)}行")

    print(f"  {len(date_rows)} 日分のデータを取得")

    fetched_at = datetime.now().isoformat()
    records = []

    for dt_cells, d_cells in zip(date_rows, data_rows):
        # 日付解析: MM/DD → YYYY-MM-DD
        date_str = dt_cells[0] if dt_cells else ""
        try:
            _, day = date_str.split("/")
            full_date = f"{year_month}-{day.zfill(2)}"
        except Exception:
            continue

        # 数値列マッピング（table[1] row[2] の順序に対応）
        # col: 0-4=総売上高, 5-9=累計, 10-11=EI売上, 12-13=リザーブ,
        #      14-15=売店売上, 16-19=客数, 20-21=EI客単価（以降は対象外）
        c = d_cells + [None] * 30

        record = {
            "store_code":   STORE_CODE,
            "store_name":   STORE_NAME,
            "date":         full_date,
            "year_month":   year_month,
            "day_of_week":  dt_cells[1] if len(dt_cells) > 1 else None,

            "total_plan":   parse_num(c[0]),
            "total_actual": parse_num(c[1]),
            "total_diff":   parse_num(c[2]),
            "total_rate":   parse_num(c[3]),
            "total_yoy":    parse_num(c[4]),

            "cum_plan":     parse_num(c[5]),
            "cum_actual":   parse_num(c[6]),
            "cum_diff":     parse_num(c[7]),
            "cum_rate":     parse_num(c[8]),
            "cum_yoy":      parse_num(c[9]),

            "ei_actual":    parse_num(c[10]),
            "ei_yoy":       parse_num(c[11]),

            "reserve_actual": parse_num(c[12]),
            "reserve_yoy":    parse_num(c[13]),

            "shop_actual":  parse_num(c[14]),
            "shop_yoy":     parse_num(c[15]),

            "guest_plan":   parse_num(c[16]),
            "guest_actual": parse_num(c[17]),
            "guest_rate":   parse_num(c[18]),
            "guest_yoy":    parse_num(c[19]),

            "ei_unit_actual": parse_num(c[20]),
            "ei_unit_diff":   parse_num(c[21]),   # EI客単価_前年差 (CSV X=23)

            # 総労働時間（EI+デリ+KPIC）: "HH:MM" 形式 (CSV AY=50, AZ=51)
            "labor_plan_text":   c[48] if len(c) > 48 and c[48] else None,
            "labor_actual_text": c[49] if len(c) > 49 and c[49] else None,
            "labor_plan_h":      parse_time_to_hours(c[48] if len(c) > 48 else None),
            "labor_actual_h":    parse_time_to_hours(c[49] if len(c) > 49 else None),

            "fetched_at":   fetched_at,
        }
        records.append(record)

    return records


# ─── DB 保存 ──────────────────────────────────────────────────────────────────

def save_to_db(records: list[dict]) -> int:
    """DB に upsert。追加・更新件数を返す"""
    if not records:
        return 0

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    upserted = 0
    for r in records:
        conn.execute("""
            INSERT INTO daily_sales (
                store_code, store_name, date, year_month, day_of_week,
                total_plan, total_actual, total_diff, total_rate, total_yoy,
                cum_plan, cum_actual, cum_diff, cum_rate, cum_yoy,
                ei_actual, ei_yoy,
                reserve_actual, reserve_yoy,
                shop_actual, shop_yoy,
                guest_plan, guest_actual, guest_rate, guest_yoy,
                ei_unit_actual, ei_unit_diff,
                labor_plan_text, labor_actual_text, labor_plan_h, labor_actual_h,
                fetched_at
            ) VALUES (
                :store_code, :store_name, :date, :year_month, :day_of_week,
                :total_plan, :total_actual, :total_diff, :total_rate, :total_yoy,
                :cum_plan, :cum_actual, :cum_diff, :cum_rate, :cum_yoy,
                :ei_actual, :ei_yoy,
                :reserve_actual, :reserve_yoy,
                :shop_actual, :shop_yoy,
                :guest_plan, :guest_actual, :guest_rate, :guest_yoy,
                :ei_unit_actual, :ei_unit_diff,
                :labor_plan_text, :labor_actual_text, :labor_plan_h, :labor_actual_h,
                :fetched_at
            )
            ON CONFLICT(store_code, date) DO UPDATE SET
                store_name       = excluded.store_name,
                day_of_week      = excluded.day_of_week,
                total_plan       = excluded.total_plan,
                total_actual     = excluded.total_actual,
                total_diff       = excluded.total_diff,
                total_rate       = excluded.total_rate,
                total_yoy        = excluded.total_yoy,
                cum_plan         = excluded.cum_plan,
                cum_actual       = excluded.cum_actual,
                cum_diff         = excluded.cum_diff,
                cum_rate         = excluded.cum_rate,
                cum_yoy          = excluded.cum_yoy,
                ei_actual        = excluded.ei_actual,
                ei_yoy           = excluded.ei_yoy,
                reserve_actual   = excluded.reserve_actual,
                reserve_yoy      = excluded.reserve_yoy,
                shop_actual      = excluded.shop_actual,
                shop_yoy         = excluded.shop_yoy,
                guest_plan       = excluded.guest_plan,
                guest_actual     = excluded.guest_actual,
                guest_rate       = excluded.guest_rate,
                guest_yoy        = excluded.guest_yoy,
                ei_unit_actual   = excluded.ei_unit_actual,
                ei_unit_diff     = excluded.ei_unit_diff,
                labor_plan_text  = excluded.labor_plan_text,
                labor_actual_text = excluded.labor_actual_text,
                labor_plan_h     = excluded.labor_plan_h,
                labor_actual_h   = excluded.labor_actual_h,
                fetched_at       = excluded.fetched_at
        """, r)
        upserted += 1

    conn.commit()
    conn.close()
    return upserted


# ─── サマリー表示 ─────────────────────────────────────────────────────────────

def print_summary(year_month: str | None = None):
    """DB から GAS スタイルの営業レポートを表示（TODAY / LATEST ACT / AVERAGE / THIS MONTH）"""
    WAGE  = 1500
    W_AMT = 12
    W2    = 9

    def fAmt(v):
        if v is None: return "-".rjust(W_AMT)
        return f"{round(v):,}".rjust(W_AMT)

    def fVal(v, lbr=False):
        if v is None: return "-".rjust(W_AMT)
        return (f"{v:.2f}" if lbr else f"{round(v):,}").rjust(W_AMT)

    def fPct(v):
        if v is None: return "-".rjust(W2)
        d = v - 100
        sign = "+" if d >= 0 else "-"
        return "   " + sign + f"{abs(d):.1f}%".rjust(W2 - 4)

    def calc(r):
        if not r: return {}
        tp = r["total_plan"]; ta = r["total_actual"]
        gp = r["guest_plan"];  ga = r["guest_actual"]
        eu = r["ei_unit_actual"]; ed = r["ei_unit_diff"]
        lp = r["labor_plan_h"];   la = r["labor_actual_h"]
        ac_tgt = tp / gp * 1000 if tp and gp else None
        ac_act = ta / ga * 1000 if ta and ga else None
        ac_diff = (ta / ga) / (tp / gp) * 100 if all([ta, ga, tp, gp]) else None
        ac_comp = eu / (eu - ed) * 100 if eu and ed and eu != ed else None
        lbr_tgt = WAGE * lp / (tp * 1000) * 100 if lp and tp else None
        lbr_act = WAGE * la / (ta * 1000) * 100 if la and ta else None
        lbr_diff = lbr_act / lbr_tgt * 100 if lbr_act and lbr_tgt else None
        return dict(
            tgt_amt=tp, act_amt=ta, diff_amt=r["total_rate"], comp_amt=r["total_yoy"],
            tgt_tc=gp, act_tc=ga, diff_tc=r["guest_rate"], comp_tc=r["guest_yoy"],
            tgt_ac=ac_tgt, act_ac=ac_act, diff_ac=ac_diff, comp_ac=ac_comp,
            lbr_tgt=lbr_tgt, lbr_act=lbr_act, lbr_diff=lbr_diff,
        )

    def avg_calc(rows):
        def pick(fn):
            v = [fn(r) for r in rows if fn(r) is not None]
            return sum(v) / len(v) if v else None
        return dict(
            diff_amt=pick(lambda r: r["total_rate"]),
            comp_amt=pick(lambda r: r["total_yoy"]),
            diff_tc=pick(lambda r: r["guest_rate"]),
            comp_tc=pick(lambda r: r["guest_yoy"]),
            ac_act=pick(lambda r: r["total_actual"] / r["guest_actual"] * 1000
                        if r["total_actual"] and r["guest_actual"] else None),
            ac_tgt=pick(lambda r: r["total_plan"] / r["guest_plan"] * 1000
                        if r["total_plan"] and r["guest_plan"] else None),
            ac_diff=pick(lambda r: (r["total_actual"] / r["guest_actual"]) /
                         (r["total_plan"] / r["guest_plan"]) * 100
                         if all([r["total_actual"], r["guest_actual"], r["total_plan"], r["guest_plan"]]) else None),
            ac_comp=pick(lambda r: r["ei_unit_actual"] / (r["ei_unit_actual"] - r["ei_unit_diff"]) * 100
                         if r["ei_unit_actual"] and r["ei_unit_diff"] and r["ei_unit_actual"] != r["ei_unit_diff"] else None),
            lbr_act=pick(lambda r: WAGE * r["labor_actual_h"] / (r["total_actual"] * 1000) * 100
                         if r["labor_actual_h"] and r["total_actual"] else None),
            lbr_tgt_avg=pick(lambda r: WAGE * r["labor_plan_h"] / (r["total_plan"] * 1000) * 100
                             if r["labor_plan_h"] and r["total_plan"] else None),
            lbr_diff=pick(lambda r: (WAGE * r["labor_actual_h"] / (r["total_actual"] * 1000) * 100) /
                          (WAGE * r["labor_plan_h"] / (r["total_plan"] * 1000) * 100) * 100
                          if all([r["labor_actual_h"], r["labor_plan_h"], r["total_actual"], r["total_plan"]]) else None),
            amt_sum=sum(r["total_actual"] or 0 for r in rows),
            tc_sum=sum(r["guest_actual"] or 0 for r in rows),
            tgt_amt_avg=pick(lambda r: r["total_plan"]),
            tgt_tc_avg=pick(lambda r: r["guest_plan"]),
            tgt_amt_sum=sum(r["total_plan"] or 0 for r in rows),
            tgt_tc_sum=sum(r["guest_plan"] or 0 for r in rows),
        )

    if not year_month:
        year_month = date.today().strftime("%Y-%m")

    today_str = date.today().isoformat()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    rows = conn.execute(
        "SELECT * FROM daily_sales WHERE store_code=? AND year_month=? ORDER BY date ASC",
        (STORE_CODE, year_month)
    ).fetchall()
    conn.close()

    act_rows  = [r for r in rows if r["total_actual"] and r["total_actual"] > 0]
    latest    = act_rows[-1] if act_rows else None
    today_row = next((r for r in rows if r["date"] == today_str), None)

    td = calc(today_row)
    ld = calc(latest)
    ag = avg_calc(act_rows)

    hdr1 = " " * 4 + "TGT".rjust(W_AMT)
    hdr2 = " " * 4 + "ACT".rjust(W_AMT) + "DIFF%".rjust(W2) + "COMP%".rjust(W2)
    hdr3 = " " * 4 + "TGT".rjust(W_AMT) + "ACT".rjust(W_AMT) + "DIFF%".rjust(W2) + "COMP%".rjust(W2)

    L = [f"📊 {STORE_NAME}　{year_month}", ""]

    # TODAY
    L += ["TODAY", hdr1,
          "AMT " + fAmt(td.get("tgt_amt")),
          "T/C " + fVal(td.get("tgt_tc")),
          "A/C " + fVal(td.get("tgt_ac")),
          "LBR%" + fVal(td.get("lbr_tgt"), True), ""]

    # LATEST ACT
    lat_label = latest["date"][5:] + " (ACT)" if latest else "LATEST (ACT)"
    L += [lat_label, hdr3,
          "AMT " + fAmt(ld.get("tgt_amt"))      + fAmt(ld.get("act_amt"))      + fPct(ld.get("diff_amt")) + fPct(ld.get("comp_amt")),
          "T/C " + fVal(ld.get("tgt_tc"))        + fVal(ld.get("act_tc"))        + fPct(ld.get("diff_tc"))  + fPct(ld.get("comp_tc")),
          "A/C " + fVal(ld.get("tgt_ac"))        + fVal(ld.get("act_ac"))        + fPct(ld.get("diff_ac"))  + fPct(ld.get("comp_ac")),
          "LBR%" + fVal(ld.get("lbr_tgt"), True) + fVal(ld.get("lbr_act"), True) + fPct(ld.get("lbr_diff")), ""]

    # AVERAGE
    L += ["AVERAGE", hdr3,
          "AMT " + fAmt(ag.get("tgt_amt_avg"))      + fAmt(None)                   + fPct(ag.get("diff_amt")) + fPct(ag.get("comp_amt")),
          "T/C " + fVal(ag.get("tgt_tc_avg"))        + fVal(None)                   + fPct(ag.get("diff_tc"))  + fPct(ag.get("comp_tc")),
          "A/C " + fVal(ag.get("ac_tgt"))            + fVal(ag.get("ac_act"))       + fPct(ag.get("ac_diff"))  + fPct(ag.get("ac_comp")),
          "LBR%" + fVal(ag.get("lbr_tgt_avg"), True) + fVal(ag.get("lbr_act"),True) + fPct(ag.get("lbr_diff")), ""]

    # THIS MONTH
    L += ["THIS MONTH", hdr3,
          "AMT " + fAmt(ag.get("tgt_amt_sum"))      + fAmt(ag.get("amt_sum"))      + fPct(ag.get("diff_amt")) + fPct(ag.get("comp_amt")),
          "T/C " + fVal(ag.get("tgt_tc_sum"))        + fVal(ag.get("tc_sum"))       + fPct(ag.get("diff_tc"))  + fPct(ag.get("comp_tc")),
          "A/C " + fVal(ag.get("ac_tgt"))            + fVal(ag.get("ac_act"))       + fPct(ag.get("ac_diff"))  + fPct(ag.get("ac_comp")),
          "LBR%" + fVal(ag.get("lbr_tgt_avg"), True) + fVal(ag.get("lbr_act"),True) + fPct(ag.get("lbr_diff"))]

    output = "\n".join(L)
    print(output)
    return output


# ─── メイン ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="STX 営業管理表データ取得")
    parser.add_argument("--month", default=None, help="対象月 YYYY-MM（デフォルト: 当月）")
    parser.add_argument("--summary", action="store_true", help="DBのサマリー表示のみ（取得しない）")
    parser.add_argument("--store", default=None, help="店舗コード（デフォルト: 017807 GT保土ヶ谷駅前）")
    parser.add_argument("--all-stores", action="store_true", help="全店舗のサマリーを表示（--summary と併用）")
    args = parser.parse_args()

    year_month = args.month or date.today().strftime("%Y-%m")

    # 店舗設定の上書き
    global STORE_CODE, STORE_NAME
    if args.store:
        if args.store not in STORES:
            print(f"⚠ 未登録の店舗コード: {args.store}。登録済み: {list(STORES.keys())}", file=sys.stderr)
            sys.exit(1)
        STORE_CODE = args.store
        STORE_NAME = STORES[args.store]

    if args.summary:
        if args.all_stores:
            for code, name in STORES.items():
                STORE_CODE = code
                STORE_NAME = name
                print_summary(year_month)
                print()
        else:
            print_summary(year_month)
        return

    if not EMAIL or not PASSWORD:
        print("⚠ .env に SKYLARK_EMAIL / SKYLARK_GOOGLE_PASSWORD が設定されていません。")
        sys.exit(1)

    print(f"{'='*50}")
    print(f"STX 営業管理表取得: {year_month} / {STORE_NAME}")
    print(f"{'='*50}")

    with sync_playwright() as p:
        browser, context, page = get_authenticated_page(p)

        try:
            records = fetch_month_data(page, year_month)
        finally:
            browser.close()

    if records:
        saved = save_to_db(records)
        print(f"✓ DB 保存: {saved} 件（{DB_PATH}）")
        print()
        print_summary(year_month)
    else:
        print("⚠ データが取得できませんでした。")
        print("  → stx_login.py を実行して再ログインしてください。")
        sys.exit(1)


if __name__ == "__main__":
    main()
