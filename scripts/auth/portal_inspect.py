#!/usr/bin/env python3
"""ポータルページの構造を詳細確認"""

import os, json
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))
PORTAL_URL  = os.getenv("SKYLARK_PORTAL_URL")
COOKIES_PATH = Path(__file__).parent / "../../drafts/session_cookies.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    with open(COOKIES_PATH) as f:
        context.add_cookies(json.load(f))
    page = context.new_page()
    page.goto(PORTAL_URL)
    page.wait_for_load_state("networkidle")

    soup = BeautifulSoup(page.content(), "html.parser")

    print("=== ページタイトル ===")
    print(soup.title.string if soup.title else "なし")

    print("\n=== 全テキスト（先頭3000文字）===")
    print(soup.get_text(separator="\n", strip=True)[:3000])

    print("\n=== リンク一覧 ===")
    for a in soup.find_all("a", href=True)[:20]:
        print(f"  {a.get_text(strip=True)[:50]}  →  {a['href']}")

    browser.close()
