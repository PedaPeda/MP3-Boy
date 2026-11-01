#!/usr/bin/env python3
"""Erzeugt zwei originale Demo-Songs als WAV (werden dann zu MP3)."""
import numpy as np, wave, sys

SR = 44100

def note_hz(n):  # MIDI
    return 440.0 * 2 ** ((n - 69) / 12)

def env(n, a=0.005, r=0.15):
    t = np.arange(n) / SR
    e = np.minimum(1, t / a) * np.exp(-t / r)
    return e

def tone(freq, dur, kind="saw", vol=0.3, r=0.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == "saw":
        w = 2 * ((t * freq) % 1) - 1
    elif kind == "sq":
        w = np.sign(np.sin(2 * np.pi * freq * t))
    elif kind == "tri":
        w = 2 * np.abs(2 * ((t * freq) % 1) - 1) - 1
    else:
        w = np.sin(2 * np.pi * freq * t)
    return w * env(n, r=r) * vol

def kick(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 50 + 120 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * 0.9

def snare(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    rng = np.random.default_rng(1)
    return (rng.uniform(-1, 1, n) * np.exp(-t * 18) * 0.5
            + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25) * 0.3)

def hat(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    rng = np.random.default_rng(2)
    x = rng.uniform(-1, 1, n)
    x = np.diff(np.concatenate([[0], x]))
    return x * np.exp(-t * 60) * 0.18

def add(buf, x, pos, pan=0.0):
    i = int(pos * SR)
    x = x[: max(0, len(buf) - i)]
    buf[i:i + len(x), 0] += x * (1 - max(0, pan))
    buf[i:i + len(x), 1] += x * (1 + min(0, pan))

def song(bpm, chords, melody, bars_rep, name, kind_lead="sq", seed=0):
    beat = 60 / bpm
    bars = len(chords) * bars_rep
    total = bars * 4 * beat + 2
    buf = np.zeros((int(total * SR), 2))
    for b in range(bars):
        root, quality = chords[b % len(chords)]
        tri = [0, 4, 7] if quality == "maj" else [0, 3, 7]
        t0 = b * 4 * beat
        # Bass (Achtel)
        for k in range(8):
            n = root - 24 + (12 if k % 2 else 0)
            add(buf, tone(note_hz(n), beat / 2, "tri", 0.45, 0.3), t0 + k * beat / 2)
        # Arpeggio (Sechzehntel)
        for k in range(16):
            n = root + tri[k % 3] + (12 if (k // 3) % 2 else 0)
            add(buf, tone(note_hz(n), beat / 4, "saw", 0.10, 0.06), t0 + k * beat / 4,
                pan=0.5 if k % 2 else -0.5)
        # Drums
        for k in range(4):
            add(buf, kick(beat), t0 + k * beat) if k in (0, 2) else add(buf, snare(beat), t0 + k * beat)
            add(buf, hat(beat / 2), t0 + k * beat + beat / 2, pan=0.3)
        # Melodie ab zweitem Durchlauf
        if b >= len(chords):
            for (pos, n, d) in melody[b % len(chords)]:
                add(buf, tone(note_hz(n), d * beat, kind_lead, 0.22, 0.35 * d),
                    t0 + pos * beat, pan=-0.2)
    buf /= np.max(np.abs(buf)) * 1.05
    # Fade-out
    fo = int(2.5 * SR)
    buf[-fo:] *= np.linspace(1, 0, fo)[:, None]
    pcm = (buf * 32767).astype("<i2")
    with wave.open(name, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())

# Song 1: "Pixel Sunrise" (C-Dur, 128 BPM)
chords1 = [(60, "maj"), (57, "min"), (53, "maj"), (55, "maj")]
mel1 = [
    [(0, 76, 1), (1, 79, 1), (2, 84, 1.5), (3.5, 83, 0.5)],
    [(0, 81, 1.5), (1.5, 79, 0.5), (2, 76, 2)],
    [(0, 77, 1), (1, 81, 1), (2, 84, 1), (3, 81, 1)],
    [(0, 79, 1.5), (1.5, 77, 0.5), (2, 74, 1), (3, 71, 1)],
]
song(128, chords1, mel1, 4, sys.argv[1] + "/pixel_sunrise.wav")

# Song 2: "Night Drive DMG" (A-Moll, 100 BPM)
chords2 = [(57, "min"), (53, "maj"), (48, "maj"), (55, "maj")]
mel2 = [
    [(0, 81, 0.5), (0.5, 84, 0.5), (1, 88, 2), (3, 86, 1)],
    [(0, 84, 1), (1, 81, 1), (2, 77, 2)],
    [(0, 79, 0.5), (0.5, 84, 0.5), (1, 88, 1.5), (2.5, 86, 0.5), (3, 84, 1)],
    [(0, 83, 2), (2, 79, 1), (3, 74, 1)],
]
song(100, chords2, mel2, 4, sys.argv[1] + "/night_drive.wav", kind_lead="saw")
