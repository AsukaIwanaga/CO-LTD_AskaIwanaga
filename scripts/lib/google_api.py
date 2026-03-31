"""Google API 直接呼出（Gmail / Calendar / Tasks）

cron 環境では MCP が使えないため、OAuth トークンで直接 API を叩く。
private (asuka.ctn1@gmail.com) と work (asuka.iwanaga@skylark.co.jp) の
2アカウントで別トークンを管理する。
"""

import json
import time
import urllib.request
import urllib.parse
import base64
from pathlib import Path
from .config import GCP_OAUTH_KEYS, GCP_TOKEN_PRIVATE, GCP_TOKEN_WORK


class GoogleAuth:
    """OAuth トークン管理。期限切れ時に自動リフレッシュ。"""

    def __init__(self, token_path: Path, keys_path: Path = GCP_OAUTH_KEYS):
        self.token_path = token_path
        self.keys_path = keys_path
        self._token_data = None
        self._keys = None

    def _load_keys(self) -> dict:
        if self._keys is None:
            with open(self.keys_path, encoding="utf-8") as f:
                data = json.load(f)
            self._keys = data.get("installed", data.get("web", data))
        return self._keys

    def _load_token(self) -> dict:
        if self._token_data is None:
            if not self.token_path.exists():
                raise FileNotFoundError(
                    f"トークンファイルが見つかりません: {self.token_path}\n"
                    f"python3 scripts/lib/google_auth_setup.py を実行してください"
                )
            with open(self.token_path, encoding="utf-8") as f:
                self._token_data = json.load(f)
        return self._token_data

    def _save_token(self, data: dict) -> None:
        self._token_data = data
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _refresh_token(self) -> str:
        """refresh_token で access_token を再取得"""
        token = self._load_token()
        keys = self._load_keys()
        params = urllib.parse.urlencode({
            "client_id": keys["client_id"],
            "client_secret": keys["client_secret"],
            "refresh_token": token["refresh_token"],
            "grant_type": "refresh_token",
        }).encode()
        req = urllib.request.Request(keys["token_uri"], data=params, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        token["access_token"] = result["access_token"]
        token["expires_at"] = int(time.time()) + result.get("expires_in", 3600)
        self._save_token(token)
        return token["access_token"]

    def get_access_token(self) -> str:
        """有効な access_token を返す（期限切れなら自動更新）"""
        token = self._load_token()
        if token.get("expires_at", 0) < time.time() + 60:
            return self._refresh_token()
        return token["access_token"]

    def api_get(self, url: str) -> dict:
        """認証付き GET リクエスト"""
        token = self.get_access_token()
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())

    def api_post(self, url: str, body: dict | str) -> dict:
        """認証付き POST リクエスト"""
        token = self.get_access_token()
        if isinstance(body, dict):
            data = json.dumps(body).encode()
            content_type = "application/json"
        else:
            data = body.encode() if isinstance(body, str) else body
            content_type = "application/json"
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", content_type)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())


# ─── シングルトン ──────────────────────────────────────────────────────────

_auth_private = None
_auth_work = None


def _get_auth(account: str = "private") -> GoogleAuth:
    global _auth_private, _auth_work
    if account == "work":
        if _auth_work is None:
            _auth_work = GoogleAuth(GCP_TOKEN_WORK)
        return _auth_work
    else:
        if _auth_private is None:
            _auth_private = GoogleAuth(GCP_TOKEN_PRIVATE)
        return _auth_private


# ─── Gmail ─────────────────────────────────────────────────────────────────

def gmail_list_unread(account: str = "private", max_results: int = 5) -> list[dict]:
    """未読メール一覧を取得（件名・送信者・本文要約）"""
    auth = _get_auth(account)
    url = (
        "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        f"?q=is%3Aunread%20in%3Ainbox&maxResults={max_results}"
    )
    try:
        result = auth.api_get(url)
    except Exception as e:
        return [{"error": str(e)}]

    messages = []
    for msg_ref in result.get("messages", []):
        msg_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_ref['id']}?format=metadata&metadataHeaders=Subject&metadataHeaders=From"
        try:
            msg = auth.api_get(msg_url)
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            messages.append({
                "id": msg["id"],
                "subject": headers.get("Subject", "(件名なし)"),
                "from": headers.get("From", ""),
                "snippet": msg.get("snippet", ""),
            })
        except Exception:
            continue
    return messages


def gmail_send_raw(raw_base64: str, account: str = "private") -> dict:
    """base64url エンコード済み MIME メッセージを送信"""
    auth = _get_auth(account)
    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    return auth.api_post(url, {"raw": raw_base64})


# ─── Calendar ──────────────────────────────────────────────────────────────

def calendar_list_events(target_date: str, calendar_ids: list[str] = None,
                         account: str = "private") -> list[dict]:
    """指定日のイベント一覧を取得"""
    if calendar_ids is None:
        calendar_ids = ["primary"]
    auth = _get_auth(account)

    time_min = f"{target_date}T00:00:00+09:00"
    time_max = f"{target_date}T23:59:59+09:00"

    all_events = []
    for cal_id in calendar_ids:
        encoded_id = urllib.parse.quote(cal_id)
        url = (
            f"https://www.googleapis.com/calendar/v3/calendars/{encoded_id}/events"
            f"?timeMin={urllib.parse.quote(time_min)}"
            f"&timeMax={urllib.parse.quote(time_max)}"
            f"&singleEvents=true&orderBy=startTime"
        )
        try:
            result = auth.api_get(url)
            for item in result.get("items", []):
                start = item.get("start", {})
                all_events.append({
                    "summary": item.get("summary", "(無題)"),
                    "start": start.get("dateTime", start.get("date", "")),
                    "end": item.get("end", {}).get("dateTime", ""),
                    "location": item.get("location", ""),
                    "calendar": cal_id,
                })
        except Exception:
            continue

    all_events.sort(key=lambda e: e["start"])
    return all_events


# ─── Tasks ─────────────────────────────────────────────────────────────────

def _get_default_list_id(account: str = "private") -> str:
    """デフォルトのタスクリストIDを取得"""
    auth = _get_auth(account)
    lists_result = auth.api_get(
        "https://tasks.googleapis.com/tasks/v1/users/@me/lists"
    )
    items = lists_result.get("items", [])
    return items[0]["id"] if items else ""


def tasks_list_all(account: str = "private", include_completed: bool = False) -> list[dict]:
    """Google Tasks の全タスク一覧（ID付き）"""
    auth = _get_auth(account)
    tasks = []

    try:
        lists_result = auth.api_get(
            "https://tasks.googleapis.com/tasks/v1/users/@me/lists"
        )
    except Exception as e:
        return [{"error": str(e)}]

    show_completed = "true" if include_completed else "false"
    for task_list in lists_result.get("items", []):
        list_id = task_list["id"]
        list_name = task_list.get("title", "")
        try:
            tasks_result = auth.api_get(
                f"https://tasks.googleapis.com/tasks/v1/lists/{list_id}/tasks"
                f"?showCompleted={show_completed}&showHidden=false&maxResults=100"
            )
            for item in tasks_result.get("items", []):
                tasks.append({
                    "google_task_id": item["id"],
                    "google_list_id": list_id,
                    "title": item.get("title", ""),
                    "due": item.get("due", ""),
                    "notes": item.get("notes", ""),
                    "status": item.get("status", "needsAction"),
                    "list": list_name,
                    "updated": item.get("updated", ""),
                })
        except Exception:
            continue

    return tasks


def tasks_list_incomplete(account: str = "private") -> list[dict]:
    """Google Tasks の未完了タスク一覧"""
    all_tasks = tasks_list_all(account, include_completed=False)
    return [t for t in all_tasks if t.get("status") != "completed"]


def tasks_create(title: str, due: str = "", notes: str = "",
                 account: str = "private") -> dict:
    """Google Tasks にタスクを作成"""
    auth = _get_auth(account)
    list_id = _get_default_list_id(account)
    body = {"title": title}
    if due:
        # YYYY-MM-DD → RFC 3339
        body["due"] = f"{due}T00:00:00.000Z"
    if notes:
        body["notes"] = notes
    return auth.api_post(
        f"https://tasks.googleapis.com/tasks/v1/lists/{list_id}/tasks",
        body
    )


def tasks_complete(task_id: str, list_id: str = "",
                   account: str = "private") -> dict:
    """Google Tasks のタスクを完了にする"""
    auth = _get_auth(account)
    if not list_id:
        list_id = _get_default_list_id(account)
    url = f"https://tasks.googleapis.com/tasks/v1/lists/{list_id}/tasks/{task_id}"
    # PATCH で status を completed に
    token = auth.get_access_token()
    data = json.dumps({"status": "completed"}).encode()
    req = urllib.request.Request(url, data=data, method="PATCH")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def tasks_delete(task_id: str, list_id: str = "",
                 account: str = "private") -> bool:
    """Google Tasks のタスクを削除"""
    auth = _get_auth(account)
    if not list_id:
        list_id = _get_default_list_id(account)
    url = f"https://tasks.googleapis.com/tasks/v1/lists/{list_id}/tasks/{task_id}"
    token = auth.get_access_token()
    req = urllib.request.Request(url, method="DELETE")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        urllib.request.urlopen(req, timeout=15)
        return True
    except Exception:
        return False
