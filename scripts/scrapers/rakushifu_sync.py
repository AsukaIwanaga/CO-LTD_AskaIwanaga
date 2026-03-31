#!/usr/bin/env python3
"""
rakushifu_sync.py — らくしふからシフトを取得し、キャッシュと差分比較する

使い方: python3 scripts/rakushifu_sync.py [--month YYYY-MM] [--headless]

出力:
  drafts/rakushifu_shifts_YYYY-MM.json   — 月別シフト（マージ済み）
  drafts/rakushifu_diff_YYYY-MM-DD.json  — 前回キャッシュとの差分（変更ありの場合のみ）
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

load_dotenv(dotenv_path=Path(__file__).parent / "../../.env")

import os

RAKUSHIFU_URL          = "https://accounts.rakushifu.com/skylark/staff/sign-in"
RAKUSHIFU_BASE_URL     = "https://skylark.enterprise.rakushifu.com"
RAKUSHIFU_SCHEDULE_URL = "https://skylark.enterprise.rakushifu.com/staff/schedules/confirmed"
RAKUSHIFU_CONFIRM_URL  = "https://skylark.enterprise.rakushifu.com/staff/v2/schedules/confirmed/me"

EMAIL    = os.getenv("SKYLARK_PERSONAL_ID", "")  # 従業員ID（例: 0000220415）
PASSWORD = os.getenv("SKYLARK_PASSWORD", "")

DRAFTS_DIR = (Path(__file__).parent / "../../drafts").resolve()
DRAFTS_DIR.mkdir(exist_ok=True)


# ─── ログイン ─────────────────────────────────────────────────────────────────

def login(page) -> bool:
    """らくしふにログインしてトップページに遷移する。"""
    print(f"[sync] ログイン中: {RAKUSHIFU_URL}")
    page.goto(RAKUSHIFU_URL)
    page.wait_for_load_state("networkidle")

    try:
        page.fill("input[name='employeeCode']", EMAIL, timeout=15000)
        page.fill("input[name='password']", PASSWORD, timeout=8000)
        page.click("button[type='submit']", timeout=5000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
    except Exception as e:
        print(f"[sync][ERROR] ログイン操作失敗: {e}", file=sys.stderr)
        return False

    if "sign-in" in page.url or "login" in page.url:
        print("[sync][ERROR] ログイン後もサインインページに留まっています。認証情報を確認してください。", file=sys.stderr)
        return False

    print(f"[sync] ログイン完了: {page.url}")
    return True


# ─── スクレイピング ───────────────────────────────────────────────────────────

MY_NAME_KEYWORD = os.getenv("SKYLARK_NAME", "岩永")  # 自分の名前（部分一致）

def scrape_month(page, year: int, month: int) -> list[dict]:
    """指定月のシフトを取得してリストで返す。

    ページ構造:
      tr.date-row > td : 日付ラベル（例: "16(月)"）
      tr.user-row > th : スタッフ名
      tr.user-row > td : 各日のシフトセル（.time-range-or-off に時刻）
    """
    url = f"{RAKUSHIFU_SCHEDULE_URL}?year={year}&month={month}"
    print(f"[sync] シフト取得中: {url}")
    page.goto(url)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    shifts: list[dict] = []
    trs = soup.select("tr")

    current_dates: list[str] = []

    for tr in trs:
        classes = tr.get("class") or []

        if "date-row" in classes:
            # 日付ヘッダー行: "16(月)" 形式のテキストを収集
            current_dates = []
            for td in tr.select("td"):
                txt = td.get_text(strip=True)
                if txt:
                    current_dates.append(txt)  # 例: "16(月)"
            continue

        if "user-row" in classes:
            th = tr.select_one("th")
            name = th.get_text(strip=True) if th else ""
            if MY_NAME_KEYWORD not in name:
                continue  # 自分以外はスキップ

            tds = tr.select("td")
            for i, td in enumerate(tds):
                if i >= len(current_dates):
                    break
                date_label = current_dates[i]  # 例: "16(月)"

                # 日付文字列: "3/16(月)"
                day_num = re.match(r"(\d+)", date_label)
                if not day_num:
                    continue
                date_str = f"{month}/{date_label}"

                time_els = td.select(".time-range-or-off")
                if not time_els:
                    # 公休/休み
                    off_el = td.select_one(".off-text, .holiday-text")
                    off_text = off_el.get_text(strip=True) if off_el else ""
                    shifts.append({
                        "date": date_str,
                        "time": off_text or "休み",
                        "store": "",
                        "breaks": [],
                        "memo": "",
                    })
                else:
                    for time_el in time_els:
                        time_text = time_el.get_text(strip=True)
                        # 店舗名（セル内の店舗ラベル）
                        store_el = time_el.find_previous_sibling() or time_el.parent
                        # ブラケット内の店舗名を抽出: 例「【キッチン】6:30-15:00」
                        m = re.match(r"【(.+?)】(.+)", time_text)
                        if m:
                            memo_text = m.group(1)
                            time_text  = m.group(2)
                        else:
                            memo_text = ""
                        shifts.append({
                            "date": date_str,
                            "time": time_text,
                            "store": "",
                            "breaks": [],
                            "memo": memo_text,
                        })

    return shifts


def merge_split_shifts(shifts: list[dict]) -> list[dict]:
    """同一日の分割シフトをひとつのエントリにマージする。"""
    from collections import defaultdict

    # 日付ごとにまとめる（順序保持）
    by_date: dict[str, list[dict]] = {}
    for s in shifts:
        key = s["date"]
        by_date.setdefault(key, [])
        by_date[key].append(s)

    merged = []
    for date, entries in by_date.items():
        # 休み
        if all(e["time"] == "休み" for e in entries):
            merged.append({"date": date, "time": "休み", "store": "", "breaks": [], "memo": ""})
            continue

        work_entries = [e for e in entries if e["time"] != "休み"]

        if len(work_entries) == 1:
            merged.append(work_entries[0])
            continue

        # 分割シフト → 開始〜終了を統合
        times = []
        stores = set()
        all_breaks = []
        memos = []
        for e in work_entries:
            if m := re.match(r"(\d{1,2}:\d{2})〜(\d{1,2}:\d{2})", e["time"]):
                times.append((m.group(1), m.group(2)))
            stores.add(e["store"])
            all_breaks.extend(e["breaks"])
            if e.get("memo"):
                memos.append(e["memo"])

        if times:
            start = min(t[0] for t in times)
            end   = max(t[1] for t in times)
            merged_time = f"{start}〜{end}"
        else:
            merged_time = work_entries[0]["time"]

        merged.append({
            "date": date,
            "time": merged_time,
            "store": " / ".join(sorted(stores)),
            "breaks": list(dict.fromkeys(all_breaks)),  # 重複除去
            "memo": " ".join(memos),
        })

    return merged


# ─── 未確認シフト確認済み処理 ────────────────────────────────────────────────

def confirm_all_shifts(page) -> bool:
    """未確認シフトを全て確認済みにする。

    /staff/v2/schedules/confirmed/me で「未確認シフトを全て確認済みにする」ボタンをクリック
    → ダイアログが出た場合は「確認済みに変更する」→「登録」をクリック。
    """
    print(f"[sync] 確定シフトページへ移動: {RAKUSHIFU_CONFIRM_URL}")
    page.goto(RAKUSHIFU_CONFIRM_URL)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # 「未確認シフトを全て確認済みにする」ボタンを探す
    btn = page.query_selector("button:has-text('未確認シフトを全て確認済みにする')")
    if not btn:
        print("[sync] 未確認シフトなし（ボタンが見つからない）")
        return True

    print("[sync] 「未確認シフトを全て確認済みにする」をクリック")
    btn.click()
    page.wait_for_timeout(2000)

    # 「確認済みに変更する」ボタン（モーダルや次画面）
    confirm_btn = page.query_selector("button:has-text('確認済みに変更する'):not(.is-disabled)")
    if confirm_btn:
        print("[sync] 「確認済みに変更する」をクリック")
        confirm_btn.click()
        page.wait_for_timeout(2000)

    # 「登録」ボタン
    register_btn = page.query_selector("button:has-text('登録')")
    if register_btn:
        print("[sync] 「登録」をクリック")
        register_btn.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

    print("[sync] 未確認シフトを確認済みにしました")
    return True


# ─── キャッシュ比較 ───────────────────────────────────────────────────────────

def _shift_key(s: dict) -> str:
    return f"{s['date']}|{s['time']}|{s['store']}"


def compare_shifts(old: list[dict], new: list[dict]) -> dict:
    """新旧シフトを比較して差分を返す。"""
    old_map = {_shift_key(s): s for s in old if s["time"] != "休み"}
    new_map = {_shift_key(s): s for s in new if s["time"] != "休み"}

    added   = [s for k, s in new_map.items() if k not in old_map]
    removed = [s for k, s in old_map.items() if k not in new_map]

    # 日付は同じだが時刻や店舗が変わったもの
    old_by_date = {s["date"]: s for s in old if s["time"] != "休み"}
    new_by_date = {s["date"]: s for s in new if s["time"] != "休み"}
    modified = []
    for date, new_s in new_by_date.items():
        if date in old_by_date:
            old_s = old_by_date[date]
            if old_s["time"] != new_s["time"] or old_s["store"] != new_s["store"]:
                modified.append({"before": old_s, "after": new_s})

    return {"added": added, "removed": removed, "modified": modified}


# ─── メイン ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="らくしふシフト同期")
    parser.add_argument("--month", help="取得対象月 (YYYY-MM形式)。省略時は今月+来月")
    parser.add_argument("--headless", action="store_true", default=True, help="ヘッドレスモード（デフォルトON）")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="ブラウザ表示モード")
    parser.add_argument("--confirm-shifts", action="store_true", help="未確認シフトを全て確認済みにする")
    args = parser.parse_args()

    now = datetime.now()

    if args.month:
        try:
            target_dt = datetime.strptime(args.month, "%Y-%m")
            months = [(target_dt.year, target_dt.month)]
        except ValueError:
            print(f"[sync][ERROR] --month の形式が不正です（YYYY-MM）: {args.month}", file=sys.stderr)
            sys.exit(1)
    else:
        # 今月 + 来月
        next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        months = [(now.year, now.month), (next_month.year, next_month.month)]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        ctx = browser.new_context()
        page = ctx.new_page()

        if not login(page):
            browser.close()
            sys.exit(1)

        # 未確認シフトを確認済みにする（--confirm-shifts 指定時）
        if args.confirm_shifts:
            confirm_all_shifts(page)

        all_changes: list[dict] = []

        for year, month in months:
            shifts_raw  = scrape_month(page, year, month)
            shifts_new  = merge_split_shifts(shifts_raw)

            month_key   = f"{year}-{month:02d}"
            cache_path  = DRAFTS_DIR / f"rakushifu_shifts_{month_key}.json"

            # キャッシュ読み込み
            shifts_old: list[dict] = []
            if cache_path.exists():
                try:
                    shifts_old = json.loads(cache_path.read_text(encoding="utf-8"))
                except Exception:
                    pass

            # 新データ保存
            cache_path.write_text(
                json.dumps(shifts_new, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"[sync] 保存: {cache_path}  ({len(shifts_new)} 件)")

            # 差分チェック（キャッシュがある場合のみ）
            if shifts_old:
                diff = compare_shifts(shifts_old, shifts_new)
                has_change = any([diff["added"], diff["removed"], diff["modified"]])
                if has_change:
                    diff["month"] = month_key
                    all_changes.append(diff)
                    print(f"[sync] 変更検出: 追加 {len(diff['added'])} / 削除 {len(diff['removed'])} / 変更 {len(diff['modified'])}")
                else:
                    print(f"[sync] 変更なし: {month_key}")
            else:
                print(f"[sync] 初回取得のためキャッシュ比較スキップ: {month_key}")

        browser.close()

    # 差分レポート保存
    if all_changes:
        diff_path = DRAFTS_DIR / f"rakushifu_diff_{now.strftime('%Y-%m-%d')}.json"
        diff_path.write_text(
            json.dumps(all_changes, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"[sync] 差分レポート保存: {diff_path}")
        print("[sync] ⚠️  シフト変更があります。朝のブリーフィングで確認してください。")
    else:
        print("[sync] シフト変更はありませんでした。")


if __name__ == "__main__":
    main()
