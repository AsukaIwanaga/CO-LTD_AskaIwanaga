"""メール構築・送信 — 等幅フォント HTML メール"""

import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.audio import MIMEAudio
from pathlib import Path
from .config import TO_PRIVATE, TO_WORK
from .google_api import gmail_send_raw



def build_mime(to: str, subject: str, body: str,
               attachments: list[Path] = None) -> str:
    """MIME メッセージを構築し base64url 文字列を返す"""
    if attachments:
        msg = MIMEMultipart()
        msg.attach(MIMEText(body, "plain", "utf-8"))
        for path in attachments:
            if path.exists():
                with open(path, "rb") as f:
                    audio = MIMEAudio(f.read(), _subtype="mpeg")
                audio.add_header("Content-Disposition", "attachment", filename=path.name)
                msg.attach(audio)
    else:
        msg = MIMEText(body, "plain", "utf-8")

    msg["To"] = to
    msg["Subject"] = subject
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


def send_email(subject: str, body: str,
               to_private: bool = True, to_work: bool = True,
               attachments: list[Path] = None) -> dict:
    """Gmail API 経由でメール送信"""
    results = {}
    if to_private:
        raw = build_mime(TO_PRIVATE, subject, body, attachments)
        results["private"] = gmail_send_raw(raw, account="private")
    if to_work:
        raw_work = build_mime(TO_WORK, subject, body, attachments)
        results["work"] = gmail_send_raw(raw_work, account="work")
    return results


def send_error_notification(feature: str, error_msg: str, tb: str) -> None:
    """エラー通知メール（private のみ）"""
    subject = f"[ERROR] {feature} 実行失敗"
    body = f"Feature: {feature}\nError: {error_msg}\n\nTraceback:\n{tb}"
    try:
        raw = build_mime(TO_PRIVATE, subject, body)
        gmail_send_raw(raw, account="private")
    except Exception:
        pass
