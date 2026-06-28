#!/bin/bash
# render.sh — Called by Python orchestrator via subprocess
# Usage: ./render.sh <spec_path> <output_dir>
set -e

SPEC_PATH="$1"
OUTPUT_DIR="$2"

if [ -z "$SPEC_PATH" ] || [ -z "$OUTPUT_DIR" ]; then
  echo "Usage: ./render.sh <spec_path> <output_dir>"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

# Use Remotion's bundled FFmpeg
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FFMPEG="$SCRIPT_DIR/node_modules/@remotion/compositor-linux-x64-gnu/ffmpeg"
if [ ! -f "$FFMPEG" ]; then
  FFMPEG="$SCRIPT_DIR/node_modules/@remotion/compositor-linux-x64-musl/ffmpeg"
fi
if [ ! -f "$FFMPEG" ]; then
  echo "[render] WARNING: No bundled FFmpeg found — audio will not be merged"
  FFMPEG=""
fi

# Kill stale Remotion/Chrome processes from previous runs
echo "[render] Cleaning up stale processes..."
killall -q headless_shell 2>/dev/null || true
pkill -f 'remotion render' 2>/dev/null || true
sleep 1

# Concatenate all audio slots into one track
AUDIO_DIR="$OUTPUT_DIR/audio"
FULL_AUDIO="$OUTPUT_DIR/full-audio.mp3"
if [ -d "$AUDIO_DIR" ] && [ -n "$FFMPEG" ]; then
  echo "[render] Concatenating audio tracks..."
  CONCAT_FILE="$OUTPUT_DIR/audio-concat.txt"
  rm -f "$CONCAT_FILE"
  for slot in hook lead scan why close; do
    if [ -f "$AUDIO_DIR/$slot.mp3" ]; then
      echo "file '$AUDIO_DIR/$slot.mp3'" >> "$CONCAT_FILE"
    fi
  done
  "$FFMPEG" -y -f concat -safe 0 -i "$CONCAT_FILE" -c copy "$FULL_AUDIO" 2>/dev/null
  AUDIO_DURATION=$("$FFMPEG" -i "$FULL_AUDIO" 2>&1 | grep Duration | awk '{print $2}' | tr -d ,)
  echo "[render] Audio concatenated: $FULL_AUDIO (duration: $AUDIO_DURATION)"
fi

# Clear Remotion bundle cache and temp profiles
rm -rf /tmp/remotion-webpack-bundle-* /tmp/puppeteer_dev_chrome_profile-*

# --- 9:16 Anchor (primary format — all platforms) ---
render_9x16() {
  echo "[render] Rendering anchor 9:16..."
  npx remotion render src/index.tsx AnchorBrief9x16 \
    --props="$SPEC_PATH" \
    --output="$OUTPUT_DIR/anchor-9x16-silent.mp4" \
    --width=1080 --height=1920 --fps=30
}

# Attempt render with 1 retry
if ! render_9x16; then
  echo "[render] First render attempt failed. Retrying after cleanup..."
  killall -q headless_shell 2>/dev/null || true
  rm -rf /tmp/remotion-webpack-bundle-* /tmp/puppeteer_dev_chrome_profile-*
  sleep 3
  render_9x16
fi

if [ -f "$FULL_AUDIO" ] && [ -n "$FFMPEG" ]; then
  echo "[render] Merging audio onto 9:16..."
  "$FFMPEG" -y \
    -i "$OUTPUT_DIR/anchor-9x16-silent.mp4" \
    -i "$FULL_AUDIO" \
    -map 0:v:0 -map 1:a:0 \
    -c:v copy -c:a aac -b:a 128k \
    -shortest \
    "$OUTPUT_DIR/anchor-9x16.mp4" 2>&1 | tail -3
  rm -f "$OUTPUT_DIR/anchor-9x16-silent.mp4"
  echo "[render] 9:16 with audio: $(ls -lh "$OUTPUT_DIR/anchor-9x16.mp4" | awk '{print $5}')"
else
  mv "$OUTPUT_DIR/anchor-9x16-silent.mp4" "$OUTPUT_DIR/anchor-9x16.mp4"
fi

# --- Thumbnail (branded static assets, no Remotion render needed) ---
# Copy the appropriate branded thumbnail based on output dir name
if echo "$OUTPUT_DIR" | grep -q "tech-"; then
  cp "$SCRIPT_DIR/../assets/thumb_tech.png" "$OUTPUT_DIR/thumbnail.png" 2>/dev/null && \
    echo "[render] Thumbnail: tech (branded)" || echo "[render] Thumbnail: not found"
else
  cp "$SCRIPT_DIR/../assets/thumb_news.png" "$OUTPUT_DIR/thumbnail.png" 2>/dev/null && \
    echo "[render] Thumbnail: news (branded)" || echo "[render] Thumbnail: not found"
fi

echo "[render] All renders complete."
echo "[render] Output files:"
ls -lh "$OUTPUT_DIR"/*.mp4 "$OUTPUT_DIR"/*.png "$OUTPUT_DIR"/*.mp3 2>/dev/null
