#!/usr/bin/env python3
"""
ポータル ログイン専用スクリプト（初回・Cookie期限切れ時に実行）

ブラウザを開いて手動（またはGoogle自動）ログイン後、
セッション状態（session cookieを含む）を storage_state.json に保存する。
portal.py はこのファイルを毎回読み込んでセッションを復元する。
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

PORTAL_URL    = "https://skylark.shoprun.jp/h2/STRStorePage.do"
STATE_PATH    = (Path(__file__).parent / "../../drafts/storage_state.json").resolve()

print("="*50)
print("ポータルログインスクリプト")
print("Googleアカウントでログインしてください。")
print("ログイン後、ポータルが表示されたら自動で保存します。")
print("="*50)

STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.goto(PORTAL_URL)

    print("\nポータルへのリダイレクト待機中...")
    print("（Googleアカウントでログインしてください）")

    try:
        page.wait_for_url("**/STRStorePage.do**", timeout=180000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # session cookieを含む全状態を保存
        context.storage_state(path=str(STATE_PATH))
        print(f"✓ ログイン完了 — セッション状態を保存しました")
        print(f"  → {STATE_PATH}")
    except Exception as e:
        print(f"タイムアウトまたはエラー: {e}")
        print("ログインを完了させてから再度実行してください。")
    finally:
        browser.close()
