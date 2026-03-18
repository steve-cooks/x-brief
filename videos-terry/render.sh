#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
npx remotion render src/index.ts XBrief-Launch out/x-brief-launch.mp4 --codec h264
echo "Done! Output: out/x-brief-launch.mp4"
