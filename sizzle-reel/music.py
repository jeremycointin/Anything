"""Generates music.wav: a 110s, 120 BPM synthwave bed cut to the reel's scene timing.

Every scene boundary in index.html lands on a 2s bar, so the arrangement below
uses the same timestamps (seconds) as the SCENES / WIPES tables there.
"""
import wave
import numpy as np

SR = 44100
DUR = 110.0
BEAT = 0.5  # 120 BPM
N = int(SR * DUR)
t_all = np.arange(N) / SR
rng = np.random.default_rng(3)

L = np.zeros(N)
R = np.zeros(N)
verb_bus = np.zeros(N)


def add(buf, start, sig, gain=1.0):
    i = int(start * SR)
    if i >= N:
        return
    j = min(N, i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def add_st(start, sig, gain=1.0, pan=0.0, verb=0.0):
    add(L, start, sig, gain * (1 - max(0, pan)))
    add(R, start, sig, gain * (1 + min(0, pan)))
    if verb:
        add(verb_bus, start, sig, gain * verb)


def env(n, a, d, sustain=0.0, rel=None):
    """Attack/decay envelope over n samples (a, d in seconds)."""
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * (sustain + (1 - sustain) * np.exp(-np.maximum(0, t - a) / d))
    if rel:
        e *= np.clip((n / SR - t) / rel, 0, 1)
    return e


def saw(f, dur, harmonics=12, detune=0.0, phase=0.0):
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    f = f * (1 + detune)
    for k in range(1, harmonics + 1):
        if k * f > 9000:
            break
        out += np.sin(2 * np.pi * k * f * t + phase * k) / k
    return out * 0.6


def square(f, dur, harmonics=7):
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    for k in range(1, harmonics * 2, 2):
        out += np.sin(2 * np.pi * k * f * t) / k
    return out * 0.7


def hp(x):
    return np.diff(x, prepend=0)


def smooth(x, w):
    return np.convolve(x, np.ones(w) / w, mode="same")


# ---------- drums ----------
def kick():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t / 0.04)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.16) + rng.standard_normal(n) * np.exp(-t / 0.004) * 0.3


def clap():
    n = int(0.3 * SR)
    noise = hp(rng.standard_normal(n))
    e = np.exp(-np.arange(n) / SR / 0.09)
    for off in (0.0, 0.011, 0.022):  # flam
        i = int(off * SR)
        e[i:] += 0.6 * np.exp(-np.arange(n - i) / SR / 0.012)
    return noise * e * 0.35


def hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR)
    x = hp(hp(rng.standard_normal(n)))
    return x * np.exp(-np.arange(n) / SR / (0.06 if open_ else 0.012)) * 0.25


K, CL, HC, HO = kick(), clap(), hat(), hat(True)

# ---------- harmony: Am F C G, one chord per 2s bar ----------
CHORDS = [
    (110.00, [220.00, 261.63, 329.63]),  # Am
    (87.31, [174.61, 220.00, 261.63]),   # F
    (130.81, [196.00, 261.63, 329.63]),  # C
    (98.00, [196.00, 246.94, 293.66]),   # G
]


def chord_at(t):
    return CHORDS[int(t // 2) % 4]


# Arrangement windows (seconds)
DRUMS_FULL = [(7, 63), (67, 95), (99, 106)]
KICK_ONLY = [(2.8, 7)]
BREAKS = [(65, 67), (95, 99)]


def inside(t, spans):
    return any(a <= t < b for a, b in spans)


bars = int(DUR // 2)
for b in range(bars):
    t0 = b * 2.0
    root, notes = chord_at(t0)
    # pad — always on, softer in the intro
    pad_gain = 0.10 if t0 < 2.8 else 0.075
    if t0 >= 106:
        pad_gain = 0.0
    for k, f in enumerate(notes):
        for d, pan in ((-0.004, -0.6), (0.004, 0.6)):
            s = saw(f, 2.2, harmonics=6, detune=d, phase=k) * env(int(2.2 * SR), 0.35, 3.0, 0.7, rel=0.4)
            add_st(t0, s, pad_gain, pan=pan, verb=0.6)
    for beat in range(4):
        tb = t0 + beat * BEAT
        full = inside(tb, DRUMS_FULL)
        if full or inside(tb, KICK_ONLY):
            add_st(tb, K, 0.9)
        if full:
            if beat in (1, 3):
                add_st(tb, CL, 0.8, verb=0.25)
            add_st(tb + 0.25, HO if beat == 3 else HC, 0.7, pan=0.25)
            for s16 in (0.125, 0.375):
                add_st(tb + s16, HC, 0.35, pan=-0.3)
        # bass: driving 8ths
        if full or inside(tb, KICK_ONLY):
            for e8 in (0, 0.25):
                f = root * (2 if (beat == 3 and e8) else 1)
                s = saw(f, 0.24, harmonics=10) * env(int(0.24 * SR), 0.005, 0.12, 0.3, rel=0.03)
                s += np.sin(2 * np.pi * f / 2 * np.arange(len(s)) / SR) * env(len(s), 0.005, 0.2) * 0.8
                add_st(tb + e8, s, 0.22)
        # arpeggio lead in the second half (side projects onward)
        if inside(tb, [(67, 95), (99, 106)]):
            seq = [notes[0] * 2, notes[1] * 2, notes[2] * 2, notes[1] * 2]
            for i, s16 in enumerate((0, 0.125, 0.25, 0.375)):
                f = seq[(beat * 4 + i) % 4]
                s = square(f, 0.12) * env(int(0.12 * SR), 0.003, 0.05, rel=0.02)
                pan = -0.4 if i % 2 else 0.4
                add_st(tb + s16, s, 0.045, pan=pan, verb=0.5)
                add_st(tb + s16 + 0.375, s, 0.02, pan=-pan)  # dotted-8th echo

# ---------- FX ----------
def riser(dur):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    # sweep: progressively smaller smoothing window = brighter noise
    seg = n // 16
    for i in range(16):
        w = max(2, int(60 * (1 - i / 16)))
        out[i * seg:(i + 1) * seg] = smooth(x, w)[i * seg:(i + 1) * seg]
    tt = np.arange(n) / SR
    tone = np.sin(2 * np.pi * np.cumsum(200 + 1200 * (tt / dur) ** 2) / SR) * 0.15
    return (out + tone) * (tt / dur) ** 2


def impact():
    n = int(2.5 * SR)
    tt = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(30 + 60 * np.exp(-tt / 0.08)) / SR) * np.exp(-tt / 0.7)
    crash = hp(rng.standard_normal(n)) * np.exp(-tt / 0.6) * 0.25
    return boom + crash


def whoosh():
    n = int(0.7 * SR)
    tt = np.arange(n) / SR
    e = np.exp(-((tt - 0.4) / 0.13) ** 2)
    return smooth(rng.standard_normal(n), 6) * e * 0.5


add_st(0.0, riser(2.8), 0.35, verb=0.3)
add_st(2.8, impact(), 0.9, verb=0.4)
for b in (7, 15, 25, 35, 45, 55, 65, 85, 99):  # matches WIPES in index.html
    add_st(b - 0.4, whoosh(), 0.5, verb=0.3)
for b in (67, 71, 75, 79, 83):  # project cuts: lighter tick
    add_st(b - 0.4, whoosh(), 0.2)
add_st(63.0, riser(2.0), 0.3)
add_st(65.0, impact(), 0.55, verb=0.5)
add_st(95.0, impact(), 0.6, verb=0.5)
add_st(97.0, riser(2.0), 0.35)
add_st(99.0, impact(), 0.8, verb=0.4)
# final chord rings out
for f in (220.00, 261.63, 329.63, 440.0):
    s = saw(f, 4.0, harmonics=8) * env(int(4.0 * SR), 0.01, 1.6)
    add_st(106.0, s, 0.08, verb=0.8)
add_st(106.0, K, 0.9)
add_st(106.0, impact(), 0.5, verb=0.5)

# ---------- reverb (FFT convolution with a decaying-noise impulse) ----------
ir_n = int(2.2 * SR)
ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR / 0.55)
ir = smooth(ir, 3)
ir /= np.sqrt(np.sum(ir ** 2))
size = 1 << int(np.ceil(np.log2(N + ir_n)))
wet = np.fft.irfft(np.fft.rfft(verb_bus, size) * np.fft.rfft(ir, size), size)[:N] * 0.35
L += wet
R += np.roll(wet, int(0.013 * SR))

# ---------- master ----------
mix = np.stack([L, R], axis=1)
fade_in = np.clip(t_all / 0.3, 0, 1)
fade_out = np.clip((DUR - t_all) / 2.0, 0, 1)
mix *= (fade_in * fade_out)[:, None]
mix = np.tanh(mix * 1.4)
mix /= np.max(np.abs(mix)) / 0.89
pcm = (mix * 32767).astype("<i2")
with wave.open("music.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote music.wav", pcm.shape[0] / SR, "s")
