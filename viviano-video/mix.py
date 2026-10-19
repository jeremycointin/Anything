"""Lay the per-scene voiceover clips over soundtrack.wav and mux into the video.

Usage: python3 mix.py   (expects vo/scene01.mp3 ... vo/scene10.mp3, soundtrack.wav,
                         viviano-promo-silent.mp4; writes viviano-promo.mp4)
"""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
SCENES = [0, 6, 14, 24, 36, 46, 56, 66, 74, 82, 90]
LEAD = {1: 1.4}  # seconds after scene start before the line begins (default below)
START = {10: None}  # scene 10's line runs long: start it so it ends just before 90s
DEFAULT_LEAD = 0.45
TAIL = 0.35      # keep this much air before the next cut


def duration(p):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(p)],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)['format']['duration'])


inputs, filters, labels = [], [], []
for i in range(1, 11):
    src = HERE / 'vo' / f'scene{i:02d}.mp3'
    clip = HERE / 'vo' / f'trim{i:02d}.wav'
    trim = 'silenceremove=start_periods=1:start_threshold=-45dB'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(src), '-af',
                    f'{trim},areverse,{trim},areverse,apad=pad_dur=0.08', str(clip)], check=True)
    d = duration(clip)
    slot = SCENES[i] - SCENES[i - 1]
    lead = LEAD.get(i, DEFAULT_LEAD)
    tempo = 1.0
    if lead + d > slot - TAIL:
        lead = max(0.15, slot - TAIL - d)
        if lead + d > slot - TAIL:
            tempo = min(1.12, d / (slot - TAIL - lead))
    start = SCENES[i - 1] + lead
    if i in START and d > slot - TAIL - lead:
        tempo = min(1.06, d / (slot - TAIL - lead))
        start = 90 - 0.25 - d / tempo
    print(f'scene {i}: clip {d:.2f}s, slot {slot}s, starts {start:.2f}s, tempo {tempo:.3f}')
    inputs += ['-i', str(clip)]
    chain = f'[{i - 1}:a]aresample=44100,aformat=channel_layouts=stereo'
    if tempo > 1.0:
        chain += f',atempo={tempo:.4f}'
    chain += f',adelay={int(start * 1000)}|{int(start * 1000)}[v{i}]'
    filters.append(chain)
    labels.append(f'[v{i}]')

music_idx = 10
video_idx = 11
filters.append(f"{''.join(labels)}amix=inputs=10:normalize=0,apad=whole_dur=90,volume=1.0,asplit=2[vo][key]")
filters.append(f'[{music_idx}:a]volume=0.19[mus]')
filters.append('[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[duck]')
filters.append('[vo][duck]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,atrim=0:90[aout]')

cmd = ['ffmpeg', '-y', '-v', 'error', *inputs,
       '-i', str(HERE / 'soundtrack.wav'), '-i', str(HERE / 'viviano-promo-silent.mp4'),
       '-filter_complex', ';'.join(filters),
       '-map', f'{video_idx}:v', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
       '-shortest', '-movflags', '+faststart', str(HERE / 'viviano-promo.mp4')]
subprocess.run(cmd, check=True)
print('wrote', HERE / 'viviano-promo.mp4')
