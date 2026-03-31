#!/usr/bin/env python3
"""
Al Neri — DaVinci Resolve タイムライン構築
Usage: python3 studio/scripts/build_timeline.py <TOML_PATH>

前提:
  - DaVinci Resolve 20 が起動していること
  - studio/output/audio/line_*.wav (synthesize_voice.py の成果物)
  - studio/output/slides/slide_*.png (build_slides.py の成果物)
  - studio/output/subtitles/*.srt
  - studio/output/timeline.json (synthesize_voice.py が生成するタイムデータ)
"""

import sys
import json
import tomllib
import argparse
from pathlib import Path
from datetime import datetime

def get_resolve():
    """DaVinci Resolve Python APIを取得"""
    try:
        import DaVinciResolveScript as dvr
        resolve = dvr.scriptapp("Resolve")
        if resolve is None:
            raise RuntimeError("DaVinci Resolve に接続できません。Resolve が起動しているか確認してください。")
        return resolve
    except ImportError:
        print("[ERROR] DaVinciResolveScript モジュールが見つかりません。", file=sys.stderr)
        print("  DaVinci Resolve 20 が起動していることを確認してください。", file=sys.stderr)
        print("  モジュールパス例: /Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules", file=sys.stderr)
        sys.exit(1)

def frames(seconds: float, fps: int = 30) -> int:
    return int(seconds * fps)

def main():
    parser = argparse.ArgumentParser(description="DaVinci Resolve タイムライン構築")
    parser.add_argument("toml_path", help="台本TOMLファイルのパス")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    toml_path = Path(args.toml_path).resolve()
    if not toml_path.exists():
        print(f"[ERROR] TOMLファイルが見つかりません: {toml_path}", file=sys.stderr)
        sys.exit(1)

    script_dir = Path(__file__).parent.parent.resolve()
    output_base = Path(args.output_dir).resolve() if args.output_dir else script_dir / "output"
    audio_dir    = output_base / "audio"
    slides_dir   = output_base / "slides"
    subtitle_dir = output_base / "subtitles"

    # タイムライン JSON
    timeline_json = output_base / "timeline.json"
    if not timeline_json.exists():
        print(f"[ERROR] timeline.json が見つかりません: {timeline_json}", file=sys.stderr)
        print("  先に synthesize_voice.py を実行してください。", file=sys.stderr)
        sys.exit(1)

    with open(timeline_json, encoding="utf-8") as f:
        timeline = json.load(f)

    # 素材確認
    missing = []
    for item in timeline:
        wav = Path(item["wav_path"])
        if not wav.exists():
            missing.append(str(wav))
        slide = slides_dir / f"slide_{item['line_no']:03d}.png"
        if not slide.exists():
            missing.append(str(slide))
    if missing:
        print("[ERROR] 素材が不足しています:", file=sys.stderr)
        for m in missing[:5]:
            print(f"  {m}", file=sys.stderr)
        sys.exit(1)

    # TOML 読み込み
    with open(toml_path, "rb") as f:
        script = tomllib.load(f)
    meta = script.get("meta", {})
    title = meta.get("title", toml_path.stem)
    date_str = datetime.now().strftime("%Y-%m-%d")
    project_name = f"ゆっくり解説_{date_str}_{toml_path.stem}"

    # 総尺
    total_duration = max(item["end"] for item in timeline)
    total_frames = frames(total_duration, args.fps)

    print(f"[INFO] プロジェクト名: {project_name}")
    print(f"[INFO] 総尺: {total_duration:.1f}秒 ({total_frames}フレーム @ {args.fps}fps)")
    print(f"[INFO] セリフ数: {len(timeline)}")

    # DaVinci Resolve 接続
    resolve = get_resolve()
    project_manager = resolve.GetProjectManager()

    # プロジェクト作成
    print(f"[INFO] プロジェクト作成: {project_name}")
    project = project_manager.CreateProject(project_name)
    if project is None:
        # 既存プロジェクトを開く
        project = project_manager.LoadProject(project_name)
        if project is None:
            print(f"[ERROR] プロジェクトの作成・読み込みに失敗しました", file=sys.stderr)
            sys.exit(1)

    # プロジェクト設定
    project.SetSetting("timelineFrameRate", str(args.fps))
    project.SetSetting("timelineResolutionWidth", "1920")
    project.SetSetting("timelineResolutionHeight", "1080")

    media_pool = project.GetMediaPool()
    root_bin = media_pool.GetRootFolder()

    # メディアプール: 素材フォルダ作成
    audio_bin = media_pool.AddSubFolder(root_bin, "Audio")
    slide_bin = media_pool.AddSubFolder(root_bin, "Slides")
    bg_bin    = media_pool.AddSubFolder(root_bin, "Backgrounds")
    bgm_bin   = media_pool.AddSubFolder(root_bin, "BGM")

    print("[INFO] 素材をメディアプールに読み込み中...")

    # 背景画像
    bg_path = script_dir / "assets" / "backgrounds" / "default.png"
    media_pool.SetCurrentFolder(bg_bin)
    bg_clips = media_pool.ImportMedia([str(bg_path)]) if bg_path.exists() else []

    # BGM
    bgm_path = script_dir / "assets" / "bgm" / "background_loop.mp3"
    media_pool.SetCurrentFolder(bgm_bin)
    bgm_clips = media_pool.ImportMedia([str(bgm_path)]) if bgm_path.exists() else []

    # スライド画像（一括インポート）
    slide_paths = [str(slides_dir / f"slide_{item['line_no']:03d}.png") for item in timeline]
    media_pool.SetCurrentFolder(slide_bin)
    slide_clips_list = media_pool.ImportMedia(slide_paths)
    # パスでクリップを引く辞書
    slide_clip_map = {}
    if slide_clips_list:
        for clip in slide_clips_list:
            if clip:
                fn = Path(clip.GetClipProperty("File Path")).name
                slide_clip_map[fn] = clip

    # WAV音声（一括インポート）
    wav_paths = [item["wav_path"] for item in timeline]
    media_pool.SetCurrentFolder(audio_bin)
    audio_clips_list = media_pool.ImportMedia(wav_paths)
    audio_clip_map = {}
    if audio_clips_list:
        for clip in audio_clips_list:
            if clip:
                fn = Path(clip.GetClipProperty("File Path")).name
                audio_clip_map[fn] = clip

    # タイムライン作成
    print("[INFO] タイムライン作成中...")
    media_pool.SetCurrentFolder(root_bin)
    timeline_obj = media_pool.CreateEmptyTimeline(project_name)
    if timeline_obj is None:
        print("[ERROR] タイムラインの作成に失敗しました", file=sys.stderr)
        sys.exit(1)

    resolve.OpenPage("cut")

    # トラック追加
    # V1: 背景, V2: スライド, V3: 立ち絵（将来用）
    # A1: セリフ, A2: BGM
    timeline_obj.AddTrack("video")  # V2
    timeline_obj.AddTrack("video")  # V3 (立ち絵用 - 将来)
    timeline_obj.AddTrack("audio")  # A2 (BGM)

    FPS = args.fps

    # V1: 背景を全尺に配置
    if bg_clips:
        bg_clip = bg_clips[0]
        media_pool.AppendToTimeline([{
            "mediaPoolItem": bg_clip,
            "startFrame":    0,
            "endFrame":      total_frames,
            "trackIndex":    1,
            "recordFrame":   0,
        }])

    # V2: スライド + A1: WAV を同期配置
    for item in timeline:
        slide_fn = f"slide_{item['line_no']:03d}.png"
        wav_fn   = Path(item["wav_path"]).name

        start_frame = frames(item["start"], FPS)
        end_frame   = frames(item["end"],   FPS)
        duration    = end_frame - start_frame

        if duration <= 0:
            continue

        slide_clip = slide_clip_map.get(slide_fn)
        audio_clip = audio_clip_map.get(wav_fn)

        if slide_clip:
            media_pool.AppendToTimeline([{
                "mediaPoolItem": slide_clip,
                "startFrame":    0,
                "endFrame":      duration,
                "trackIndex":    2,
                "recordFrame":   start_frame,
            }])

        if audio_clip:
            media_pool.AppendToTimeline([{
                "mediaPoolItem": audio_clip,
                "startFrame":    0,
                "endFrame":      duration,
                "trackIndex":    1,  # A1
                "recordFrame":   start_frame,
            }])

    # A2: BGM をループ配置（音量は後でフェードで調整）
    if bgm_clips:
        bgm_clip = bgm_clips[0]
        # BGMの尺を確認し、必要なら繰り返し配置
        bgm_props = bgm_clip.GetClipProperty()
        bgm_fps   = float(bgm_props.get("FPS", 30))
        bgm_frames = int(float(bgm_props.get("Duration", 300)) * bgm_fps)

        record_pos = 0
        while record_pos < total_frames:
            end_pos = min(record_pos + bgm_frames, total_frames)
            seg_len = end_pos - record_pos
            media_pool.AppendToTimeline([{
                "mediaPoolItem": bgm_clip,
                "startFrame":    0,
                "endFrame":      seg_len,
                "trackIndex":    2,  # A2
                "recordFrame":   record_pos,
            }])
            record_pos += bgm_frames

    # SRT字幕インポート
    srt_path = subtitle_dir / (toml_path.stem + ".srt")
    if srt_path.exists():
        try:
            timeline_obj.ImportIntoTimeline(str(srt_path), {
                "timelineName": project_name,
                "importSourceClips": False,
            })
            print(f"[INFO] SRT字幕インポート完了: {srt_path.name}")
        except Exception as e:
            print(f"[WARN] SRT字幕インポートをスキップ: {e}")

    minutes = int(total_duration // 60)
    seconds = int(total_duration % 60)

    print(f"\n[完了] Al Neri からの報告: タイムラインを構築しました。")
    print(f"  プロジェクト名: {project_name}")
    print(f"  総尺: 約 {minutes}分{seconds}秒")
    print(f"  DaVinci Resolve でご確認ください。")

if __name__ == "__main__":
    main()
