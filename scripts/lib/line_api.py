"""LINE Messaging API — テキスト・画像 Push 送信"""

import json
import urllib.request
from pathlib import Path
from .config import get_env

PUSH_URL = "https://api.line.me/v2/bot/message/push"


def _token() -> str:
    return get_env("LINE_CHANNEL_ACCESS_TOKEN")


def _uid() -> str:
    return get_env("LINE_USER_ID")


def send_text(text: str, user_id: str = "") -> dict:
    """テキストメッセージを Push 送信"""
    body = json.dumps({
        "to": user_id or _uid(),
        "messages": [{"type": "text", "text": text}]
    }).encode()

    req = urllib.request.Request(PUSH_URL, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {_token()}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req, timeout=15) as resp:
        result = resp.read()
        return json.loads(result) if result.strip() else {"status": "ok"}


def send_image(image_path: Path, user_id: str = "") -> dict:
    """画像を catbox.moe にアップロード → LINE Push 送信"""
    if not image_path.exists():
        return {"error": f"file not found: {image_path}"}

    # catbox.moe に匿名アップロード（無期限保持）
    url = _upload_catbox(image_path)
    if not url:
        return send_text("ブリーフィング画像の送信に失敗しました。")

    uid = user_id or _uid()
    body = json.dumps({
        "to": uid,
        "messages": [{
            "type": "image",
            "originalContentUrl": url,
            "previewImageUrl": url,
        }]
    }).encode()

    req = urllib.request.Request(PUSH_URL, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {_token()}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = resp.read()
            return json.loads(result) if result.strip() else {"status": "ok", "image_url": url}
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode(), "code": e.code}


def _upload_catbox(image_path: Path) -> str:
    """catbox.moe に匿名アップロード（HTTPS、無期限）"""
    try:
        boundary = "----CatboxBoundary"
        image_data = image_path.read_bytes()
        filename = image_path.name

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="reqtype"\r\n\r\nfileupload\r\n'
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="fileToUpload"; filename="{filename}"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode() + image_data + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            "https://catbox.moe/user/api.php",
            data=body,
            method="POST"
        )
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode().strip()
    except Exception as e:
        print(f"catbox.moe upload failed: {e}")
        return ""
