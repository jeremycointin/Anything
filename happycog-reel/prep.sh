#!/usr/bin/env bash
# Extracts the narration + T-shirt video frames the canvas composites (not committed: ~200MB).
set -e
cd "$(dirname "$0")/assets"
mkdir -p fr_av fr_ts
ffmpeg -loglevel error -y -i avatar.mp4 -q:v 3 fr_av/%05d.jpg
ffmpeg -loglevel error -y -i tshirt.mp4 -q:v 3 fr_ts/%05d.jpg
