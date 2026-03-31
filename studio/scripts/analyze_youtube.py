#!/usr/bin/env python3
"""
Moe Greene — YouTube Data API v3 分析レポート生成
Usage: python3 studio/scripts/analyze_youtube.py [--channel-id ID] [--video-id ID]

環境変数:
  YOUTUBE_API_KEY  — YouTube Data API v3 キー
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"

def get_api_key() -> str:
    key = os.getenv("YOUTUBE_API_KEY", "")
    if not key:
        print("[ERROR] YOUTUBE_API_KEY 環境変数が設定されていません。", file=sys.stderr)
        sys.exit(1)
    return key

def api_get(endpoint: str, params: dict) -> dict:
    r = requests.get(f"{YOUTUBE_API_BASE}/{endpoint}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def get_channel_videos(api_key: str, channel_id: str, max_results: int = 10) -> list:
    """チャンネルの動画一覧を取得"""
    data = api_get("search", {
        "key":        api_key,
        "channelId":  channel_id,
        "part":       "id,snippet",
        "order":      "date",
        "maxResults": max_results,
        "type":       "video",
    })
    return [item for item in data.get("items", []) if item.get("id", {}).get("kind") == "youtube#video"]

def get_video_stats(api_key: str, video_ids: list[str]) -> dict:
    """動画の統計情報を取得"""
    ids = ",".join(video_ids)
    data = api_get("videos", {
        "key":  api_key,
        "id":   ids,
        "part": "statistics,snippet,contentDetails",
    })
    return {item["id"]: item for item in data.get("items", [])}

def get_analytics(api_key: str, video_id: str) -> dict:
    """
    YouTube Analytics API (別エンドポイント) は OAuth が必要なため、
    Data API v3 の statistics を代替として使用。
    CTR・視聴維持率は Analytics API / Studio のみ取得可。
    """
    data = api_get("videos", {
        "key":  api_key,
        "id":   video_id,
        "part": "statistics,contentDetails,snippet",
    })
    items = data.get("items", [])
    return items[0] if items else {}

def format_duration(iso: str) -> str:
    """ISO 8601 duration を MM:SS に変換"""
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return iso
    h = int(m.group(1) or 0)
    mins = int(m.group(2) or 0)
    secs = int(m.group(3) or 0)
    total_secs = h * 3600 + mins * 60 + secs
    mm = total_secs // 60
    ss = total_secs % 60
    return f"{mm}:{ss:02d}"

def main():
    parser = argparse.ArgumentParser(description="YouTube分析レポート生成")
    parser.add_argument("--channel-id", default=os.getenv("YOUTUBE_CHANNEL_ID", ""), help="YouTubeチャンネルID")
    parser.add_argument("--video-id",   default="", help="単一動画ID（指定すると1本のみ分析）")
    parser.add_argument("--output",     default=None, help="レポートJSON保存先")
    parser.add_argument("--max",        type=int, default=5, help="分析動画数（デフォルト: 5）")
    args = parser.parse_args()

    api_key = get_api_key()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    videos_data = []

    if args.video_id:
        item = get_analytics(api_key, args.video_id)
        if item:
            videos_data = [item]
        else:
            print(f"[ERROR] 動画 {args.video_id} が見つかりません", file=sys.stderr)
            sys.exit(1)
    elif args.channel_id:
        print(f"[INFO] チャンネル {args.channel_id} の動画を取得中...")
        search_items = get_channel_videos(api_key, args.channel_id, args.max)
        video_ids = [item["id"]["videoId"] for item in search_items]
        stats_map = get_video_stats(api_key, video_ids)
        videos_data = list(stats_map.values())
    else:
        print("[ERROR] --channel-id または --video-id を指定してください。", file=sys.stderr)
        print("  環境変数 YOUTUBE_CHANNEL_ID も使用できます。", file=sys.stderr)
        sys.exit(1)

    # レポート生成
    report_lines = []
    report_lines.append(f"📊 YouTube分析レポート — {now_str}")
    report_lines.append("─" * 65)

    for video in videos_data:
        snippet = video.get("snippet", {})
        stats   = video.get("statistics", {})
        content = video.get("contentDetails", {})

        title     = snippet.get("title", "不明")[:50]
        vid_id    = video.get("id", "")
        views     = int(stats.get("viewCount", 0))
        likes     = int(stats.get("likeCount", 0))
        comments  = int(stats.get("commentCount", 0))
        duration  = format_duration(content.get("duration", "PT0S"))
        pub_date  = snippet.get("publishedAt", "")[:10]

        report_lines.append(f"\n動画: {title}")
        report_lines.append(f"  ID:       {vid_id}")
        report_lines.append(f"  公開日:   {pub_date}")
        report_lines.append(f"  尺:       {duration}")
        report_lines.append(f"  視聴回数: {views:,} 回")
        report_lines.append(f"  いいね:   {likes:,}")
        report_lines.append(f"  コメント: {comments:,}")

        # エンゲージメント率（いいね / 視聴数）
        if views > 0:
            eng_rate = likes / views * 100
            report_lines.append(f"  ENG率:    {eng_rate:.2f}%")

        # CTR・視聴維持率は YouTube Studio / Analytics API でのみ取得可
        report_lines.append(f"  CTR:      YouTube Studio で確認してください")
        report_lines.append(f"  平均視聴率: YouTube Studio Analytics で確認")

    # 改善提案
    report_lines.append("\n" + "─" * 65)
    report_lines.append("改善提案（一般論ベース）:")
    report_lines.append("・タイトルに「2026年版」「速報」等の時事性を追加する")
    report_lines.append("・サムネイルにテキストを大きく、コントラストを強くする")
    report_lines.append("・最初の30秒でテーマを明確に提示してドロップを防ぐ")
    report_lines.append("・動画末尾に次回予告・チャンネル登録CTAを入れる")

    report_text = "\n".join(report_lines)
    print(report_text)

    # JSON保存
    script_dir = Path(__file__).parent.parent
    output_path = args.output or str(script_dir / "output" / "analytics_report.json")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now_str,
            "videos":       videos_data,
            "report":       report_text,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n[完了] Moe Greene からの報告: 分析レポートを保存しました → {output_path}")

if __name__ == "__main__":
    main()
