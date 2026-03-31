#!/usr/bin/env python3
"""
area_events.py — GT保土ヶ谷駅前周辺のイベント・店舗影響予測を取得する

使い方:
  python3 scripts/area_events.py              # テキスト出力（テンプレート形式）
  python3 scripts/area_events.py --format json # JSON 出力
  python3 scripts/area_events.py --days 3      # 本日+3日先まで表示（デフォルト: 2）

出力フォーマット:
  店舗周辺イベント
        DATE     PLACE             GUEST_AMT      START ~ END      EFFORT
                                                                   HH:mm    NUMBER
  TODAY  MM-dd   YOKOHAMA_ARENA    ###,###        HH:mm - HH:mm    HH:mm   ###
  FUTURE MM-dd   NISSAN_STADIUM    ###,###        HH:mm - HH:mm    HH:mm   ###

取得対象:
  1. 横浜アリーナ     enjoy-live.net (hall_id=1)    ← キャパ 17,000
  2. 日産スタジアム   enjoy-live.net (hall_id=27)   ← キャパ 72,000
  3. 横浜スタジアム   enjoy-live.net (hall_id=28)   ← キャパ 35,000
  4. 特殊イベント     DuckDuckGo 検索 + 新横浜・保土ヶ谷周辺情報 + 横浜観光情報
  5. 交通・気象影響   JMA 気象警報 + Yahoo!路線情報

EFFORT (NUMBER) = 想定来場者数 × 会場別影響係数
  影響係数はコンサート終了後に周辺飲食店を利用する割合の推定値。
  sales/event_impact.json に実績データが蓄積されると自動更新。
"""

import argparse
import html
import json
import re
import sys
import urllib.request
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path

TODAY = date.today()
TODAY_STR = TODAY.strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# 会場設定
# ---------------------------------------------------------------------------

VENUE_CONFIG = {
    "YOKOHAMA_ARENA": {
        "name_jp": "横浜アリーナ",
        "hall_id": 1,
        "capacity": 17000,
        # 保土ヶ谷駅前との関係: 新横浜から相鉄線で1駅。夜公演後に来店しやすい
        "impact_rate_evening":   0.006,
        "impact_rate_afternoon": -0.003,  # 昼公演は帰宅ルートが変わり来店減リスク
        "default_open":  "17:00",
        "default_start": "18:00",
        "default_end":   "21:00",
    },
    "NISSAN_STADIUM": {
        "name_jp": "日産スタジアム",
        "hall_id": 27,
        "capacity": 72000,
        # 新横浜駅隣接。大規模イベント時は駅周辺が混雑し保土ヶ谷にも波及
        "impact_rate_evening":   0.003,
        "impact_rate_afternoon": 0.001,
        "default_open":  "16:00",
        "default_start": "17:00",
        "default_end":   "20:00",
    },
    "YOKOHAMA_STADIUM": {
        "name_jp": "横浜スタジアム",
        "hall_id": 28,
        "capacity": 35000,
        # 関内駅。横須賀線で保土ヶ谷まで5駅。試合後帰宅ルートに乗る層が来店
        "impact_rate_evening":   0.004,
        "impact_rate_afternoon": 0.001,
        "default_open":  "17:00",
        "default_start": "18:00",
        "default_end":   "21:00",
    },
}

# 開演時刻がこの時間以前ならafternoon判定
AFTERNOON_CUTOFF_HOUR = 16

# ジャンル定義: (キーワードリスト, genre_id, 稼働率, 影響係数乗数)
# 影響係数乗数: ジャンルごとに飲食店来訪傾向が異なる
# ※ 先頭から順にマッチ判定 — より具体的なキーワードを上に配置
GENRE_MAP = [
    # イベント形式（コンサートより優先度高い修飾子）
    (["握手", "ハイタッチ", "お見送り", "ファンミ", "ファンミーティング"],
     "fanmeet",      0.70, 0.6),
    (["卒業", "卒コン", "ファイナル", "FINAL", "LAST", "解散"],
     "graduation",   0.98, 1.3),
    (["D.U.N.K", "ダンス", "DANCE", "HIP HOP", "ヒップホップ"],
     "dance",        0.80, 0.7),   # 実績: D.U.N.K.で+2.8pp
    (["フェス", "FES", "FESTIVAL", "大作戦"],
     "festival",     0.85, 1.0),
    (["古舘", "トークショー", "トーキング", "お笑い", "落語", "講演"],
     "talk_comedy",  0.65, 0.4),
    (["スポーツ", "試合", "バスケ", "バレー", "ボクシング"],
     "sports",       0.80, 0.5),
    # アーティスト／ジャンル
    (["乃木坂", "AKB", "SKE", "HKT", "NMB", "日向坂", "STU", "≒JOY"],
     "female_idol",  0.90, 1.5),   # 実績: 乃木坂46で+17pp
    (["STPR", "ジャニーズ", "SixTONES", "Snow Man", "なにわ", "関ジャニ", "Hey! Say!", "Travis Japan"],
     "male_idol",    0.92, 1.2),
    (["SUPER BEAVER", "BanG Dream", "MyGO", "Ave Mujica", "バンド", "BAND", "ロック", "ROCK"],
     "band_rock",    0.88, 1.0),
    (["アニメ", "声優", "ゲーム", "vtuber", "VTuber", "ホロライブ", "にじさんじ"],
     "anime_seiyuu", 0.85, 0.9),
]
DEFAULT_GENRE    = ("other", 0.80, 1.0)


def classify_event(event_name: str) -> tuple[str, float, float]:
    """イベント名からジャンル・稼働率・影響係数乗数を返す。"""
    for keywords, genre_id, fill, multiplier in GENRE_MAP:
        if any(kw in event_name for kw in keywords):
            return genre_id, fill, multiplier
    return DEFAULT_GENRE

# 天気補正係数: 降水確率・降水量 → 来客率への影響
# 実績ベース（雨天日の来客減傾向より推定）
WEATHER_FACTOR_MAP = [
    (0,   10,  1.00),   # 快晴〜ほぼ晴れ: 補正なし
    (10,  30,  0.97),   # 少し雨リスク: -3%
    (30,  60,  0.90),   # 傘が必要: -10%
    (60,  80,  0.82),   # 雨の可能性高い: -18%
    (80,  101, 0.72),   # ほぼ確実に雨: -28%
]

def get_weather_factor(target: date) -> tuple[float, str]:
    """
    Open-Meteo から対象日の降水確率を取得し、天気補正係数と説明を返す。
    戻り値: (factor: float, label: str)
    """
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=35.4539&longitude=139.5979"
        "&daily=precipitation_probability_max,weathercode"
        "&timezone=Asia%2FTokyo&forecast_days=7"
    )
    text = fetch(url, timeout=8)
    if not text:
        return 1.0, "取得失敗"
    try:
        data = json.loads(text)
        dates = data["daily"]["time"]
        probs = data["daily"]["precipitation_probability_max"]
        target_str = target.isoformat()
        if target_str in dates:
            idx = dates.index(target_str)
            prob = probs[idx] or 0
            for lo, hi, factor in WEATHER_FACTOR_MAP:
                if lo <= prob < hi:
                    label = f"降水確率{prob}%"
                    return factor, label
    except Exception:
        pass
    return 1.0, "不明"


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def fetch(url: str, timeout: int = 10) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            charset = r.headers.get_content_charset() or "utf-8"
            return r.read().decode(charset, errors="replace")
    except Exception as e:
        print(f"[WARN] fetch failed: {url} — {e}", file=sys.stderr)
        return ""


def strip_tags(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def estimate_fill_rate(event_name: str) -> float:
    _, fill, _ = classify_event(event_name)
    return fill


def load_impact_history() -> dict:
    """過去のイベント実績データ（蓄積型）を読み込む。"""
    path = Path(__file__).parent.parent.parent / "sales" / "event_impact.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {"venue_impact_rates": {}, "events": []}


def get_impact_rate(venue_key: str, start_time: str, event_name: str = "") -> float:
    """
    実績データ × セッション(午前/夜) × ジャンル乗数 で影響係数を返す。
    午後公演（開演 < AFTERNOON_CUTOFF_HOUR）はマイナス係数を返す場合あり。
    """
    history = load_impact_history()
    overrides = history.get("venue_impact_rates", {})

    session = "afternoon"
    if start_time:
        try:
            hour = int(start_time.split(":")[0])
            if hour >= AFTERNOON_CUTOFF_HOUR:
                session = "evening"
        except ValueError:
            session = "evening"
    else:
        session = "evening"

    if venue_key in overrides and isinstance(overrides[venue_key], dict):
        base = overrides[venue_key].get(session, overrides[venue_key].get("evening", 0.005))
    else:
        cfg = VENUE_CONFIG[venue_key]
        base = cfg.get(f"impact_rate_{session}", cfg.get("impact_rate_evening", 0.005))

    # ジャンル乗数を適用（午後マイナスには掛けない）
    if event_name and base > 0:
        _, _, genre_multiplier = classify_event(event_name)
        return base * genre_multiplier
    return base


# ---------------------------------------------------------------------------
# イベント時刻検索（DuckDuckGo）
# ---------------------------------------------------------------------------

def _extract_times(text: str) -> tuple[str, str]:
    """テキストから開演・終演時刻を正規表現で抽出する。"""
    start_m = re.search(
        r'(?:開演|START|スタート|開始)[^\d]*(\d{1,2})[：:時](\d{2})', text)
    end_m   = re.search(
        r'(?:終演|END|終了|閉演)[^\d]*(\d{1,2})[：:時](\d{2})', text)
    start = f"{int(start_m.group(1)):02d}:{start_m.group(2)}" if start_m else ""
    end   = f"{int(end_m.group(1)):02d}:{end_m.group(2)}"   if end_m   else ""
    return start, end


def _ddg_search(query: str) -> str:
    """DuckDuckGo HTML 検索結果のスニペットを結合して返す。"""
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    text = fetch(url, timeout=8)
    if not text:
        return ""
    snippets = re.findall(
        r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', text,
        re.DOTALL | re.IGNORECASE
    )
    return " ".join(strip_tags(s) for s in snippets[:5])


def _pw_get_event_time(page, search_url: str, detail_selector: str,
                       base_url: str, event_name: str) -> tuple[str, str]:
    """Playwright ページで検索 → 詳細ページへ遷移 → 時刻抽出の共通処理。"""
    page.goto(search_url, timeout=20000, wait_until="networkidle")
    links = page.query_selector_all(detail_selector)
    detail_url = None
    kws = [w for w in event_name.split() if len(w) > 1][:3]
    for lnk in links[:10]:
        title = re.sub(r"\s+", " ", lnk.inner_text()).strip()
        if any(kw in title for kw in kws):
            detail_url = lnk.get_attribute("href")
            break
    if not detail_url and links:
        detail_url = links[0].get_attribute("href")
    if not detail_url:
        return "", ""
    if not detail_url.startswith("http"):
        detail_url = base_url + detail_url
    page.goto(detail_url, timeout=20000, wait_until="networkidle")
    return _extract_times(page.inner_text("body"))


def _playwright_search_time(event_name: str, target: date) -> tuple[str, str]:
    """
    Playwright (Chromium) で eplus.jp → t.pia.jp の順に検索し、
    JS レンダリング後の時刻情報を取得する。
    Playwright が使えない環境ではサイレントに ("", "") を返す。
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "", ""

    kw = urllib.parse.quote(event_name)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(locale="ja-JP")

            # --- eplus.jp ---
            page = ctx.new_page()
            start, end = _pw_get_event_time(
                page,
                search_url     = f"https://eplus.jp/sf/search?keyword={kw}",
                detail_selector= "a[href*='/sf/detail']",
                base_url       = "https://eplus.jp",
                event_name     = event_name,
            )
            if start:
                browser.close()
                return start, end

            # --- t.pia.jp ---
            page2 = ctx.new_page()
            start, end = _pw_get_event_time(
                page2,
                search_url     = f"https://t.pia.jp/pia/search_all.do?kw={kw}",
                detail_selector= "a[href*='/pia/event.do']",
                base_url       = "https://ticket.pia.jp",
                event_name     = event_name,
            )
            browser.close()
            return start, end
    except Exception:
        return "", ""


def search_event_time(event_name: str, target: date) -> tuple[str, str]:
    """
    イベント名で開演・終演時刻を検索する。
    戻り値: (start_time "HH:MM", end_time "HH:MM") — 不明なら ("", "")

    fallback 順序:
      1. DuckDuckGo 一般検索
      2. DuckDuckGo + site:eplus.jp
      3. DuckDuckGo + site:t.pia.jp
      4. Playwright (Chromium) で eplus.jp を直接取得
    """
    date_str = f"{target.year}年{target.month}月{target.day}日"

    # 1. 一般検索
    combined = _ddg_search(f"{event_name} {date_str} 開演 終演 時間")
    start, end = _extract_times(combined)
    if start:
        return start, end

    # 2. e+ 検索
    combined = _ddg_search(f"site:eplus.jp {event_name} {date_str} 開演")
    start, end = _extract_times(combined)
    if start:
        return start, end

    # 3. チケットぴあ検索
    combined = _ddg_search(f"site:t.pia.jp {event_name} {date_str} 開演")
    start, end = _extract_times(combined)
    if start:
        return start, end

    # 4. Playwright で eplus.jp を直接取得（JS レンダリング対応）
    return _playwright_search_time(event_name, target)


def calc_effort_window(start: str, end: str, cfg: dict) -> tuple[str, str]:
    """
    影響時間帯: 開場1時間前 〜 終演2時間後。
    戻り値: (impact_start "HH:MM", impact_end "HH:MM")
    """
    def parse(t: str) -> int:
        if not t:
            return -1
        h, m = t.split(":")
        return int(h) * 60 + int(m)

    def fmt(minutes: int) -> str:
        h, m = divmod(minutes, 60)
        return f"{h % 24:02d}:{m:02d}"

    open_t  = parse(cfg["default_open"])
    start_t = parse(start) if start else parse(cfg["default_start"])
    end_t   = parse(end)   if end   else parse(cfg["default_end"])

    impact_start = min(open_t, start_t) - 60   # 開場1時間前
    impact_end   = end_t + 120                  # 終演2時間後
    return fmt(impact_start), fmt(impact_end)


# ---------------------------------------------------------------------------
# enjoy-live.net 共通パーサー
# ---------------------------------------------------------------------------

def fetch_enjoy_live_events(hall_id: int, targets: list[date]) -> dict[str, list[dict]]:
    """
    enjoy-live.net から指定日リストのイベントを取得する。
    戻り値: {date_str: [{"name": ..., "artist_id": ...}]}
    """
    url = f"https://schedule.enjoy-live.net/schedule.php?hall_id={hall_id}"
    html_text = fetch(url)
    if not html_text:
        return {}

    results: dict[str, list[dict]] = {}

    sections = re.split(r'<h2[^>]*>', html_text, flags=re.IGNORECASE)
    for section in sections:
        # このセクションの年月を特定
        year_month_m = re.match(r'(\d{4})年(\d{1,2})月', section)
        if not year_month_m:
            continue
        sec_year  = int(year_month_m.group(1))
        sec_month = int(year_month_m.group(2))

        for target in targets:
            if target.year != sec_year or target.month != sec_month:
                continue

            day_patterns = [f"{target.day}日(", f"{target.day}日 ("]
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', section, re.DOTALL | re.IGNORECASE)
            for row in rows:
                text = strip_tags(row)
                if not any(p in text for p in day_patterns):
                    continue
                artist_link = re.search(
                    r'<a[^>]+href="[^"]*artist\.php\?artist_id=([^"&]+)"[^>]*>(.*?)</a>',
                    row, re.DOTALL | re.IGNORECASE
                )
                if not artist_link:
                    continue
                artist_id = artist_link.group(1)
                td_m = re.search(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                name = strip_tags(td_m.group(1))[:80] if td_m else strip_tags(artist_link.group(2))[:80]
                date_str = target.isoformat()
                results.setdefault(date_str, []).append({
                    "name": name,
                    "artist_id": artist_id,
                })

    return results


def get_artist_capacity(artist_id: str, hall_id: int) -> int | None:
    """enjoy-live.net artist ページから会場キャパを取得する。"""
    url = f"https://schedule.enjoy-live.net/artist.php?artist_id={artist_id}"
    text = fetch(url)
    if not text:
        return None
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', text, re.DOTALL | re.IGNORECASE)
    for row in rows:
        t = strip_tags(row)
        # 会場名に対応するキャパ数値を探す（hall_id で逆引きは難しいので数値だけ）
        nums = re.findall(r'\b(\d{3,6})\b', t)
        if nums:
            cap = int(nums[-1])
            if 500 <= cap <= 100000:
                return cap
    return None


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# メイン処理: イベント情報 + 影響予測
# ---------------------------------------------------------------------------

def build_venue_events(targets: list[date]) -> list[dict]:
    """
    各会場の日程別イベントを取得し、影響予測を付加して返す。
    """
    venue_keys = list(VENUE_CONFIG.keys())

    # 日別天気補正係数を事前取得
    weather_factors: dict[str, tuple[float, str]] = {}
    for t in targets:
        weather_factors[t.isoformat()] = get_weather_factor(t)

    # enjoy-live データを一括取得
    enjoy_data: dict[str, dict[str, list[dict]]] = {}
    for vk in venue_keys:
        cfg = VENUE_CONFIG[vk]
        enjoy_data[vk] = fetch_enjoy_live_events(cfg["hall_id"], targets)

    rows = []
    for target in targets:
        date_str = target.isoformat()
        for vk in venue_keys:
            cfg = VENUE_CONFIG[vk]

            # イベント取得
            events = enjoy_data.get(vk, {}).get(date_str, [])

            if not events:
                rows.append({
                    "date": date_str,
                    "venue_key": vk,
                    "venue_name": cfg["name_jp"],
                    "has_event": False,
                    "event_name": "",
                    "guest_amt": None,
                    "start": "",
                    "end": "",
                    "effort_start": "",
                    "effort_number": None,
                })
                continue

            ev = events[0]
            name = ev["name"]

            # キャパ・稼働率 → 想定来場者数
            cap = cfg["capacity"]
            if ev.get("artist_id"):
                fetched_cap = get_artist_capacity(ev["artist_id"], cfg["hall_id"])
                if fetched_cap:
                    cap = fetched_cap
            fill = estimate_fill_rate(name)
            guest_amt = int(cap * fill)

            # 開演・終演時刻
            start, end = search_event_time(name, target)
            if not start:
                start = cfg["default_start"]
            if not end:
                end   = cfg["default_end"]

            # 影響時間帯・来客数予測（天気補正あり）
            effort_start, _ = calc_effort_window(start, end, cfg)
            genre_id, _, _ = classify_event(name)
            impact_rate   = get_impact_rate(vk, start, name)
            weather_factor, weather_label = weather_factors.get(date_str, (1.0, ""))
            effort_number = int(guest_amt * impact_rate * weather_factor)

            rows.append({
                "date": date_str,
                "venue_key": vk,
                "venue_name": cfg["name_jp"],
                "has_event": True,
                "event_name": name,
                "guest_amt": guest_amt,
                "start": start,
                "end": end,
                "effort_start": effort_start,
                "effort_number": effort_number,
                "genre": genre_id,
                "afternoon_risk": impact_rate < 0,
                "weather_factor": weather_factor,
                "weather_label": weather_label,
            })
    return rows


# ---------------------------------------------------------------------------
# 複数会場同日集計
# ---------------------------------------------------------------------------

# 同日同セッション（夕方）複数会場の重複補正係数
# 「複数会場がある日は来客が分散するため、単純合算より少なくなる」を表現
# n=2会場: 0.85, n=3会場: 0.75（実績データが増えたら調整）
MULTI_VENUE_OVERLAP_FACTOR = {1: 1.00, 2: 0.85, 3: 0.75}


def calc_multiday_totals(venue_rows: list[dict]) -> dict[str, dict]:
    """
    同日の全会場 effort_number を合算し、日付別のサマリーを返す。

    返り値: {
        "YYYY-MM-DD": {
            "total_guests":  int,   # 全会場合計来場者数（稼働率考慮）
            "total_effort":  int,   # 重複補正後の想定来客増加数
            "event_count":   int,   # イベントあり会場数
            "has_afternoon": bool,  # 午後公演（来客減リスク）があるか
        }
    }
    """
    from collections import defaultdict
    day_data: dict[str, list[dict]] = defaultdict(list)
    for row in venue_rows:
        if row["has_event"]:
            day_data[row["date"]].append(row)

    result = {}
    for date_str, rows in day_data.items():
        total_guests = sum(r["guest_amt"] for r in rows if r.get("guest_amt"))
        # 午後公演（マイナス係数）は合算から除外してリスク警告として記録
        positive_rows  = [r for r in rows if not r.get("afternoon_risk")]
        afternoon_rows = [r for r in rows if r.get("afternoon_risk")]
        n = len(positive_rows)
        overlap = MULTI_VENUE_OVERLAP_FACTOR.get(n, 0.70)
        raw_effort = sum(r.get("effort_number", 0) for r in positive_rows)
        total_effort = int(raw_effort * overlap)
        # 午後分は減算
        afternoon_penalty = sum(abs(r.get("effort_number", 0)) for r in afternoon_rows)

        result[date_str] = {
            "total_guests":     total_guests,
            "total_effort":     total_effort - afternoon_penalty,
            "raw_effort":       raw_effort,
            "overlap_factor":   overlap,
            "event_count":      len(rows),
            "has_afternoon":    len(afternoon_rows) > 0,
        }
    return result


# ---------------------------------------------------------------------------
# 特殊イベント / 気象 / 交通
# ---------------------------------------------------------------------------

def fetch_shinyokohama_events(target: date) -> list[dict]:
    """新横浜・保土ヶ谷周辺のイベントをDuckDuckGo検索で取得する。"""
    try:
        query = (
            f"新横浜 保土ヶ谷 横浜アリーナ 日産スタジアム イベント "
            f"{target.year}年{target.month}月{target.day}日"
        )
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        text = fetch(url)
        if not text:
            return []

        snippets = re.findall(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', text, re.DOTALL | re.IGNORECASE)
        titles   = re.findall(r'<a[^>]+class="result__a"[^>]*>(.*?)</a>',       text, re.DOTALL | re.IGNORECASE)

        results, seen = [], set()
        for title, snippet in zip(titles[:8], snippets[:8]):
            t = strip_tags(title)[:50]
            s = strip_tags(snippet)[:100]
            key = t[:20]
            if key in seen:
                continue
            seen.add(key)
            results.append({"title": t, "snippet": s, "source": "shinyokohama"})
            if len(results) >= 5:
                break
        return results
    except Exception:
        return []


def fetch_yokohama_kanko_events(target: date) -> list[dict]:
    """横浜観光情報 (yokohamajapan.com) を DuckDuckGo サイト限定検索で取得する。"""
    try:
        query = (
            f"新横浜 保土ヶ谷 イベント {target.year}年{target.month}月{target.day}日"
            " site:yokohamajapan.com"
        )
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        text = fetch(url)
        if not text:
            return []

        snippets = re.findall(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', text, re.DOTALL | re.IGNORECASE)
        titles   = re.findall(r'<a[^>]+class="result__a"[^>]*>(.*?)</a>',       text, re.DOTALL | re.IGNORECASE)

        results, seen = [], set()
        for title, snippet in zip(titles[:8], snippets[:8]):
            t = strip_tags(title)[:50]
            s = strip_tags(snippet)[:100]
            key = t[:20]
            if key in seen:
                continue
            seen.add(key)
            results.append({"title": t, "snippet": s, "source": "yokohama-kanko"})
            if len(results) >= 5:
                break
        return results
    except Exception:
        return []


def fetch_special_events(target: date) -> list[dict]:
    # --- ソース1: DuckDuckGo 汎用検索 ---
    query = (
        f"新横浜 保土ヶ谷 横浜 イベント {target.year}年{target.month}月{target.day}日 "
        "OR 花火 OR フェス OR コンサート OR ライブ OR マラソン OR 野球"
    )
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    text = fetch(url)
    ddg_results = []
    if text:
        snippets = re.findall(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', text, re.DOTALL | re.IGNORECASE)
        titles   = re.findall(r'<a[^>]+class="result__a"[^>]*>(.*?)</a>',       text, re.DOTALL | re.IGNORECASE)
        for title, snippet in zip(titles[:8], snippets[:8]):
            t = strip_tags(title)[:50]
            s = strip_tags(snippet)[:100]
            if any(kw in (t + s) for kw in ["新横浜", "保土ヶ谷", "横浜アリーナ", "日産スタジアム", "横浜スタジアム", "横浜"]):
                ddg_results.append({"title": t, "snippet": s, "source": "ddg"})

    # --- ソース2: 新横浜・保土ヶ谷周辺情報 ---
    mm21_results = fetch_shinyokohama_events(target)

    # --- ソース3: 横浜観光情報 ---
    kanko_results = fetch_yokohama_kanko_events(target)

    # --- マージ・重複除外（タイトル先頭20文字）・最大10件 ---
    results, seen = [], set()
    for item in ddg_results + mm21_results + kanko_results:
        key = item["title"][:20]
        if key in seen:
            continue
        seen.add(key)
        results.append(item)
        if len(results) >= 10:
            break
    return results


def fetch_weather_alert() -> list[str]:
    url = "https://www.jma.go.jp/bosai/warning/data/warning/140000.json"
    text = fetch(url)
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    alerts = []
    for area in data.get("areaTypes", []):
        for a in area.get("areas", []):
            name = a.get("name", "")
            for warn in a.get("warnings", []):
                status    = warn.get("status", "")
                kind_name = warn.get("kind", {}).get("name", "")
                if status in ("発表", "継続") and kind_name:
                    alerts.append(f"{name}: {kind_name}（{status}）")
    return alerts


def fetch_train_disruption() -> list[str]:
    url = "https://transit.yahoo.co.jp/traininfo/area/4/"
    text = fetch(url, timeout=10)
    if not text:
        return []

    target_lines = ["相鉄本線", "JR横須賀線", "JR東海道線", "JR横浜線", "東急東横線"]
    disruptions  = []
    found_lines  = set()

    for block in re.findall(r'<li[^>]*>.*?</li>', text, re.DOTALL | re.IGNORECASE):
        t = strip_tags(block)
        for line in target_lines:
            if line in t and line not in found_lines:
                found_lines.add(line)
                if "平常通り" not in t and ("遅延" in t or "見合わせ" in t or "運休" in t):
                    disruptions.append(f"{line}: {re.sub(r' +', ' ', t).strip()[:100]}")
                break
    return disruptions


# ---------------------------------------------------------------------------
# テキスト出力（テンプレート形式）
# ---------------------------------------------------------------------------

def format_text(targets: list[date], venue_rows: list[dict],
                special_events: list[dict],
                weather_alerts: list[str], train_disruptions: list[str]) -> str:
    lines = []
    lines.append("店舗周辺イベント")
    lines.append(f"      DATE     PLACE             GUEST_AMT      START ~ END      EFFORT")
    lines.append(f"                                                                 HH:mm    NUMBER")
    lines.append("-" * 80)

    today_str = TODAY.isoformat()
    prev_date = ""
    day_totals = calc_multiday_totals(venue_rows)

    for row in venue_rows:
        is_today   = row["date"] == today_str
        dt         = date.fromisoformat(row["date"])
        date_label = dt.strftime("%m-%d")

        # prefix / date 列 — 同一日付の2・3行目は空白
        if date_label != prev_date:
            pref = f"{'TODAY' if is_today else 'FUTURE':<6}"
            dstr = f"{date_label:<5}"
            prev_date = date_label
        else:
            pref = " " * 6
            dstr = " " * 5

        venue_col = f"{row['venue_key']:<17}"

        if row["has_event"]:
            wf = row.get("weather_factor", 1.0)
            wlabel = f" [{row.get('weather_label','')}]" if wf < 1.0 else ""
            guest    = f"{row['guest_amt']:>11,}"
            time_col = f"{row['start']} - {row['end']}" if row["start"] else "  ?   -  ?   "
            eff_t    = row["effort_start"] if row["effort_start"] else "  ?  "
            if row.get("afternoon_risk"):
                eff_n = f"{'⚠来客減':>7}"
            else:
                eff_n = f"{row['effort_number']:>7,}{wlabel}"
        else:
            guest    = f"{'  -':>11}"
            time_col = "       -        "
            eff_t    = "  -  "
            eff_n    = "      -"

        lines.append(f"{pref} {dstr}  {venue_col} {guest}    {time_col:<17}  {eff_t}  {eff_n}")

    # 複数会場がある日は合算サマリー行を出力
    for target in targets:
        date_str = target.isoformat()
        summary  = day_totals.get(date_str)
        if not summary or summary["event_count"] < 2:
            continue
        is_today   = date_str == today_str
        dt         = date.fromisoformat(date_str)
        date_label = dt.strftime("%m-%d")
        pref       = f"{'TODAY' if is_today else 'FUTURE':<6}"
        n          = summary["event_count"]
        ov         = summary["overlap_factor"]
        total      = summary["total_effort"]
        warn       = " ⚠午後来客減含む" if summary["has_afternoon"] else ""
        overlap_note = f"(×{ov:.2f} 重複補正, {n}会場合算)" if ov < 1.0 else f"({n}会場合算)"
        lines.append(
            f"{'':6} {date_label}  {'MULTI-VENUE TOTAL':<17} {'':>11}    {'':17}  {'':5}  {total:>7,}  {overlap_note}{warn}"
        )

    if special_events:
        lines.append("")
        lines.append("その他イベント（DuckDuckGo）")
        for ev in special_events:
            lines.append(f"  - {ev['title']}")
            if ev.get("snippet"):
                lines.append(f"    {ev['snippet']}")

    lines.append("")
    lines.append("交通・気象影響")
    lines.append("-" * 80)
    if weather_alerts:
        for a in weather_alerts:
            lines.append(f"  ⚠ 気象警報: {a}")
    if train_disruptions:
        for d in train_disruptions:
            lines.append(f"  ⚠ 運行情報: {d}")
    if not weather_alerts and not train_disruptions:
        lines.append("  特になし")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="GT保土ヶ谷駅前周辺イベント・影響予測")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    parser.add_argument("--date",   default=TODAY_STR, help="基準日 YYYY-MM-DD")
    parser.add_argument("--days",   type=int, default=2, help="本日+N日先まで表示")
    args = parser.parse_args()

    base   = date.fromisoformat(args.date)
    targets = [base + timedelta(days=i) for i in range(args.days)]

    print(f"[INFO] {base} 〜 {targets[-1]} のイベント情報を取得中...", file=sys.stderr)

    venue_rows     = build_venue_events(targets)
    special_events = fetch_special_events(base)
    weather_alerts = fetch_weather_alert()
    train_dis      = fetch_train_disruption()

    if args.format == "json":
        day_totals = calc_multiday_totals(venue_rows)
        print(json.dumps({
            "date": str(base),
            "venue_events": venue_rows,
            "day_totals": day_totals,
            "special_events": special_events,
            "weather_alerts": weather_alerts,
            "train_disruptions": train_dis,
        }, ensure_ascii=False, indent=2))
        return

    print(format_text(targets, venue_rows, special_events, weather_alerts, train_dis))


if __name__ == "__main__":
    main()
