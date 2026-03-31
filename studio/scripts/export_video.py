#!/usr/bin/env python3
"""
Al Neri — DaVinci Resolve エクスポート
Usage: python3 studio/scripts/export_video.py [--project-name NAME] [--output-dir DIR]

DaVinci Resolve で現在開いているプロジェクトを H.264 / 1080p / YouTube向けで書き出す。
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

def get_resolve():
    try:
        import DaVinciResolveScript as dvr
        resolve = dvr.scriptapp("Resolve")
        if resolve is None:
            raise RuntimeError("DaVinci Resolve に接続できません。")
        return resolve
    except ImportError:
        print("[ERROR] DaVinciResolveScript モジュールが見つかりません。", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="DaVinci Resolve エクスポート")
    parser.add_argument("--output-dir", default=None, help="MP4出力先ディレクトリ")
    parser.add_argument("--filename", default=None, help="出力ファイル名（拡張子なし）")
    args = parser.parse_args()

    script_dir = Path(__file__).parent.parent.resolve()
    output_base = Path(args.output_dir).resolve() if args.output_dir else script_dir / "output"
    output_base.mkdir(parents=True, exist_ok=True)

    resolve = get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    if project is None:
        print("[ERROR] 現在のプロジェクトを取得できません。", file=sys.stderr)
        sys.exit(1)

    project_name = project.GetName()
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = args.filename or f"{date_str}_{project_name}"
    # ファイル名に使えない文字を除去
    for ch in r'/\:*?"<>|':
        filename = filename.replace(ch, "_")

    output_path = output_base / f"{filename}.mp4"

    print(f"[INFO] プロジェクト: {project_name}")
    print(f"[INFO] 出力先: {output_path}")

    # レンダー設定（YouTube向け H.264）
    render_settings = {
        "SelectAllFrames":   True,
        "TargetDir":         str(output_base),
        "CustomName":        filename,
        "ExportVideo":       True,
        "ExportAudio":       True,
        "FormatWidth":       1920,
        "FormatHeight":      1080,
        "FrameRate":         "30",
        "PixelAspectRatio":  "Square",
        "VideoQuality":      0,          # 0 = Automatic
        "AudioCodec":        "aac",
        "AudioBitDepth":     "16",
        "AudioSampleRate":   "48000",
        "ColorSpaceTag":     "Same as Project",
        "GammaTag":          "Same as Project",
    }

    # YouTube プリセットを設定
    project.LoadRenderPreset("YouTube - 1080p")

    project.SetRenderSettings(render_settings)

    # レンダーキューに追加
    project.ClearRenderQueue()
    job_id = project.AddRenderJob()
    if not job_id:
        print("[ERROR] レンダージョブの追加に失敗しました。", file=sys.stderr)
        sys.exit(1)

    print("[INFO] レンダリング開始...")
    project.StartRendering(job_id)

    # 完了待機
    while project.IsRenderingInProgress():
        status = project.GetRenderJobStatus(job_id)
        progress = status.get("CompletionPercentage", 0)
        print(f"\r  進捗: {progress:.0f}%", end="", flush=True)
        time.sleep(2)

    print("\r  進捗: 100%")

    # 結果確認
    status = project.GetRenderJobStatus(job_id)
    if status.get("JobStatus") == "Complete":
        print(f"\n[完了] Al Neri: エクスポート完了しました → {output_path}")
    else:
        error = status.get("Error", "不明なエラー")
        print(f"\n[ERROR] レンダリング失敗: {error}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
