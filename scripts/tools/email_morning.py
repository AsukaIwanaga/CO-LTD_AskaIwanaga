#!/usr/bin/env python3
"""
email_morning.py — 朝のブリーフィングをメール送信用の raw MIME を生成する
使い方:
  python3 scripts/email_morning.py "本文テキスト"                    # MP3 なし
  python3 scripts/email_morning.py "本文テキスト" /path/to/morning.mp3  # MP3 添付
stdout に {"private": "<base64url>", "work": "<base64url>"} を JSON で出力する。
Claude が mcp__gmail__send_message の raw パラメータに渡す。
"""

import base64
import email.header
import email.mime.audio
import email.mime.multipart
import email.mime.text
import json
import sys
from datetime import datetime
from pathlib import Path

TO_PRIVATE = "asuka.ctn1@gmail.com"
TO_WORK    = "asuka.iwanaga@skylark.co.jp"


def build_raw(body: str, to: str, mp3_path: Path | None = None) -> str:
    """multipart/mixed MIME メッセージを構築し base64url 文字列を返す。"""
    if mp3_path and mp3_path.exists():
        msg = email.mime.multipart.MIMEMultipart()
    else:
        msg = email.mime.multipart.MIMEMultipart()

    msg["To"]      = to
    subject_str = f"朝のブリーフィング {datetime.now().strftime('%Y/%m/%d (%a)')}"
    msg["Subject"] = email.header.Header(subject_str, "utf-8")

    # 本文
    msg.attach(email.mime.text.MIMEText(body, "plain", "utf-8"))

    # MP3 添付（ファイルが存在する場合のみ）
    if mp3_path and mp3_path.exists():
        audio_data = mp3_path.read_bytes()
        part = email.mime.audio.MIMEAudio(audio_data, "mpeg")
        part["Content-Disposition"] = (
            f'attachment; filename="morning_{datetime.now().strftime("%Y-%m-%d")}.mp3"'
        )
        msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return raw


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 scripts/email_morning.py \"本文\" [/path/to/morning.mp3]", file=sys.stderr)
        sys.exit(1)

    body     = sys.argv[1]
    mp3_path = Path(sys.argv[2]) if len(sys.argv) >= 3 and sys.argv[2] else None

    if mp3_path and not mp3_path.exists():
        print(f"[WARNING] MP3ファイルが見つかりません: {mp3_path}", file=sys.stderr)
        mp3_path = None

    result = {
        "private": build_raw(body, TO_PRIVATE, mp3_path),
        "work":    build_raw(body, TO_WORK,    mp3_path),
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
