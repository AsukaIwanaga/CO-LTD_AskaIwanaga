#!/usr/bin/env python3
"""
Luca Brasi — スライド画像・立ち絵切り替えマップ生成
Usage: python3 studio/scripts/build_slides.py <TOML_PATH>
"""

import sys
import json
import tomllib
import argparse
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("[ERROR] Pillow がインストールされていません。", file=sys.stderr)
    print("  pip install pillow", file=sys.stderr)
    sys.exit(1)

# スライドサイズ
SLIDE_W, SLIDE_H = 1920, 1080

# 立ち絵エリア（左: reimu, 右: marisa）
CHARA_LEFT_X   = 120
CHARA_RIGHT_X  = 1920 - 120 - 500  # 右端から500px
CHARA_Y        = 1080 - 900         # 下端合わせ

# テキストエリア（下部バー）
TEXT_BAR_H     = 220
TEXT_BAR_Y     = SLIDE_H - TEXT_BAR_H
TEXT_PADDING   = 60
TEXT_FONT_SIZE = 46
NAME_FONT_SIZE = 38

# キャラクター名表示色
SPEAKER_COLORS = {
    "reimu":  (255, 100, 100),   # 赤系（霊夢）
    "marisa": (255, 220,  60),   # 黄系（魔理沙）
}
SPEAKER_NAMES = {
    "reimu":  "霊夢",
    "marisa": "魔理沙",
}

def load_font(size: int):
    """利用可能なフォントをロード（macOS優先）"""
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode MS.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

def wrap_text(text: str, font, max_width: int, draw: ImageDraw) -> list[str]:
    """テキストを指定幅で折り返す"""
    lines = []
    current = ""
    for char in text:
        test = current + char
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines

def draw_slide(
    bg_image: Image.Image,
    chara_reimu: Image.Image | None,
    chara_marisa: Image.Image | None,
    speaker: str,
    text: str,
    slide_no: int,
    total: int,
) -> Image.Image:
    img = bg_image.copy().resize((SLIDE_W, SLIDE_H))
    draw = ImageDraw.Draw(img)

    # 立ち絵描画（発話者を明るく、非発話者を暗く）
    def draw_character(chara: Image.Image | None, x: int, active: bool):
        if chara is None:
            return
        # 立ち絵を最大高 900px にリサイズ
        h = min(900, chara.height)
        ratio = h / chara.height
        w = int(chara.width * ratio)
        chara_resized = chara.resize((w, h), Image.LANCZOS)
        if not active:
            # 非発話者は透過度を下げてグレーアウト
            overlay = Image.new("RGBA", chara_resized.size, (0, 0, 0, 80))
            chara_resized = Image.alpha_composite(chara_resized.convert("RGBA"), overlay)
        paste_y = SLIDE_H - h
        img.paste(chara_resized, (x, paste_y), chara_resized if chara_resized.mode == "RGBA" else None)

    draw_character(chara_reimu,  CHARA_LEFT_X,  speaker == "reimu")
    draw_character(chara_marisa, CHARA_RIGHT_X, speaker == "marisa")

    # テキストバー背景（半透明ブラック）
    bar_overlay = Image.new("RGBA", (SLIDE_W, TEXT_BAR_H), (0, 0, 0, 180))
    img.paste(bar_overlay, (0, TEXT_BAR_Y), bar_overlay)

    # キャラクター名
    name_font = load_font(NAME_FONT_SIZE)
    name_color = SPEAKER_COLORS.get(speaker, (255, 255, 255))
    name_text = SPEAKER_NAMES.get(speaker, speaker)
    draw.text((TEXT_PADDING, TEXT_BAR_Y + 16), name_text, font=name_font, fill=name_color)

    # セリフ本文
    text_font = load_font(TEXT_FONT_SIZE)
    max_text_w = SLIDE_W - TEXT_PADDING * 2
    wrapped = wrap_text(text, text_font, max_text_w, draw)
    text_y = TEXT_BAR_Y + NAME_FONT_SIZE + 28
    for line in wrapped[:3]:  # 最大3行
        draw.text((TEXT_PADDING, text_y), line, font=text_font, fill=(255, 255, 255))
        text_y += TEXT_FONT_SIZE + 8

    # スライド番号
    num_font = load_font(24)
    draw.text((SLIDE_W - 100, SLIDE_H - 36), f"{slide_no}/{total}", font=num_font, fill=(180, 180, 180))

    return img

def main():
    parser = argparse.ArgumentParser(description="スライド画像・立ち絵マップ生成")
    parser.add_argument("toml_path", help="台本TOMLファイルのパス")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    toml_path = Path(args.toml_path)
    if not toml_path.exists():
        print(f"[ERROR] TOMLファイルが見つかりません: {toml_path}", file=sys.stderr)
        sys.exit(1)

    script_dir = Path(__file__).parent.parent  # studio/
    output_base = Path(args.output_dir) if args.output_dir else script_dir / "output"
    slides_dir = output_base / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    assets_dir = script_dir / "assets"

    # 素材ロード
    bg_path = assets_dir / "backgrounds" / "default.png"
    if bg_path.exists():
        bg_image = Image.open(bg_path).convert("RGB")
    else:
        # デフォルト背景（グラデーション風）
        bg_image = Image.new("RGB", (SLIDE_W, SLIDE_H), (20, 20, 40))
        print(f"[WARN] 背景画像が見つかりません: {bg_path} — デフォルト背景を使用")

    def load_chara(name: str) -> Image.Image | None:
        for ext in ("png", "PNG"):
            p = assets_dir / "characters" / f"{name}.{ext}"
            if p.exists():
                return Image.open(p).convert("RGBA")
        print(f"[WARN] 立ち絵が見つかりません: {name} — スキップ")
        return None

    chara_reimu  = load_chara("reimu")
    chara_marisa = load_chara("marisa")

    # TOML 読み込み
    with open(toml_path, "rb") as f:
        script = tomllib.load(f)

    lines = script.get("lines", [])
    print(f"[INFO] スライド生成: {len(lines)} 枚")

    character_map = []  # [{slide_no, speaker, start_line}]

    for i, line in enumerate(lines):
        speaker = line.get("speaker", "reimu")
        text = line.get("text", "").strip()
        slide_no = i + 1

        img = draw_slide(bg_image, chara_reimu, chara_marisa, speaker, text, slide_no, len(lines))

        out_path = slides_dir / f"slide_{slide_no:03d}.png"
        img.save(out_path, "PNG")

        character_map.append({
            "slide_no": slide_no,
            "speaker":  speaker,
            "scene":    line.get("scene", "main"),
        })

        if slide_no % 10 == 0 or slide_no == len(lines):
            print(f"  {slide_no}/{len(lines)} 枚完了")

    # 立ち絵切り替えマップ保存
    map_path = slides_dir / "character_map.json"
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(character_map, f, ensure_ascii=False, indent=2)

    print(f"\n[完了] Luca からの報告:")
    print(f"  スライド {len(lines)} 枚 → {slides_dir}")
    print(f"  立ち絵マップ → {map_path}")

if __name__ == "__main__":
    main()
