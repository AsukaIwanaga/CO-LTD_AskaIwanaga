#!/usr/bin/env python3
"""
Al Neri — DaVinci Resolve エクスポート（Resolve内部実行版）

実行方法:
  DaVinci Resolve → ワークスペース → スクリプト → export_video

前提:
  - DaVinci Resolve が起動してプロジェクトが開かれていること
  - タイムラインが構築済みであること
"""

import json
import time
from pathlib import Path
from datetime import datetime

STUDIO_DIR = Path("/Users/askaiwanaga/CO-LTD_AskaIwanaga/studio")
OUTPUT_DIR = STUDIO_DIR / "output"


def main():
    resolve = fusion.GetResolve()  # noqa: F821
    if resolve is None:
        print("[ERROR] resolve の取得に失敗しました。")
        return

    project = resolve.GetProjectManager().GetCurrentProject()
    if project is None:
        print("[ERROR] 現在のプロジェクトを取得できません。")
        return

    project_name = project.GetName()
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}_{project_name}"
    for ch in r'/\:*?"<>|':
        filename = filename.replace(ch, "_")

    output_path = OUTPUT_DIR / f"{filename}.mp4"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] プロジェクト: {project_name}")
    print(f"[INFO] 出力先: {output_path}")

    # YouTube向け H.264 レンダー設定
    project.LoadRenderPreset("YouTube - 1080p")
    project.SetRenderSettings({
        "SelectAllFrames":  True,
        "TargetDir":        str(OUTPUT_DIR),
        "CustomName":       filename,
        "ExportVideo":      True,
        "ExportAudio":      True,
        "FormatWidth":      1920,
        "FormatHeight":     1080,
        "FrameRate":        "30",
        "PixelAspectRatio": "Square",
        "AudioCodec":       "aac",
        "AudioBitDepth":    "16",
        "AudioSampleRate":  "48000",
    })

    project.ClearRenderQueue()
    job_id = project.AddRenderJob()
    if not job_id:
        print("[ERROR] レンダージョブの追加に失敗しました。")
        return

    print("[INFO] レンダリング開始...")
    project.StartRendering(job_id)

    while project.IsRenderingInProgress():
        status = project.GetRenderJobStatus(job_id)
        progress = status.get("CompletionPercentage", 0)
        print(f"  進捗: {progress:.0f}%")
        time.sleep(3)

    status = project.GetRenderJobStatus(job_id)
    if status.get("JobStatus") == "Complete":
        print(f"\n[完了] Al Neri: エクスポート完了 → {output_path}")
    else:
        error = status.get("Error", "不明なエラー")
        print(f"\n[ERROR] レンダリング失敗: {error}")


main()
