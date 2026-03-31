#!/usr/bin/env python3
"""週次提案報告 — project/will/ の未報告提案を Don にメール報告"""

import sys, re
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.config import PROJECT_DIR
from lib.mailer import send_email

WILL_DIR = PROJECT_DIR / "project" / "will"


def _char_width(c: str) -> int:
    """全角=2, 半角=1"""
    import unicodedata
    ea = unicodedata.east_asian_width(c)
    return 2 if ea in ("F", "W", "A") else 1


def _str_width(s: str) -> int:
    """文字列の表示幅（半角単位）"""
    return sum(_char_width(c) for c in s)


def _wrap(text: str, max_width: int) -> str:
    """1行に収まるよう切り詰め"""
    result = ""
    w = 0
    for c in text:
        cw = _char_width(c)
        if w + cw > max_width:
            break
        result += c
        w += cw
    return result


def _wrap_lines(text: str, max_width: int) -> list[str]:
    """表示幅を考慮して複数行に折り返す"""
    lines = []
    current = ""
    w = 0
    for c in text:
        cw = _char_width(c)
        if w + cw > max_width:
            lines.append(current)
            current = c
            w = cw
        else:
            current += c
            w += cw
    if current:
        lines.append(current)
    return lines if lines else [""]


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    today = date.today().isoformat()
    print(f"[{now}] weekly_proposal 開始")

    # will/ 内の .md ファイルを収集
    proposals = []
    for f in sorted(WILL_DIR.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        # reported チェック
        reported_match = re.search(r"\*\*reported\*\*:\s*(.+)", content)
        if reported_match:
            reported_val = reported_match.group(1).strip()
            if reported_val and reported_val != "（未報告）":
                continue  # 既報告 → スキップ

        # タイトル抽出
        title_match = re.search(r"^# WILL:\s*(.+)", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else f.stem

        # 各セクション抽出
        sections = {}
        for section in ["課題", "提案", "期待効果", "工数見積"]:
            sec_match = re.search(rf"## {section}\n(.+?)(?=\n## |\Z)", content, re.DOTALL)
            if sec_match:
                sections[section] = sec_match.group(1).strip()

        proposals.append({
            "file": f,
            "title": title,
            "sections": sections,
        })

    if not proposals:
        print(f"[{now}] 未報告の提案なし")
        return

    # メール本文（構造は維持、幅制御はGmailに任せる）
    lines = [
        "WEEKLY PROPOSAL",
        today,
        "=" * 33,
        f"Michael より {len(proposals)}件",
        "",
    ]

    for i, p in enumerate(proposals, 1):
        lines.append("-" * 33)
        lines.append(f"[{i}] {p['title']}")
        lines.append("-" * 33)
        lines.append("")
        for key in ["課題", "提案", "期待効果", "工数見積"]:
            val = p["sections"].get(key, "")
            if val:
                lines.append(f"【{key}】")
                for chunk_line in val.split("\n"):
                    chunk_line = chunk_line.strip()
                    if chunk_line:
                        lines.append(chunk_line)
                lines.append("")

    lines.append("=" * 33)
    lines.append("やろう→active")
    lines.append("保留→据置")
    lines.append("不要→削除")

    body = "\n".join(lines)

    # メール送信
    send_email(
        subject=f"週次提案報告 {today} ({len(proposals)}件)",
        body=body,
        to_private=True,
        to_work=False,  # 提案報告は private のみ
    )
    print(f"  → メール送信完了 ({len(proposals)}件)")

    # reported フラグを付与
    for p in proposals:
        content = p["file"].read_text(encoding="utf-8")
        content = content.replace("**reported**: （未報告）", f"**reported**: {today}")
        p["file"].write_text(content, encoding="utf-8")
        print(f"  → reported: {p['title']}")

    print(f"[{now}] weekly_proposal 完了")


if __name__ == "__main__":
    main()
