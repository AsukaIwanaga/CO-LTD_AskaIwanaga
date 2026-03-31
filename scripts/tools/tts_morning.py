#!/usr/bin/env python3
"""
tts_morning.py — VOICEVOX で朝のブリーフィングを音声化・再生・保存する

使い方:
  python3 scripts/tts_morning.py "読み上げテキスト"   # 引数として渡す
  echo "テキスト" | python3 scripts/tts_morning.py -  # stdin から読み込む
  python3 scripts/tts_morning.py --text-only "テキスト"  # 正規化テキストのみ出力（VOICEVOX 不要）

VOICEVOX エンジンが起動している必要があります（http://localhost:50021）
声: 青山龍星 ノーマル（speaker ID: 13）

【朝のブリーフィングにおける TTS フロー】
1. Claude がブリーフィング内容を自然な日本語話し言葉に変換した「読み上げ文」を生成する
2. その文章を引数または stdin でこのスクリプトに渡す
3. VOICEVOX で音声合成 → MP3 変換 → iCloud コピー → 再生
"""

import json
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

VOICEVOX_BASE = "http://localhost:50021"
SPEAKER_ID = 11  # 玄野武宏 ノーマル（青山龍星=13 は高すぎとのフィードバックで変更）
VOICEVOX_APP = "/Applications/VOICEVOX.app"


def ensure_voicevox() -> None:
    """VOICEVOX エンジンが起動していなければ起動し、準備完了まで待つ。"""
    for _ in range(2):
        try:
            urllib.request.urlopen(f"{VOICEVOX_BASE}/version", timeout=2)
            return  # 起動済み
        except Exception:
            pass

    print("[TTS] VOICEVOX が起動していません。起動します...", file=sys.stderr)
    subprocess.Popen(["open", VOICEVOX_APP])

    for i in range(30):
        time.sleep(2)
        try:
            urllib.request.urlopen(f"{VOICEVOX_BASE}/version", timeout=2)
            print("[TTS] VOICEVOX エンジン準備完了。", file=sys.stderr)
            return
        except Exception:
            print(f"[TTS] 待機中... ({(i+1)*2}秒)", file=sys.stderr)

    print("[ERROR] VOICEVOX の起動がタイムアウトしました。", file=sys.stderr)
    sys.exit(1)

# 朝のブリーフィングに出現しやすい英語 → カタカナ辞書
EN_TO_KANA: dict[str, str] = {
    # 人名・固有名
    "Don": "ドン",
    # 優先度
    "HIGH": "ハイ", "MEDIUM": "ミディアム", "LOW": "ロー",
    # タグ
    "WORK": "ワーク", "LIFE": "ライフ", "HEALTH": "ヘルス", "MONEY": "マネー",
    # 習慣
    "ENG": "イング",
    # 金融
    "BTC": "ビットコイン", "ETF": "イーティーエフ", "NYダウ": "ニューヨークダウ",
    # 曜日
    "Mon": "月曜", "Tue": "火曜", "Wed": "水曜", "Thu": "木曜",
    "Fri": "金曜", "Sat": "土曜", "Sun": "日曜",
    # その他よく出る単語
    "OK": "オーケー", "AM": "エーエム", "PM": "ピーエム",
    "ONCE": "ワンス", "DAILY": "デイリー", "WEEKLY": "ウィークリー",
}

# アルファベット1文字の読み（辞書にない単語のフォールバック用）
_ALPHA_READ = {
    "A": "エー", "B": "ビー", "C": "シー", "D": "ディー", "E": "イー",
    "F": "エフ", "G": "ジー", "H": "エイチ", "I": "アイ", "J": "ジェー",
    "K": "ケー", "L": "エル", "M": "エム", "N": "エヌ", "O": "オー",
    "P": "ピー", "Q": "キュー", "R": "アール", "S": "エス", "T": "ティー",
    "U": "ユー", "V": "ブイ", "W": "ダブリュー", "X": "エックス",
    "Y": "ワイ", "Z": "ゼット",
}


def _en_word_to_kana(word: str) -> str:
    """英単語をカタカナに変換する。辞書にあればそれを、なければ1文字ずつ読む。"""
    if word in EN_TO_KANA:
        return EN_TO_KANA[word]
    upper = word.upper()
    if upper in EN_TO_KANA:
        return EN_TO_KANA[upper]
    # フォールバック: 大文字で1文字ずつ
    return "".join(_ALPHA_READ.get(c, c) for c in upper)


def normalize_for_tts(text: str) -> str:
    """TTS 読み上げ用にテキストを正規化する。"""
    # 英字のみの単語（数字混在も含む）をカタカナに置換
    def replace_en(m: re.Match) -> str:
        word = m.group(0)
        # 数字のみはそのまま
        if word.isdigit():
            return word
        return _en_word_to_kana(word)

    text = re.sub(r"[A-Za-z]+", replace_en, text)
    # 英語変換後の余分な空白を除去
    text = re.sub(r" +", "", text)
    return text

DRAFTS_DIR = Path(__file__).parent.parent / "drafts"
DRAFTS_DIR.mkdir(exist_ok=True)

ICLOUD_DIR = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/morning_reports"


def synthesize(text: str) -> Path:
    """VOICEVOX で音声合成し、wav ファイルパスを返す。"""
    # audio_query
    params = urllib.parse.urlencode({"text": text, "speaker": SPEAKER_ID})
    req = urllib.request.Request(f"{VOICEVOX_BASE}/audio_query?{params}", method="POST")
    with urllib.request.urlopen(req) as r:
        query = json.load(r)

    # synthesis
    data = json.dumps(query).encode()
    req2 = urllib.request.Request(
        f"{VOICEVOX_BASE}/synthesis?speaker={SPEAKER_ID}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req2) as r:
        audio = r.read()

    date_str = datetime.now().strftime("%Y-%m-%d")
    out_path = DRAFTS_DIR / f"morning_audio_{date_str}.wav"
    out_path.write_bytes(audio)
    return out_path


def to_mp3(wav_path: Path) -> Path:
    """ffmpeg で WAV → MP3 に変換する。ffmpeg がなければ WAV をそのまま返す。"""
    mp3_path = wav_path.with_suffix(".mp3")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("[WARNING] ffmpeg が見つかりません。WAV のまま使用します。", file=sys.stderr)
        return wav_path
    result = subprocess.run(
        [ffmpeg, "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-qscale:a", "2", str(mp3_path)],
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"[WARNING] MP3変換失敗: {result.stderr.decode()}", file=sys.stderr)
        return wav_path
    print(f"[TTS] MP3変換完了: {mp3_path}")
    return mp3_path


def copy_to_icloud(src: Path) -> None:
    """iCloud Drive の morning_reports フォルダにコピーする。"""
    try:
        ICLOUD_DIR.mkdir(parents=True, exist_ok=True)
        dest = ICLOUD_DIR / src.name
        shutil.copy2(src, dest)
        print(f"[iCloud] コピー完了: {dest}")
    except Exception as e:
        print(f"[WARNING] iCloud コピー失敗: {e}", file=sys.stderr)


def play(path: Path) -> None:
    """afplay で音声を再生する。"""
    subprocess.run(["afplay", str(path)], check=True)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="VOICEVOX TTS 読み上げ")
    parser.add_argument("text", nargs="?", default=None,
                        help="読み上げテキスト。\"-\" を指定すると stdin から読み込む")
    parser.add_argument("--text-only", action="store_true",
                        help="正規化済みテキストを stdout に出力するだけで音声合成しない")
    parser.add_argument("--no-play", action="store_true",
                        help="音声合成・保存はするが再生しない（MTG中など）")
    args = parser.parse_args()

    if args.text == "-" or args.text is None and not sys.stdin.isatty():
        text = sys.stdin.read()
    elif args.text:
        text = args.text
    else:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if not text.strip():
        print("[ERROR] テキストが空です。", file=sys.stderr)
        sys.exit(1)

    text = normalize_for_tts(text)

    if args.text_only:
        print(text)
        return

    ensure_voicevox()
    print("[TTS] 音声を生成中...")
    wav_path = synthesize(text)
    print(f"[TTS] 保存完了: {wav_path}")

    mp3_path = to_mp3(wav_path)
    copy_to_icloud(mp3_path)

    if args.no_play:
        print(f"[TTS] 完了（再生スキップ）。MP3: {mp3_path}")
    else:
        print("[TTS] 再生中...")
        play(wav_path)
        print(f"[TTS] 完了。MP3: {mp3_path}")


if __name__ == "__main__":
    main()
