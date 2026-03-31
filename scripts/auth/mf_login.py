#!/usr/bin/env python3
"""
マネーフォワード ME ログインスクリプト（手動実行用）

- ブラウザを表示して手動ログイン
- ログイン完了後、セッションを drafts/mf_session.json に保存
- 以降は mf_balance.py が自動でセッションを再利用
"""

import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

SESSION_PATH = (Path(__file__).parent / "../../drafts/mf_session.json").resolve()
MF_URL = "https://moneyforward.com"


def main():
    print("マネーフォワード ME にログインします。")
    print("ブラウザが開いたら、手動でログインしてください。")
    print("ログイン完了後、このスクリプトが自動的にセッションを保存します。")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--window-size=1200,800"],
        )
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://id.moneyforward.com/sign_in")
        page.wait_for_load_state("networkidle")

        print("ログイン画面が開きました。ログインしてください...")
        print("（二要素認証がある場合はそのまま完了させてください）")

        # ログイン完了を待機（アカウントページに到達するまで）
        try:
            page.wait_for_url(
                lambda url: "moneyforward.com" in url and "sign_in" not in url and "id.moneyforward.com" not in url,
                timeout=300000,  # 5分待機
            )
        except Exception:
            print("⚠ タイムアウトしました。ログインが完了しているか確認してください。")
            browser.close()
            sys.exit(1)

        print("ログイン確認済み。セッションを保存中...")
        SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(SESSION_PATH))
        browser.close()

    print(f"✅ セッションを保存しました: {SESSION_PATH}")
    print("以降は mf_balance.py が自動で残高を取得します。")


if __name__ == "__main__":
    main()
