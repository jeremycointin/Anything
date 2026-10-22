#!/usr/bin/env bash
# Fetches the HeyGen narration (too big for GitHub) and extracts the frames the canvas composites.
set -e
cd "$(dirname "$0")/assets"
[ -f avatar.mp4 ] || curl -sSL -f -o avatar.mp4 "https://stlcodescape.com/Jeremy%20Cointin_%20Web%20Developer%20for%20Brightter_1080p.mp4"
mkdir -p fr_av
ffmpeg -loglevel error -y -i avatar.mp4 -q:v 3 fr_av/%05d.jpg
