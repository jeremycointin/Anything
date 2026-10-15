"""Builds soundtrack.wav: the HeyGen narration on the reel timeline (2s lead-in,
plus a pause for the T-shirt clip) with music.wav ducked underneath.

Keep LEAD / GAP_AT / GAP in sync with avatarTime() in index.html."""
import subprocess, wave
import numpy as np

SR = 44100
LEAD = 2.0      # reel seconds before the narration starts
GAP_AT = 89.2   # narration time where the T-shirt pause is inserted
GAP = 2.9       # length of that pause


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, "<i2").astype(np.float64) / 32768


with wave.open("music.wav") as w:
    music = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float64).reshape(-1, 2) / 32768
N = len(music)
src = decode("assets/avatar.mp4")
cut = int(GAP_AT * SR)
vo = np.zeros(N)
a = int(LEAD * SR)
vo[a:a + cut] = src[:cut]
b = int((LEAD + GAP_AT + GAP) * SR)
rest = src[cut:][: N - b]
vo[b:b + len(rest)] = rest
vo *= 0.9 / np.max(np.abs(vo))

env = np.convolve(np.abs(vo), np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
duck = 1 - 0.62 * np.clip(env / 0.04, 0, 1)
duck = np.convolve(duck, np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
mix = music * 0.75 * duck[:, None] + vo[:, None]
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
with wave.open("soundtrack.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote soundtrack.wav")
