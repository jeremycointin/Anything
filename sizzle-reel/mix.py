"""Builds soundtrack.wav: places each voiceover line (vo_segments.json) at its
scene time (vo_script.json) and ducks music.wav underneath it."""
import json, subprocess, wave
import numpy as np

SR = 44100
script = json.load(open("vo_script.json"))
seg = json.load(open("vo_segments.json"))


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, "<i2").astype(np.float64) / 32768


with wave.open("music.wav") as w:
    music = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float64).reshape(-1, 2) / 32768
N = len(music)
vo_src = decode(seg["source"])
vo = np.zeros(N)
pad = int(0.06 * SR)
for (at, text), s, e in zip(script, seg["starts"], seg["ends"]):
    a, b = max(0, int(s * SR) - pad), min(len(vo_src), int(e * SR) + pad)
    clip = vo_src[a:b].copy()
    f = int(0.03 * SR)
    clip[:f] *= np.linspace(0, 1, f)
    clip[-f:] *= np.linspace(1, 0, f)
    i = int(at * SR) - pad
    end = min(N, i + len(clip))
    if i + len(clip) > N:
        print("warning: line runs past the end:", text)
    vo[i:end] += clip[: end - i]
    nxt = [t for t, _ in script if t > at]
    if nxt and at + (e - s) > nxt[0]:
        print(f"warning: line at {at}s overlaps the next one: {text}")

vo *= 0.92 / np.max(np.abs(vo))
# duck the music while the voice is speaking (smoothed envelope, ~120ms attack/release)
env = np.convolve(np.abs(vo), np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
duck = 1 - 0.6 * np.clip(env / 0.05, 0, 1)
duck = np.convolve(duck, np.ones(int(0.2 * SR)) / int(0.2 * SR), mode="same")
mix = music * 0.8 * duck[:, None] + vo[:, None] * 0.95
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
with wave.open("soundtrack.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote soundtrack.wav")
