"""テキスト整形ユーティリティ — iPhone 等幅表示対応"""

import unicodedata

# iPhone 12 Gmail 等幅フォント表示幅（半角単位）
MAX_WIDTH = 24


def char_width(c: str) -> int:
    """全角=2, 半角=1"""
    ea = unicodedata.east_asian_width(c)
    return 2 if ea in ("F", "W", "A") else 1


def str_width(s: str) -> int:
    """文字列の表示幅（半角単位）"""
    return sum(char_width(c) for c in s)


def truncate(text: str, max_width: int = MAX_WIDTH) -> str:
    """表示幅に収まるよう切り詰め"""
    result = ""
    w = 0
    for c in text:
        cw = char_width(c)
        if w + cw > max_width:
            break
        result += c
        w += cw
    return result


def wrap_lines(text: str, max_width: int = MAX_WIDTH) -> list[str]:
    """表示幅を考慮して複数行に折り返す"""
    lines = []
    current = ""
    w = 0
    for c in text:
        cw = char_width(c)
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


def separator(char: str = "─", width: int = MAX_WIDTH) -> str:
    """区切り線（全角文字なら幅/2個）"""
    cw = char_width(char)
    return char * (width // cw)
