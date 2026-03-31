#!/usr/bin/env python3
"""
STX（営業データシステム）ログインスクリプト

Google SAML SSO でログインし、セッション状態を stx_storage_state.json に保存する。
stx_kanrihyo.py 実行前に一度実行すること（またはセッション期限切れ時）。
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv(dotenv_path=Path(__file__).parent / "../../.env")

STX_URL    = "https://sdsr-co.go.akamai-access.com/stx/index.html"
STATE_PATH = (Path(__file__).parent / "../../drafts/stx_storage_state.json").resolve()
EMAIL      = os.getenv("SKYLARK_EMAIL", "")
PASSWORD   = os.getenv("SKYLARK_GOOGLE_PASSWORD", "")


def complete_google_login(page):
    """Google OAuth フォームを自動入力してログイン（portal.py と同じ手順）"""
    try:
        page.wait_for_selector("input[type='email']", timeout=10000)
        page.fill("input[type='email']", EMAIL)
        page.click("#identifierNext")
        page.wait_for_timeout(3000)

        if "challenge/pk" in page.url:
            print("  → パスキー画面を検出。パスワード認証に切り替え中...")
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
        print(f"  自動ログインエラー: {e}")
        return False


def main():
    if not EMAIL or not PASSWORD:
        print("⚠ .env に SKYLARK_EMAIL / SKYLARK_GOOGLE_PASSWORD が設定されていません。")
        return

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    print("=" * 50)
    print("STX ログインスクリプト")
    print(f"対象: {STX_URL}")
    print("=" * 50)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        print("STX へアクセス中...")
        page.goto(STX_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)

        # Google 認証へリダイレクトされた場合
        if "accounts.google.com" in page.url:
            print("  → Google 認証を自動入力中...")
            if not complete_google_login(page):
                print("⚠ 自動ログイン失敗。ブラウザで手動ログインしてください...")

        # STX へのリダイレクト待ち
        try:
            page.wait_for_url(
                lambda url: "akamai-access.com/stx" in url and "accounts.google.com" not in url,
                timeout=120000,
            )
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
        except Exception as e:
            if "accounts.google.com" in page.url:
                print("⚠ 追加認証が必要です。ブラウザで完了してください...")
                try:
                    page.wait_for_url(
                        lambda url: "akamai-access.com/stx" in url,
                        timeout=180000,
                    )
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(2000)
                except Exception:
                    print(f"タイムアウト: {e}")
                    browser.close()
                    return
            else:
                print(f"⚠ タイムアウト: {e} / URL: {page.url}")
                browser.close()
                return

        # セッション保存
        context.storage_state(path=str(STATE_PATH))
        print(f"✓ ログイン完了 — セッション保存: {STATE_PATH}")
        browser.close()


if __name__ == "__main__":
    main()
