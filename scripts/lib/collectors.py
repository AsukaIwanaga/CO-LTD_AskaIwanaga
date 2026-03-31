"""外部データ収集 — API 直接呼出 + 既存スクリプト subprocess 実行"""

import json
import subprocess
import urllib.request
from datetime import date
from .config import PYTHON, SCRIPTS_DIR, DRAFTS_DIR


# ─── 外部 API ────────────────────────────────────────────────────────────

def fetch_weather() -> dict:
    """Open-Meteo API（横浜 / 保土ヶ谷）"""
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        "latitude=35.4437&longitude=139.6380"
        "&current=temperature_2m,weathercode,windspeed_10m"
        "&daily=temperature_2m_max,temperature_2m_min,weathercode,precipitation_probability_max"
        "&timezone=Asia%2FTokyo&forecast_days=1"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def fetch_stocks() -> dict:
    """Yahoo Finance v8 API — 主要指数 + 為替"""
    tickers = {
        "nikkei": "^N225", "dow": "^DJI", "nasdaq": "^IXIC",
        "sp500": "^GSPC", "skylark": "3197.T",
        "usdjpy": "USDJPY=X", "twdjpy": "TWDJPY=X",
    }
    results = {}
    for name, ticker in tickers.items():
        try:
            # DoD (1日)
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            chart = data["chart"]["result"][0]
            meta = chart["meta"]
            now = meta.get("regularMarketPrice", 0)
            prev_close = meta.get("previousClose", meta.get("chartPreviousClose", 0))
            dod = now - prev_close if prev_close else 0

            # WoW (5日)
            url_w = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=5d&interval=1d"
            req_w = urllib.request.Request(url_w, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_w, timeout=10) as resp_w:
                data_w = json.loads(resp_w.read())
            closes_w = data_w["chart"]["result"][0]["indicators"]["quote"][0].get("close", [])
            closes_w = [c for c in closes_w if c is not None]
            wow = now - closes_w[0] if closes_w else 0

            # YoY (1年)
            url_y = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1mo"
            req_y = urllib.request.Request(url_y, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_y, timeout=10) as resp_y:
                data_y = json.loads(resp_y.read())
            closes_y = data_y["chart"]["result"][0]["indicators"]["quote"][0].get("close", [])
            closes_y = [c for c in closes_y if c is not None]
            yoy = now - closes_y[0] if closes_y else 0

            results[name] = {"now": now, "dod": dod, "wow": wow, "yoy": yoy}
        except Exception as e:
            results[name] = {"error": str(e)}
    return results


# ─── 既存スクリプト subprocess ─────────────────────────────────────────────

def _run_script(script_name: str, args: list[str] = None, timeout: int = 120) -> str:
    """既存スクリプトを subprocess で実行し stdout を返す"""
    cmd = [PYTHON, str(SCRIPTS_DIR / script_name)] + (args or [])
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=str(SCRIPTS_DIR.parent),
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return ""
    except Exception as e:
        return f"ERROR: {e}"


def run_portal_headless() -> list[dict]:
    """portal.py --headless → portal_latest.json を読んで返す"""
    _run_script("scrapers/portal.py", ["--headless"], timeout=300)
    latest_path = DRAFTS_DIR / "portal_latest.json"
    if latest_path.exists():
        with open(latest_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("notices", [])
    return []


def run_stx_summary() -> str:
    """stx_kanrihyo.py --summary の出力テキストをそのまま返す"""
    return _run_script("scrapers/stx_kanrihyo.py", ["--summary"])


def run_area_events() -> list[dict]:
    """area_events.py --format json の出力を JSON パースして返す"""
    output = _run_script("scrapers/area_events.py", ["--format", "json"], timeout=60)
    try:
        return json.loads(output)
    except Exception:
        return []


def run_rakushifu_sync() -> str:
    """rakushifu_sync.py --confirm-shifts --headless の出力を返す"""
    return _run_script("scrapers/rakushifu_sync.py", ["--confirm-shifts", "--headless"], timeout=120)
