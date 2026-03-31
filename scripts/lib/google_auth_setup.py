#!/usr/bin/env python3
"""
Google OAuth 初回認証セットアップ

ブラウザが開き、Google アカウントでログイン → 認証コードを取得 → トークンを保存。
private / work アカウントそれぞれに対して実行する。

Usage:
  python3 scripts/lib/google_auth_setup.py private   # asuka.ctn1@gmail.com
  python3 scripts/lib/google_auth_setup.py work      # asuka.iwanaga@skylark.co.jp
"""

import json, sys, time, webbrowser, urllib.request, urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# プロジェクトルートからの相対パス
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_DIR / "scripts"))
from lib.config import GCP_OAUTH_KEYS, GCP_TOKEN_PRIVATE, GCP_TOKEN_WORK

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks",
]

REDIRECT_URI = "http://localhost:8089"


class OAuthHandler(BaseHTTPRequestHandler):
    code = None

    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        OAuthHandler.code = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK! You can close this window.")

    def log_message(self, format, *args):
        pass  # suppress logs


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("private", "work"):
        print("Usage: python3 google_auth_setup.py [private|work]")
        sys.exit(1)

    account = sys.argv[1]
    token_path = GCP_TOKEN_PRIVATE if account == "private" else GCP_TOKEN_WORK

    with open(GCP_OAUTH_KEYS, encoding="utf-8") as f:
        keys_data = json.load(f)
    keys = keys_data.get("installed", keys_data.get("web", keys_data))

    # 認証 URL を構築
    auth_url = (
        f"{keys['auth_uri']}?"
        f"client_id={keys['client_id']}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&response_type=code"
        f"&scope={urllib.parse.quote(' '.join(SCOPES))}"
        f"&access_type=offline"
        f"&prompt=consent"
    )

    print(f"\n{'='*50}")
    print(f"Google OAuth セットアップ [{account}]")
    print(f"{'='*50}")
    if account == "private":
        print("asuka.ctn1@gmail.com でログインしてください")
    else:
        print("asuka.iwanaga@skylark.co.jp でログインしてください")
    print()

    # ローカルサーバー起動
    server = HTTPServer(("localhost", 8089), OAuthHandler)
    webbrowser.open(auth_url)
    print("ブラウザが開きます。ログインして権限を許可してください...")

    # コールバック待ち
    while OAuthHandler.code is None:
        server.handle_request()

    code = OAuthHandler.code
    print(f"認証コード取得: {code[:20]}...")

    # トークン交換
    params = urllib.parse.urlencode({
        "code": code,
        "client_id": keys["client_id"],
        "client_secret": keys["client_secret"],
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(keys["token_uri"], data=params, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        token_data = json.loads(resp.read())

    token_data["expires_at"] = int(time.time()) + token_data.get("expires_in", 3600)

    # 保存
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with open(token_path, "w", encoding="utf-8") as f:
        json.dump(token_data, f, ensure_ascii=False, indent=2)

    print(f"\nトークン保存完了: {token_path}")
    print(f"スコープ: {', '.join(SCOPES)}")
    print("セットアップ完了!")


if __name__ == "__main__":
    main()
