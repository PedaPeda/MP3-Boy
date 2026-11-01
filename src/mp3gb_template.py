#!/usr/bin/env python3
"""
mp3boy.py - MP3 BOY: packt MP3s (oder jedes andere Audioformat) in eine Game Boy ROM.

Benutzung:
    python3 mp3boy.py song1.mp3 song2.mp3 ... -o mp3boy.gb
    python3 mp3boy.py ordner_mit_mp3s/ -o mp3boy.gb

Voraussetzungen: Python 3, numpy, ffmpeg (im PATH).

Die ROM laeuft auf dem originalen Game Boy (DMG), Game Boy Pocket/Color
und in Emulatoren (SameBoy, BGB, mGBA, Emulicious). Fuer echte Hardware
ein Flashcart mit MBC5-Unterstuetzung verwenden (z.B. EverDrive GB,
EZ-Flash Junior, oder ein 8-MB-MBC5-Repro-Flashcart).

Audio: 16384 Hz Stereo, 3 Bit pro Kanal -> 16 KB/s, max. ca. 8,5 Minuten
pro ROM (8 MB). Mit --lang: 8192 Hz, doppelte Spielzeit (ca. 17 Min.),
dafuer dumpferer Klang.
"""
import argparse, base64, math, os, re, subprocess, sys, zlib, json, unicodedata

try:
    import numpy as np
except ImportError:
    sys.exit("Fehler: numpy fehlt. Installieren mit:  pip install numpy")

RATE = 16384                    # wird mit --lang auf 8192 gesetzt
BANK = 0x4000
MAX_BANKS = 512                 # 8 MB (MBC5)
TABLE_COUNT = 0x3000
TABLE = 0x3100
ENTRY = 32
MAX_TRACKS = (0x4000 - TABLE) // ENTRY
NAME_LEN = 24
VIS_BYTES = 0x280               # Spektrum-Kopf je Bank
AUDIO_PER_BANK = BANK - VIS_BYTES
VIS_FRAMES = 62
VIS_BANDS = 20

BASE_ROM = zlib.decompress(base64.b64decode(
"@@BASE@@"
))

AUDIO_EXT = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".opus", ".wma", ".aiff", ".aif"}

UMLAUT = {"ä": "AE", "ö": "OE", "ü": "UE", "Ä": "AE", "Ö": "OE", "Ü": "UE", "ß": "SS"}
ALLOWED = set(" ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:;-_!?'\"()[]/&+=*#%<>$@")


def clean_name(s):
    s = "".join(UMLAUT.get(c, c) for c in s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.upper()
    s = "".join(c if c in ALLOWED else " " for c in s)
    s = re.sub(r"\s+", " ", s).strip()
    return (s or "UNTITLED")[:NAME_LEN]


def probe_title(path, with_artist=False):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, check=True).stdout
        tags = {k.lower(): v for k, v in json.loads(out).get("format", {}).get("tags", {}).items()}
        title, artist = tags.get("title"), tags.get("artist")
        if title and artist and with_artist:
            return f"{artist} - {title}"
        if title:
            return title
    except Exception:
        pass
    return os.path.splitext(os.path.basename(path))[0]


def decode(path, mono):
    lp = 7600 if RATE == 16384 else 3800
    # Halteglied-Ausgleich (der GB haelt jedes Sample -> Hoehen fallen ab)
    zoh = "highshelf=f=5000:g=2.5:t=q:w=0.7," if RATE == 16384 else "highshelf=f=2500:g=2.5:t=q:w=0.7,"
    af = (f"highpass=f=90,lowpass=f={lp},"
          "equalizer=f=250:t=q:w=1:g=-2,"           # weniger Droehnen
          "equalizer=f=3000:t=q:w=1:g=2,"           # mehr Praesenz
          "dynaudnorm=f=75:g=7:p=0.9:m=40:s=12,"
          "acompressor=threshold=0.05:ratio=8:attack=2:release=60:makeup=4,"
          + zoh +
          "alimiter=limit=0.98:attack=1:release=20")
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-vn", "-af", af,
           "-ac", "1" if mono else "2", "-ar", str(RATE), "-f", "s16le", "-"]
    try:
        raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    except FileNotFoundError:
        sys.exit("Fehler: ffmpeg nicht gefunden. Bitte installieren und in den PATH legen.")
    except subprocess.CalledProcessError as e:
        print(f"  ! konnte {path} nicht dekodieren: {e.stderr.decode(errors='ignore').strip()}")
        return None
    a = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    a = a.reshape(-1, 1 if mono else 2)
    if mono:
        a = np.repeat(a, 2, axis=1)
    return a


def normalize(a):
    """Pegel so anheben, dass alle 8 Stufen genutzt werden (sanftes Soft-Clipping)."""
    peak = np.percentile(np.abs(a), 99.5)
    if peak < 1e-4:
        return a * 0
    y = a / peak
    return np.tanh(y * 1.1) / np.tanh(1.1)


def quantize(ch, gate=0.03, shape=0.8):
    """Float [-1,1] -> Stufen 0..7.
    - symmetrisch um 3.5, nutzt alle 8 Stufen ohne abgeschnittene Spitzen
    - Rauschformung: Quantisierungsrauschen wird in tiefe Frequenzen
      verschoben, wo die Musik es ueberdeckt (weniger Zischen und weniger
      Spiegelfrequenzen ueber 8 kHz)
    - Stille liegt exakt auf Stufe 4 -> kein Grundrauschen"""
    w = RATE // 50
    env = np.convolve(np.abs(ch), np.ones(w) / w, "same")
    silent = env < gate
    k = int(RATE * 0.06)
    glide = np.convolve(silent.astype(np.float64), np.ones(k) / k, "same")
    y = (3.5 + 0.5 * glide + np.clip(ch, -1, 1) * 4.0).tolist()
    sil = silent.tolist()
    out = bytearray(len(y))
    e = 0.0
    for i in range(len(y)):
        if sil[i]:
            out[i] = 4
            e = 0.0
            continue
        v = y[i] - shape * e        # NTF = 1 + shape*z^-1 -> Rauschen nach unten
        q = int(v + 0.5) if v > -0.5 else 0
        if q > 7:
            q = 7
        e = v - q
        if e > 1.0:
            e = 1.0
        elif e < -1.0:
            e = -1.0
        out[i] = q
    return np.frombuffer(bytes(out), dtype=np.uint8)


def spectrum_frames(mono, n_banks):
    """Spektrum fuer jeden Visualizer-Frame (20 Baender, 0..15).
    Frame k einer Bank = Audioadressen mit High-Byte $42+k."""
    j = np.arange(AUDIO_PER_BANK)
    frame_of = ((0x4280 + j) >> 8) - 0x42
    centers = np.array([j[frame_of == k].mean() for k in range(VIS_FRAMES)])
    c = (np.arange(n_banks)[:, None] * AUDIO_PER_BANK + centers[None, :]).ravel().astype(int)
    N = 512
    total = n_banks * AUDIO_PER_BANK
    pad = np.zeros(total + N * 3)
    pad[N:N + len(mono)] = mono[:total]
    idx = c[:, None] + N // 2 + np.arange(N)[None, :]
    win = np.hanning(N)
    spec = np.abs(np.fft.rfft(pad[idx] * win, axis=1))
    freqs = np.fft.rfftfreq(N, 1 / RATE)
    edges = np.geomspace(60, min(7600, RATE / 2 - 200), VIS_BANDS + 1)
    cols = []
    for b in range(VIS_BANDS):
        m = (freqs >= edges[b]) & (freqs < edges[b + 1])
        if not m.any():
            m = np.zeros(len(freqs), bool)
            m[np.argmin(np.abs(freqs - np.sqrt(edges[b] * edges[b + 1])))] = True
        cols.append(spec[:, m].mean(axis=1))
    bands = np.stack(cols, axis=1)
    db = 20 * np.log10(bands + 1e-6)
    top = np.percentile(db, 99, axis=0)            # jedes Band erreicht oben die Spitze
    lv = (db - (top - 33)) / 33 * 15
    lv = np.clip(lv, 0, 15)
    # langsam abfallende Balken
    out = np.empty_like(lv)
    prev = np.zeros(VIS_BANDS)
    fall = 0.7 if RATE == 16384 else 1.4
    for t in range(len(lv)):
        prev = np.maximum(lv[t], prev - fall)
        out[t] = prev
    return np.round(out).astype(np.uint8).reshape(n_banks, VIS_FRAMES, VIS_BANDS)


def pack_banks(levels, vis):
    """Audio + Spektrum zu Baenken zusammensetzen."""
    nb = vis.shape[0]
    data = bytearray()
    for b in range(nb):
        v = vis[b]
        head = bytes(((v[:, 0::2] << 4) | v[:, 1::2]).ravel().tolist())
        head += b"\x00" * (VIS_BYTES - len(head))
        chunk = levels[b * AUDIO_PER_BANK:(b + 1) * AUDIO_PER_BANK]
        chunk += b"\x44" * (AUDIO_PER_BANK - len(chunk))   # Rest = Stille
        data += head + chunk
    return data


def collect(inputs):
    files = []
    for p in inputs:
        if os.path.isdir(p):
            for f in sorted(os.listdir(p)):
                if os.path.splitext(f)[1].lower() in AUDIO_EXT:
                    files.append(os.path.join(p, f))
        elif os.path.isfile(p):
            files.append(p)
        else:
            print(f"  ! nicht gefunden: {p}")
    return files


def main():
    ap = argparse.ArgumentParser(description="MP3 BOY: MP3s -> Game Boy (DMG) ROM")
    ap.add_argument("inputs", nargs="+", help="Audiodateien oder Ordner")
    ap.add_argument("-o", "--output", default="mp3boy.gb", help="Ausgabe-ROM (Standard: mp3boy.gb)")
    ap.add_argument("--lang", action="store_true",
                    help="Langspiel: 8192 Hz, doppelte Spielzeit, dumpferer Klang")
    ap.add_argument("--mono", action="store_true", help="Mono statt Stereo")
    ap.add_argument("--artist", action="store_true", help="Interpret vor den Titel setzen")
    ap.add_argument("--max-seconds", type=float, default=0, help="Songs auf N Sekunden kuerzen")
    args = ap.parse_args()
    global RATE
    if args.lang:
        RATE = 8192

    files = collect(args.inputs)
    if not files:
        sys.exit("Keine Audiodateien gefunden.")

    rom = bytearray(BASE_ROM)
    rom = rom[:BANK]                    # Bank 0 = Player-Code
    banks_used = 1
    tracks = []
    for path in files:
        if len(tracks) >= MAX_TRACKS:
            print(f"  ! maximal {MAX_TRACKS} Titel, Rest ignoriert")
            break
        name = clean_name(probe_title(path, args.artist))
        print(f"* {os.path.basename(path)}  ->  {name}")
        a = decode(path, args.mono)
        if a is None or len(a) == 0:
            continue
        if args.max_seconds > 0:
            a = a[: int(args.max_seconds * RATE)]
        free_banks = MAX_BANKS - banks_used
        max_samples = free_banks * AUDIO_PER_BANK
        if max_samples < RATE:
            print("  ! ROM voll (8 MB), Titel uebersprungen")
            break
        if len(a) > max_samples:
            print(f"  ! zu lang fuer den Restplatz, gekuerzt auf {max_samples // RATE} s")
            a = a[:max_samples]
        a = normalize(a)
        l = quantize(a[:, 0])
        r = quantize(a[:, 1])
        levels = bytes(((l << 4) | r).astype(np.uint8).tobytes())
        nb = math.ceil(len(levels) / AUDIO_PER_BANK)
        vis = spectrum_frames((a[:, 0] + a[:, 1]) / 2, nb)
        data = pack_banks(levels, vis)
        start = banks_used
        rom += data
        banks_used += nb
        secs = math.ceil(len(a) / RATE)
        tracks.append((start, nb, secs, name))
        print(f"  {secs // 60}:{secs % 60:02d} min, {nb * 16} KB, Baenke {start}-{start + nb - 1}")

    if not tracks:
        sys.exit("Keine Titel konvertiert.")

    # Tracktabelle
    rom[TABLE_COUNT] = len(tracks)
    rom[TABLE_COUNT + 1] = 0 if RATE == 16384 else 1
    for i, (start, nb, secs, name) in enumerate(tracks):
        o = TABLE + i * ENTRY
        e = bytearray(ENTRY)
        e[0:2] = start.to_bytes(2, "little")
        e[2:4] = nb.to_bytes(2, "little")
        e[4:6] = min(secs, 0xFFFF).to_bytes(2, "little")
        nm = name.ljust(NAME_LEN).encode("ascii")
        e[8:8 + NAME_LEN] = nm
        rom[o:o + ENTRY] = e

    # Auf Zweierpotenz (min. 32 KB) auffuellen
    size = 0x8000
    while size < len(rom):
        size *= 2
    rom += b"\xFF" * (size - len(rom))
    rom[0x148] = int(math.log2(size // 0x8000))

    # Header- und globale Pruefsumme
    c = 0
    for b in rom[0x134:0x14D]:
        c = (c - b - 1) & 0xFF
    rom[0x14D] = c
    rom[0x14E] = rom[0x14F] = 0
    g = sum(rom) & 0xFFFF
    rom[0x14E], rom[0x14F] = g >> 8, g & 0xFF

    with open(args.output, "wb") as f:
        f.write(rom)
    total = sum(t[2] for t in tracks)
    print(f"\nFertig: {args.output}  ({len(rom) // 1024} KB, {len(tracks)} Titel, "
          f"{total // 60}:{total % 60:02d} min, {RATE} Hz)")


if __name__ == "__main__":
    main()
