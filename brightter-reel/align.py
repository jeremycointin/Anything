"""Finds where each script line (vo_lines.json) starts/ends in the narration by
matching detected pauses to line lengths (dynamic programming)."""
import json, re, subprocess, sys
src = sys.argv[1]
lines = json.load(open("vo_lines.json"))
N = len(lines)
out = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af", "silencedetect=noise=-38dB:d=0.2", "-f", "null", "-"], capture_output=True, text=True).stderr
st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
s0 = en[0] if st and st[0] < 0.05 else 0.0
s1 = st[-1] if len(st) > len(en) else dur
sil = [(a, b) for a, b in zip(st, en) if a > s0 + 0.2 and b < s1 - 0.2]
L = [len(t) for t in lines]; tot = sum(L)
exp = [s0 + (s1 - s0) * sum(L[:i + 1]) / tot for i in range(N - 1)]
M = len(sil); INF = 1e18
cost = lambda i, j: (((sil[j][0] + sil[j][1]) / 2 - exp[i]) / 1.5) ** 2 - 6 * min(sil[j][1] - sil[j][0], 0.8)
dp = [[INF] * M for _ in range(N - 1)]; bk = [[-1] * M for _ in range(N - 1)]
for j in range(M): dp[0][j] = cost(0, j)
for i in range(1, N - 1):
    best, bj = INF, -1
    for j in range(M):
        if j > 0 and dp[i - 1][j - 1] < best: best, bj = dp[i - 1][j - 1], j - 1
        if bj >= 0: dp[i][j] = best + cost(i, j); bk[i][j] = bj
j = min(range(M), key=lambda j: dp[N - 2][j]); picks = [j]
for i in range(N - 2, 0, -1): j = bk[i][j]; picks.append(j)
cuts = [sil[j] for j in reversed(picks)]
starts = [s0] + [b for a, b in cuts]; ends = [a for a, b in cuts] + [s1]
res = [{"start": round(a, 3), "end": round(b, 3), "text": t} for a, b, t in zip(starts, ends, lines)]
for r in res: print("%6.2f-%6.2f %5.1f c/s  %s" % (r["start"], r["end"], len(r["text"]) / (r["end"] - r["start"]), r["text"][:60]))
json.dump(res, open("vo_timing.json", "w"), indent=1)
