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

BASE_ROM = zlib.decompress(base64.b64decode(
"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"
"IBAIBALBf8835Ey6cw=="
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
        max_samples = free_banks * BANK
        if max_samples < RATE:
            print("  ! ROM voll (8 MB), Titel uebersprungen")
            break
        if len(a) > max_samples:
            print(f"  ! zu lang fuer den Restplatz, gekuerzt auf {max_samples // RATE} s")
            a = a[:max_samples]
        a = normalize(a)
        l = quantize(a[:, 0])
        r = quantize(a[:, 1])
        data = bytearray(((l << 4) | r).astype(np.uint8).tobytes())
        nb = math.ceil(len(data) / BANK)
        data += b"\x44" * (nb * BANK - len(data))   # Rest der Bank = Stille
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
