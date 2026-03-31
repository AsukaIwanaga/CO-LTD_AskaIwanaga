#!/usr/bin/env python3
"""
マネーフォワード ME 残高自動取得スクリプト

- 保存済みセッション（drafts/mf_session.json）でログイン
- 銀行（ゆうちょ）・ローン・クレジットカード残高を取得
- financial.json に自動 upsert
- セッション切れ → 警告出力 + exit(1)
- 再連携要求を検知 → 警告出力（残高は記録しない）
"""

import json, re, sys
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

SESSION_PATH   = (Path(__file__).parent / "../../drafts/mf_session.json").resolve()
FINANCIAL_PATH = (Path(__file__).parent / "../../data/financial.json").resolve()
ACCOUNTS_URL   = "https://moneyforward.com/accounts"

# 取得対象アカウント名キーワード（ゆうちょを main として扱う）
MAIN_KEYWORDS  = ["ゆうちょ", "郵便貯金", "Japan Post"]
LOAN_KEYWORDS  = ["ローン", "住宅ローン", "カードローン", "借入"]
CREDIT_KEYWORDS = ["クレジット", "カード", "VISA", "Mastercard", "JCB", "AMEX", "楽天カード", "dカード", "Suica"]

# 再連携が必要な状態を示すキーワード
RELINK_KEYWORDS = ["再連携", "再認証", "更新が必要", "接続が切れ", "連携エラー", "エラーが発生"]


def load_session():
    if not SESSION_PATH.exists():
        return None
    try:
        with open(SESSION_PATH) as f:
            return json.load(f)
    except Exception:
        return None


def is_logged_in(page) -> bool:
    url = page.url
    return "id.moneyforward.com" not in url and "sign_in" not in url


def parse_amount(text: str) -> int:
    """「¥1,234,567」「-1,234,567円」などを整数に変換。負の値はそのまま返す。"""
    text = text.replace(",", "").replace("¥", "").replace("円", "").strip()
    try:
        return int(re.sub(r"[^\d\-]", "", text))
    except Exception:
        return 0


def fetch_balances() -> dict:
    """
    マネーフォワード ME から残高を取得。
    Returns: {
        "main": int,    # ゆうちょ残高
        "loan": int,    # ローン残高
        "credit": int,  # クレジット利用残高
        "relink_warning": bool,
    }
    """
    session = load_session()
    if not session:
        print("⚠ セッションがありません。python3 scripts/mf_login.py を実行してください。")
        sys.exit(1)

    result = {"main": 0, "loan": 0, "credit": 0, "relink_warning": False}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # headless だと Forbidden になるため非 headless で実行
            args=["--disable-blink-features=AutomationControlled", "--window-size=1200,800"],
        )
        context = browser.new_context(
            storage_state=session,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            ignore_https_errors=True,
        )
        page = context.new_page()

        # ネットワークレスポンスをインターセプト（内部 API があれば活用）
        api_data = {}
        def handle_response(response):
            if "accounts" in response.url and response.status == 200:
                try:
                    data = response.json()
                    if isinstance(data, (dict, list)):
                        api_data["accounts"] = data
                except Exception:
                    pass

        page.on("response", handle_response)

        print("マネーフォワードにアクセス中...")
        page.goto(ACCOUNTS_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)

        # アカウント選択画面の自動クリック
        if "account_selector" in page.url:
            print("  → アカウント選択画面。自動選択中...")
            try:
                page.click("text=asuka.ctn1@gmail.com", timeout=5000)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3000)
            except Exception:
                pass

        if not is_logged_in(page):
            browser.close()
            print("⚠ セッション切れです。python3 scripts/mf_login.py を実行してください。")
            sys.exit(1)

        # 再連携要求チェック
        content = page.content()
        if any(kw in content for kw in RELINK_KEYWORDS):
            result["relink_warning"] = True
            print("⚠ 再連携が必要なアカウントがあります。マネーフォワードで確認してください。")

        # ─── DOM スクレイピング ────────────────────────────────────────
        # 内部 API データがあれば使う
        if api_data.get("accounts"):
            result = parse_from_api(api_data["accounts"], result)
        else:
            result = parse_from_dom(page, result)

        # セッション更新して保存
        context.storage_state(path=str(SESSION_PATH))
        browser.close()

    return result


def parse_from_api(data, result: dict) -> dict:
    """内部 API レスポンスから残高を抽出"""
    accounts = data if isinstance(data, list) else data.get("accounts", [])
    for acc in accounts:
        name    = acc.get("name", "") or acc.get("service_name", "")
        balance = acc.get("balance", 0) or acc.get("amount", 0)
        try:
            balance = int(balance)
        except Exception:
            continue
        if any(kw in name for kw in MAIN_KEYWORDS):
            result["main"] += balance
        elif any(kw in name for kw in LOAN_KEYWORDS):
            result["loan"] += abs(balance)
        elif any(kw in name for kw in CREDIT_KEYWORDS):
            result["credit"] += abs(balance)
    return result


def parse_from_dom(page, result: dict) -> dict:
    """
    マネーフォワード ME の口座一覧ページ（/accounts）をテーブルセル単位でパース。
    table の各 tr を走査し、金融機関名セルと残高セルをペアで取得する。
    """
    try:
        rows = page.locator("table tr").all()
        for row in rows:
            cells = row.locator("td").all()
            if len(cells) < 2:
                continue

            try:
                inst_text = cells[0].inner_text().strip()
                bal_text  = cells[1].inner_text().strip()
            except Exception:
                continue

            # 残高セルに「円」がなければスキップ
            if "円" not in bal_text:
                continue

            amount = parse_amount(bal_text)

            if any(kw in inst_text for kw in MAIN_KEYWORDS):
                result["main"] += amount
                print(f"  {inst_text[:20]}: ¥{amount:,}")
            elif any(kw in inst_text for kw in LOAN_KEYWORDS):
                result["loan"] += abs(amount)
                print(f"  {inst_text[:20]}(ローン): ¥{abs(amount):,}")
            elif any(kw in inst_text for kw in CREDIT_KEYWORDS):
                result["credit"] += abs(amount)
                print(f"  {inst_text[:20]}(クレジット): ¥{abs(amount):,}")

        # 設定エラーの検知
        body_text = page.inner_text("body")
        if "設定エラー" in body_text:
            print("⚠ 設定エラーのアカウントがあります。マネーフォワードで再連携が必要です。")
            result["relink_warning"] = True

    except Exception as e:
        print(f"DOM パースエラー: {e}")

    return result


def parse_fallback(page, result: dict) -> dict:
    """使用しない（parse_from_dom で完結）"""
    return result


def upsert_financial(main: int, loan: int, credit: int):
    """financial.json に今日分の残高を upsert"""
    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().isoformat()

    existing = []
    if FINANCIAL_PATH.exists():
        try:
            with open(FINANCIAL_PATH) as f:
                existing = json.load(f)
        except Exception:
            existing = []

    # 今日のエントリがあれば更新、なければ追加
    today_entry = next((e for e in existing if e.get("date") == today), None)

    if today_entry:
        today_entry["main"]      = main
        today_entry["loan"]      = loan
        today_entry["credit"]    = credit
        today_entry["timestamp"] = timestamp
        today_entry["description"] = "mf_balance.py 自動取得"
    else:
        new_id = str(max((int(e.get("id", 0)) for e in existing), default=0) + 1)
        existing.append({
            "id":          new_id,
            "date":        today,
            "timestamp":   timestamp,
            "main":        main,
            "loan":        loan,
            "credit":      credit,
            "description": "mf_balance.py 自動取得",
        })

    with open(FINANCIAL_PATH, "w") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"✅ financial.json 更新: 残高¥{main:,} / ローン¥{loan:,} / クレジット¥{credit:,}")


def main():
    balances = fetch_balances()

    main_bal = balances.get("main", 0)
    loan_bal = balances.get("loan", 0)
    credit_bal = balances.get("credit", 0)

    print(f"\n取得結果:")
    print(f"  ゆうちょ残高 : ¥{main_bal:,}")
    print(f"  ローン残高   : ¥{loan_bal:,}")
    print(f"  クレジット   : ¥{credit_bal:,}")

    if balances.get("relink_warning"):
        print("\n⚠ 再連携が必要なアカウントがあります。マネーフォワードで確認してください。")

    if main_bal == 0 and loan_bal == 0 and credit_bal == 0:
        print("\n⚠ 残高が取得できませんでした。セレクタが変更された可能性があります。")
        print("  手動で確認して financial.json を更新するか、mf_login.py で再ログインしてください。")
        sys.exit(2)

    upsert_financial(main_bal, loan_bal, credit_bal)


if __name__ == "__main__":
    main()
