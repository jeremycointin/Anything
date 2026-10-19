"""Synthesize the original 90s background soundtrack (numpy only).

120 BPM so every scene cut (6, 14, 24, ... 82s) lands on a bar line.
Writes soundtrack.wav (44.1kHz stereo) next to this file.
"""
import wave
from pathlib import Path

import numpy as np

SR = 44100
DUR = 90.0
BEAT = 0.5
BAR = 2.0
CUTS = [6, 14, 24, 36, 46, 56, 66, 74, 82]
rng = np.random.default_rng(7)
N = int(SR * DUR)
L = np.zeros(N)
R = np.zeros(N)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


CH = {  # chord tones as MIDI (root octave 3)
    'C': [48, 52, 55], 'G': [43, 47, 50], 'Am': [45, 48, 52], 'F': [41, 45, 48],
    'Em': [40, 43, 47], 'Dm': [50, 53, 57],
}
MAIN = ['C', 'G', 'Am', 'F']
DARK = ['Am', 'F', 'C', 'G']


def chord_at(bar):
    t = bar * BAR
    if 14 <= t < 24:
        return DARK[(bar - 7) % 4]
    return MAIN[bar % 4]


def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * (1 - pan) ** .5
    R[i:i + len(sig)] += sig * gain * (1 + pan) ** .5


def env(n, a, d_total):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4))
    rel = 0.4
    tail = np.clip((d_total - t) / rel, 0, 1)
    return e * tail


def soft_saw(f, dur, harm=7, detune=0.0):
    t = np.arange(int(dur * SR)) / SR
    s = np.zeros_like(t)
    for h in range(1, harm + 1):
        ph = rng.random() * 6.28
        s += np.sin(2 * np.pi * f * (1 + detune) * h * t + ph) / h ** 1.6
    return s


def pad(chord, t0, dur, lvl):
    notes = CH[chord] + [CH[chord][0] + 12, CH[chord][1] + 12]
    for k, n in enumerate(notes):
        f = midi(n + 12)
        s = (soft_saw(f, dur, detune=0.003) + soft_saw(f, dur, detune=-0.003)) * .5
        add(s * env(len(s), .35, dur), t0, lvl * .07, pan=(-.5 + k / 4))


def pluck(n, t0, lvl, pan=0.0):
    d = .45
    t = np.arange(int(d * SR)) / SR
    f = midi(n)
    s = (np.sin(2 * np.pi * f * t) + .35 * np.sin(4 * np.pi * f * t) + .1 * np.sin(6 * np.pi * f * t))
    s *= np.exp(-t * 9) * np.minimum(1, t / .004)
    add(s, t0, lvl * .16, pan)


def bass(n, t0, d, lvl):
    t = np.arange(int(d * SR)) / SR
    f = midi(n - 12)
    s = np.sin(2 * np.pi * f * t) + .25 * np.sin(4 * np.pi * f * t)
    s *= np.exp(-t * 2.2) * np.minimum(1, t / .01) * np.clip((d - t) / .05, 0, 1)
    add(s, t0, lvl * .38)


def kick(t0, lvl):
    d = .35
    t = np.arange(int(d * SR)) / SR
    f = 45 + 95 * np.exp(-t * 28)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    add(s, t0, lvl * .7)


def noise_hit(t0, d, decay, lvl, hp=1, pan=0.0):
    n = rng.standard_normal(int(d * SR))
    for _ in range(hp):
        n = np.diff(n, prepend=0)
    t = np.arange(len(n)) / SR
    add(n * np.exp(-t * decay) / (2 ** hp), t0, lvl, pan)


def clap(t0, lvl):
    for k, off in enumerate([0, .012, .024]):
        noise_hit(t0 + off, .18, 30 if k < 2 else 16, lvl * .22, hp=1)


def hat(t0, lvl, pan=.3):
    noise_hit(t0, .06, 70, lvl * .12, hp=2, pan=pan)


def whoosh(tc, lvl=1.0):
    d = 1.4
    n = rng.standard_normal(int(d * SR))
    n = np.diff(n, prepend=0)
    t = np.arange(len(n)) / SR
    e = np.exp(-((t - .85) / .3) ** 2)
    sweep = np.sin(2 * np.pi * np.cumsum(300 + 1500 * e) / SR)
    s = n * e * .5 + sweep * e * .05
    add(s, tc - .85, lvl * .35, pan=-.3)
    add(s, tc - .85, lvl * .15, pan=.3)
    # sub thump on the cut
    tt = np.arange(int(.6 * SR)) / SR
    add(np.sin(2 * np.pi * 52 * tt) * np.exp(-tt * 6), tc, lvl * .35)


def riser(t_end, d, lvl):
    n = np.diff(rng.standard_normal(int(d * SR)), prepend=0)
    t = np.arange(len(n)) / SR
    add(n * (t / d) ** 2.5, t_end - d, lvl * .3)


# ---- arrangement ----
ARP = [0, 1, 2, 3, 2, 1, 2, 4]  # index into extended chord tones
for bar in range(int(DUR / BAR)):
    t0 = bar * BAR
    c = chord_at(bar)
    tones = CH[c] + [CH[c][0] + 12, CH[c][1] + 12]
    intro = t0 < 6
    problem = 14 <= t0 < 24
    groove = 24 <= t0 < 82
    finale = t0 >= 82
    lift = 46 <= t0 < 66

    pad(c, t0, BAR + .4, .55 if intro else (.8 if problem else 1.0))

    if not intro:
        for i in range(8):
            if problem and i % 2:
                continue
            pluck(tones[ARP[i]] + (36 if finale else 24), t0 + i * .25,
                  .6 if problem else (1.0 if not finale else 1.15), pan=(-.4 if i % 2 else .4))

    if t0 >= 14:
        pattern = [(0, .75), (.75, .25), (1.0, .5), (1.5, .5)] if (groove or finale) else [(0, 1.0), (1.0, 1.0)]
        for off, d in pattern:
            bass(CH[c][0], t0 + off, d, .8 if problem else 1.0)

    if 6 <= t0 < 14:
        for i in range(4):
            hat(t0 + i * .5 + .25, .7)
    if problem:
        kick(t0, .5)
        kick(t0 + 1.0, .5)
    if groove or finale:
        for b in range(4):
            kick(t0 + b * .5, 1.0 if (b % 2 == 0 or finale or lift) else .0)
            hat(t0 + b * .5 + .25, 1.0)
            if lift or finale:
                hat(t0 + b * .5 + .125, .45, pan=-.3)
                hat(t0 + b * .5 + .375, .45, pan=-.3)
        clap(t0 + .5, 1.0)
        clap(t0 + 1.5, 1.0)

riser(6, 3.0, .8)
riser(24, 2.0, .7)
riser(82, 2.0, 1.0)
for c in CUTS:
    whoosh(c, 1.0 if c in (6, 24, 82) else .7)

# final sting: big C chord ringing out
for k, n in enumerate([36, 48, 55, 60, 64, 67, 72]):
    d = 2.2
    t = np.arange(int(d * SR)) / SR
    f = midi(n)
    s = (np.sin(2 * np.pi * f * t) + .3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 1.6)
    add(s, 87.8, .1, pan=-.5 + k / 6)
kick(87.8, 1.2)
clap(87.8, 1.0)

# ---- master ----
mix = np.stack([L, R], axis=1)
fade_in = np.minimum(1, np.arange(N) / (SR * 1.5))[:, None]
fade_out = np.clip((DUR - np.arange(N) / SR) / 0.6, 0, 1)[:, None]
mix *= fade_in * fade_out
mix = np.tanh(mix * 1.4) / np.tanh(1.4)  # gentle glue saturation
mix /= np.abs(mix).max() / 0.89
pcm = (mix * 32767).astype('<i2')
out = Path(__file__).with_name('soundtrack.wav')
with wave.open(str(out), 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print('wrote', out)
