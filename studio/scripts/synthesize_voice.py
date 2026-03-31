#!/usr/bin/env python3
"""
Johnny Fontane — VOICEVOX音声合成 + SRT字幕生成
Usage: python3 studio/scripts/synthesize_voice.py <TOML_PATH>
"""

import sys
import json
import time
import struct
import tomllib
import requests
import argparse
from pathlib import Path

VOICEVOX_URL = "http://localhost:50021"

# speaker ID マッピング
SPEAKER_IDS = {
    "reimu":   2,   # 四国めたん（ノーマル）
    "marisa":  3,   # ずんだもん（ノーマル）
}

def check_voicevox() -> bool:
    try:
        r = requests.get(f"{VOICEVOX_URL}/version", timeout=3)
        return r.status_code == 200
    except Exception:
        return False

def synthesize(text: str, speaker_id: int) -> bytes:
    """VOICEVOX APIで音声合成し、WAVバイト列を返す"""
    # STEP 1: audio_query
    r = requests.post(
        f"{VOICEVOX_URL}/audio_query",
        params={"text": text, "speaker": speaker_id},
        timeout=30,
    )
    r.raise_for_status()
    query = r.json()

    # STEP 2: synthesis
    r = requests.post(
        f"{VOICEVOX_URL}/synthesis",
        params={"speaker": speaker_id},
        json=query,
        timeout=60,
    )
    r.raise_for_status()
    return r.content  # WAVバイト列

def get_wav_duration(wav_bytes: bytes) -> float:
    """WAVバイト列から再生時間（秒）を取得"""
    # WAVヘッダー解析: fmt チャンク
    # RIFF header: 4 + 4 + 4 = 12 bytes
    # fmt chunk: 4(id) + 4(size) + 2(format) + 2(ch) + 4(srate) + 4(brate) + 2(balign) + 2(bits)
    try:
        sample_rate = struct.unpack_from("<I", wav_bytes, 24)[0]
        num_channels = struct.unpack_from("<H", wav_bytes, 22)[0]
        bits_per_sample = struct.unpack_from("<H", wav_bytes, 34)[0]
        # data チャンクを探す
        pos = 12
        while pos < len(wav_bytes) - 8:
            chunk_id = wav_bytes[pos:pos+4]
            chunk_size = struct.unpack_from("<I", wav_bytes, pos+4)[0]
            if chunk_id == b"data":
                num_samples = chunk_size // (num_channels * (bits_per_sample // 8))
                return num_samples / sample_rate
            pos += 8 + chunk_size
    except Exception:
        pass
    return 0.0

def format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def main():
    parser = argparse.ArgumentParser(description="VOICEVOX音声合成 + SRT字幕生成")
    parser.add_argument("toml_path", help="台本TOMLファイルのパス")
    parser.add_argument("--output-dir", default=None, help="出力ディレクトリ（デフォルト: studio/output）")
    args = parser.parse_args()

    toml_path = Path(args.toml_path)
    if not toml_path.exists():
        print(f"[ERROR] TOMLファイルが見つかりません: {toml_path}", file=sys.stderr)
        sys.exit(1)

    # 出力ディレクトリ設定
    script_dir = Path(__file__).parent.parent  # studio/
    output_base = Path(args.output_dir) if args.output_dir else script_dir / "output"
    audio_dir = output_base / "audio"
    subtitle_dir = output_base / "subtitles"
    audio_dir.mkdir(parents=True, exist_ok=True)
    subtitle_dir.mkdir(parents=True, exist_ok=True)

    # VOICEVOX 起動確認
    if not check_voicevox():
        print("[ERROR] VOICEVOXエンジンが起動していません。", file=sys.stderr)
        print("  起動してから再実行してください。", file=sys.stderr)
        sys.exit(1)
    print(f"[OK] VOICEVOX エンジン接続確認")

    # TOML 読み込み
    with open(toml_path, "rb") as f:
        script = tomllib.load(f)

    lines = script.get("lines", [])
    if not lines:
        print("[ERROR] 台本に lines が見つかりません", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] 台本: {script.get('meta', {}).get('title', toml_path.stem)}")
    print(f"[INFO] セリフ数: {len(lines)} 行")

    # タイムライン情報（SRT + キャラクターマップ用）
    timeline = []   # [{line_no, speaker, text, start, end, wav_path}]
    current_time = 0.0

    for i, line in enumerate(lines):
        speaker = line.get("speaker", "reimu")
        text = line.get("text", "").strip()
        if not text:
            continue

        speaker_id = SPEAKER_IDS.get(speaker, 2)
        line_no = i + 1
        wav_filename = f"line_{line_no:03d}.wav"
        wav_path = audio_dir / wav_filename

        print(f"  [{line_no:03d}] {speaker}: {text[:30]}{'...' if len(text) > 30 else ''}", end="", flush=True)

        wav_bytes = synthesize(text, speaker_id)
        duration = get_wav_duration(wav_bytes)

        with open(wav_path, "wb") as f:
            f.write(wav_bytes)

        print(f" → {duration:.2f}s")

        start_time = current_time
        end_time = current_time + duration
        timeline.append({
            "line_no":   line_no,
            "speaker":   speaker,
            "text":      text,
            "scene":     line.get("scene", "main"),
            "start":     start_time,
            "end":       end_time,
            "duration":  duration,
            "wav_path":  str(wav_path),
        })
        current_time = end_time

        # API 負荷軽減のため微小待機
        time.sleep(0.1)

    # SRT 字幕生成
    srt_name = toml_path.stem + ".srt"
    srt_path = subtitle_dir / srt_name
    with open(srt_path, "w", encoding="utf-8") as f:
        for idx, item in enumerate(timeline, 1):
            f.write(f"{idx}\n")
            f.write(f"{format_srt_time(item['start'])} --> {format_srt_time(item['end'])}\n")
            f.write(f"{item['text']}\n\n")

    # タイムライン JSON 保存（build_timeline.py が参照）
    timeline_path = output_base / "timeline.json"
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2)

    # current_job.json 保存（Resolve 内部スクリプトが参照）
    job_info = {
        "toml_stem": toml_path.stem,
        "title": script.get("meta", {}).get("title", toml_path.stem),
        "toml_path": str(toml_path.resolve()),
    }
    job_path = output_base / "current_job.json"
    with open(job_path, "w", encoding="utf-8") as f:
        json.dump(job_info, f, ensure_ascii=False, indent=2)

    total_duration = current_time
    minutes = int(total_duration // 60)
    seconds = int(total_duration % 60)

    print(f"\n[完了] Johnny からの報告:")
    print(f"  音声ファイル: {len(timeline)} 件 → {audio_dir}")
    print(f"  字幕ファイル: {srt_path}")
    print(f"  タイムライン: {timeline_path}")
    print(f"  総尺: 約 {minutes}分{seconds}秒")

if __name__ == "__main__":
    main()
