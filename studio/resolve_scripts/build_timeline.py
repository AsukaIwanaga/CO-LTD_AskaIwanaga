#!/usr/bin/env python3
"""
Al Neri — DaVinci Resolve タイムライン構築（Resolve内部実行版）

実行方法:
  DaVinci Resolve → ワークスペース → スクリプト → build_timeline

前提:
  - DaVinci Resolve が起動してプロジェクトが開かれていること
  - studio/output/timeline.json (synthesize_voice.py の成果物)
  - studio/output/audio/line_*.wav
  - studio/output/slides/slide_*.png
  - studio/output/current_job.json (どの台本を使うか)
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# ベースディレクトリ（このスクリプトの場所から2階層上 = studio/）
STUDIO_DIR = Path("/Users/askaiwanaga/CO-LTD_AskaIwanaga/studio")
OUTPUT_DIR = STUDIO_DIR / "output"
FPS = 30


def frames(seconds: float) -> int:
    return int(seconds * FPS)


def main():
    # fusion は Resolve 内部実行時にグローバルで存在する
    resolve = fusion.GetResolve()  # noqa: F821
    if resolve is None:
        print("[ERROR] resolve の取得に失敗しました。プロジェクトが開かれているか確認してください。")
        return

    # current_job.json からジョブ情報を取得
    job_file = OUTPUT_DIR / "current_job.json"
    if not job_file.exists():
        print(f"[ERROR] current_job.json が見つかりません: {job_file}")
        print("  先に synthesize_voice.py と build_slides.py を実行してください。")
        return

    with open(job_file, encoding="utf-8") as f:
        job = json.load(f)

    toml_stem = job.get("toml_stem", "unknown")
    title = job.get("title", toml_stem)
    date_str = datetime.now().strftime("%Y-%m-%d")
    project_name = f"ゆっくり解説_{date_str}_{toml_stem}"

    # timeline.json 読み込み
    timeline_json = OUTPUT_DIR / "timeline.json"
    if not timeline_json.exists():
        print(f"[ERROR] timeline.json が見つかりません: {timeline_json}")
        return

    with open(timeline_json, encoding="utf-8") as f:
        timeline = json.load(f)

    audio_dir = OUTPUT_DIR / "audio"
    slides_dir = OUTPUT_DIR / "slides"
    subtitle_dir = OUTPUT_DIR / "subtitles"

    # 素材確認
    missing = []
    for item in timeline:
        if not Path(item["wav_path"]).exists():
            missing.append(item["wav_path"])
        slide = slides_dir / f"slide_{item['line_no']:03d}.png"
        if not slide.exists():
            missing.append(str(slide))

    if missing:
        print("[ERROR] 素材が不足しています:")
        for m in missing[:5]:
            print(f"  {m}")
        return

    total_duration = max(item["end"] for item in timeline)
    total_frames = frames(total_duration)

    print(f"[INFO] プロジェクト名: {project_name}")
    print(f"[INFO] 総尺: {total_duration:.1f}秒  セリフ数: {len(timeline)}")

    # プロジェクト作成
    project_manager = resolve.GetProjectManager()
    project = project_manager.CreateProject(project_name)
    if project is None:
        project = project_manager.LoadProject(project_name)
    if project is None:
        print("[ERROR] プロジェクトの作成・読み込みに失敗しました")
        return

    project.SetSetting("timelineFrameRate", str(FPS))
    project.SetSetting("timelineResolutionWidth", "1920")
    project.SetSetting("timelineResolutionHeight", "1080")

    media_pool = project.GetMediaPool()
    root_bin = media_pool.GetRootFolder()

    audio_bin = media_pool.AddSubFolder(root_bin, "Audio")
    slide_bin = media_pool.AddSubFolder(root_bin, "Slides")
    bg_bin    = media_pool.AddSubFolder(root_bin, "Backgrounds")
    bgm_bin   = media_pool.AddSubFolder(root_bin, "BGM")

    print("[INFO] 素材をメディアプールに読み込み中...")

    # 背景画像
    bg_path = STUDIO_DIR / "assets" / "backgrounds" / "default.png"
    media_pool.SetCurrentFolder(bg_bin)
    bg_clips = media_pool.ImportMedia([str(bg_path)]) if bg_path.exists() else []

    # BGM
    bgm_path = STUDIO_DIR / "assets" / "bgm" / "background_loop.mp3"
    media_pool.SetCurrentFolder(bgm_bin)
    bgm_clips = media_pool.ImportMedia([str(bgm_path)]) if bgm_path.exists() else []

    # スライド一括インポート
    slide_paths = [str(slides_dir / f"slide_{item['line_no']:03d}.png") for item in timeline]
    media_pool.SetCurrentFolder(slide_bin)
    slide_clips_list = media_pool.ImportMedia(slide_paths) or []
    slide_clip_map = {}
    for clip in slide_clips_list:
        if clip:
            fn = Path(clip.GetClipProperty("File Path")).name
            slide_clip_map[fn] = clip

    # WAV一括インポート
    wav_paths = [item["wav_path"] for item in timeline]
    media_pool.SetCurrentFolder(audio_bin)
    audio_clips_list = media_pool.ImportMedia(wav_paths) or []
    audio_clip_map = {}
    for clip in audio_clips_list:
        if clip:
            fn = Path(clip.GetClipProperty("File Path")).name
            audio_clip_map[fn] = clip

    # タイムライン作成
    print("[INFO] タイムライン構築中...")
    media_pool.SetCurrentFolder(root_bin)
    timeline_obj = media_pool.CreateEmptyTimeline(project_name)
    if timeline_obj is None:
        print("[ERROR] タイムラインの作成に失敗しました")
        return

    resolve.OpenPage("cut")

    # トラック追加: V1=背景 V2=スライド V3=立ち絵(将来用) / A1=セリフ A2=BGM
    timeline_obj.AddTrack("video")
    timeline_obj.AddTrack("video")
    timeline_obj.AddTrack("audio")

    # V1: 背景を全尺に配置
    if bg_clips:
        media_pool.AppendToTimeline([{
            "mediaPoolItem": bg_clips[0],
            "startFrame":    0,
            "endFrame":      total_frames,
            "trackIndex":    1,
            "recordFrame":   0,
        }])

    # V2 + A1: スライドと音声を同期配置
    for item in timeline:
        slide_fn = f"slide_{item['line_no']:03d}.png"
        wav_fn   = Path(item["wav_path"]).name
        s = frames(item["start"])
        e = frames(item["end"])
        dur = e - s
        if dur <= 0:
            continue

        slide_clip = slide_clip_map.get(slide_fn)
        audio_clip = audio_clip_map.get(wav_fn)

        if slide_clip:
            media_pool.AppendToTimeline([{
                "mediaPoolItem": slide_clip,
                "startFrame": 0, "endFrame": dur,
                "trackIndex": 2, "recordFrame": s,
            }])
        if audio_clip:
            media_pool.AppendToTimeline([{
                "mediaPoolItem": audio_clip,
                "startFrame": 0, "endFrame": dur,
                "trackIndex": 1, "recordFrame": s,
            }])

    # A2: BGM ループ配置
    if bgm_clips:
        bgm_clip = bgm_clips[0]
        bgm_props = bgm_clip.GetClipProperty()
        bgm_fps    = float(bgm_props.get("FPS", 30))
        bgm_frames = int(float(bgm_props.get("Duration", 300)) * bgm_fps)
        pos = 0
        while pos < total_frames:
            seg = min(bgm_frames, total_frames - pos)
            media_pool.AppendToTimeline([{
                "mediaPoolItem": bgm_clip,
                "startFrame": 0, "endFrame": seg,
                "trackIndex": 2, "recordFrame": pos,
            }])
            pos += bgm_frames

    # SRT字幕インポート
    srt_path = subtitle_dir / f"{toml_stem}.srt"
    if srt_path.exists():
        try:
            timeline_obj.ImportIntoTimeline(str(srt_path), {
                "timelineName": project_name,
                "importSourceClips": False,
            })
            print(f"[INFO] SRT字幕インポート完了: {srt_path.name}")
        except Exception as e:
            print(f"[WARN] SRT字幕インポートをスキップ: {e}")

    m = int(total_duration // 60)
    s = int(total_duration % 60)
    print(f"\n[完了] Al Neri: タイムライン構築完了")
    print(f"  プロジェクト名: {project_name}")
    print(f"  総尺: 約 {m}分{s}秒")


main()
