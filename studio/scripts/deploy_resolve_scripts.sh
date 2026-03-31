#!/bin/bash
# Al Neri — resolve_scripts を DaVinci Resolve の Scripts フォルダにデプロイ

RESOLVE_SCRIPTS_DIR="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp"
SRC_DIR="$(dirname "$0")/../resolve_scripts"

mkdir -p "$RESOLVE_SCRIPTS_DIR"

cp "$SRC_DIR/build_timeline.py" "$RESOLVE_SCRIPTS_DIR/build_timeline.py"
cp "$SRC_DIR/export_video.py"   "$RESOLVE_SCRIPTS_DIR/export_video.py"

echo "[完了] Resolve Scripts にデプロイしました:"
echo "  $RESOLVE_SCRIPTS_DIR/build_timeline.py"
echo "  $RESOLVE_SCRIPTS_DIR/export_video.py"
echo ""
echo "DaVinci Resolve → ワークスペース → スクリプト から実行できます。"
