#!/usr/bin/env python3
"""
Luca Brasi — サムネイル生成 (1280x720)
Usage: python3 studio/scripts/generate_thumbnail.py <TOML_PATH>
"""

import sys
import tomllib
import argparse
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("[ERROR] Pillow がインストールされていません。pip install pillow", file=sys.stderr)
    sys.exit(1)

THUMB_W, THUMB_H = 1280, 720

def load_font(size: int):
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

def draw_text_outlined(draw, pos, text, font, fill, outline_color=(0, 0, 0), outline_width=4):
    """縁取りテキスト描画"""
    x, y = pos
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    draw.text((x, y), text, font=font, fill=fill)

def main():
    parser = argparse.ArgumentParser(description="サムネイル生成")
    parser.add_argument("toml_path", help="台本TOMLファイルのパス")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    toml_path = Path(args.toml_path)
    if not toml_path.exists():
        print(f"[ERROR] TOMLファイルが見つかりません: {toml_path}", file=sys.stderr)
        sys.exit(1)

    script_dir = Path(__file__).parent.parent
    output_base = Path(args.output_dir) if args.output_dir else script_dir / "output"
    thumb_dir = output_base / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)

    assets_dir = script_dir / "assets"

    with open(toml_path, "rb") as f:
        script = tomllib.load(f)

    meta = script.get("meta", {})
    thumbnail_text = meta.get("thumbnail_text", meta.get("title", "ゆっくり解説"))
    title = meta.get("title", "")

    # 背景
    bg_path = assets_dir / "backgrounds" / "default.png"
    if bg_path.exists():
        bg = Image.open(bg_path).convert("RGB").resize((THUMB_W, THUMB_H))
        # ぼかして暗くする
        bg = bg.filter(ImageFilter.GaussianBlur(radius=4))
        overlay = Image.new("RGBA", (THUMB_W, THUMB_H), (0, 0, 30, 160))
        bg = bg.convert("RGBA")
        bg = Image.alpha_composite(bg, overlay).convert("RGB")
    else:
        bg = Image.new("RGB", (THUMB_W, THUMB_H), (15, 15, 50))

    # 立ち絵（右側に配置）
    chara_path = assets_dir / "characters" / "reimu.png"
    if chara_path.exists():
        chara = Image.open(chara_path).convert("RGBA")
        h = min(680, chara.height)
        ratio = h / chara.height
        w = int(chara.width * ratio)
        chara = chara.resize((w, h), Image.LANCZOS)
        bg.paste(chara, (THUMB_W - w - 40, THUMB_H - h), chara)

    draw = ImageDraw.Draw(bg)

    # メインテキスト（thumbnail_text）
    lines = thumbnail_text.split("\n")
    font_main = load_font(110 if len(lines) == 1 else 90)
    y = 80
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_main)
        line_w = bbox[2] - bbox[0]
        x = min(60, (THUMB_W - line_w) // 2)
        draw_text_outlined(draw, (x, y), line, font_main,
                           fill=(255, 230, 50), outline_color=(20, 0, 0), outline_width=6)
        y += (bbox[3] - bbox[1]) + 20

    # サブタイトル（title の最初の40文字）
    if title:
        sub = title[:40] + ("..." if len(title) > 40 else "")
        font_sub = load_font(36)
        draw_text_outlined(draw, (60, THUMB_H - 90), sub, font_sub,
                           fill=(220, 220, 220), outline_color=(0, 0, 0), outline_width=3)

    # 「ゆっくり解説」バッジ
    badge_font = load_font(32)
    badge_text = "ゆっくり解説"
    badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_w = badge_bbox[2] - badge_bbox[0] + 30
    badge_h = badge_bbox[3] - badge_bbox[1] + 16
    badge_x, badge_y = 60, THUMB_H - 90 - badge_h - 16
    draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
                            radius=8, fill=(200, 50, 50))
    draw.text((badge_x + 15, badge_y + 8), badge_text, font=badge_font, fill=(255, 255, 255))

    # 保存
    out_path = thumb_dir / "thumbnail.png"
    bg.save(out_path, "PNG")

    print(f"[完了] Luca からの報告: サムネイル生成 → {out_path}")

if __name__ == "__main__":
    main()
