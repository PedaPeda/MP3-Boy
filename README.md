# MP3 BOY: an MP3 player for the Game Boy (DMG)

Turns your MP3s into a Game Boy ROM, with a track list, playback controls and a
spectrum visualizer that moves with the music. Runs on real hardware
(flash cart with MBC5) and in emulators.

### ▶ [Open the web app: pedapeda.github.io/MP3-Boy](https://pedapeda.github.io/MP3-Boy/)

[![MP3 BOY web app](docs/web-app.png)](https://pedapeda.github.io/MP3-Boy/)

<table>
<tr>
<td align="center"><img src="visualizer.gif" width="320" alt="ROM running in the SameBoy emulator"><br><sub>The finished ROM in an emulator (SameBoy)</sub></td>
<td align="center"><img src="docs/web-preview.gif" width="240" alt="Live preview in the web app"><br><sub>Live preview in the web app</sub></td>
</tr>
</table>

`mp3boy.gb` is a ready-to-play ROM with two demo songs. Build your own ROMs with the
web app (`index.html`) or the Python tool (`mp3boy.py`).

## Web app (no installation)

Open the **[web app](https://pedapeda.github.io/MP3-Boy/)**, or download `index.html`
and double-click it (Chrome, Edge, Firefox or Safari):

1. Drag your MP3s into the window
2. Reorder and rename tracks, pick the quality (High or Long play, Stereo or Mono)
3. Listen on the preview Game Boy on the right (sound and visualizer match the real ROM)
4. Click **Build ROM** → `mp3boy.gb` is downloaded

Everything runs locally in your browser, nothing is uploaded. No Python or ffmpeg
needed. The web app produces practically the same ROM as the Python tool.

## Python tool

Requirements: Python 3, `numpy` (`pip install numpy`) and `ffmpeg`.
On Windows you can simply put `ffmpeg.exe` and `ffprobe.exe` in the same folder
as `mp3boy.py`.

```
python mp3boy.py songs -o mp3boy.gb
python mp3boy.py song1.mp3 song2.mp3 -o mp3boy.gb
```

Options:
- `--lang`: long play at 8192 Hz: twice the playing time, but a duller sound
- `--mono`: mono instead of stereo
- `--artist`: put the artist in front of the title ("ARTIST - TITLE")
- `--max-seconds 90`: cut every song after N seconds

Track names come from the ID3 title, otherwise from the file name. Besides MP3,
WAV, FLAC, OGG, M4A etc. work too.

**Capacity:** an 8 MB ROM holds about 8 minutes at best quality, about 16 minutes
with `--lang`. Up to 120 tracks.

## Controls

| Button       | Action                                      |
|--------------|---------------------------------------------|
| Up / Down    | scroll through the list (hold = fast)       |
| A            | play selected track / pause                 |
| START        | pause / resume                              |
| B            | stop                                        |
| Left / Right | previous / next track                       |
| SELECT       | jump the cursor to the playing track        |

When a track ends, the next one starts automatically.

## Spectrum visualizer

20 frequency bands from 60 Hz to 7.6 kHz, with smoothly falling bars. The Game Boy
is too slow for a real-time FFT, so the converter calculates the spectrum ahead of
time (62 frames per second) and stores it at the start of every 16 KB bank (640 bytes,
just under 4 % of the space). The player always reads the frame for the current
playback position, so everything stays exactly in sync. Drawing is flicker-free:
bars grow from the bottom first, then shrink from the top.

## Real hardware

You need a flash cart with **MBC5** support (e.g. EverDrive GB X series,
EZ-Flash Junior or an 8 MB MBC5 repro flash cart). The ROM runs on DMG,
Pocket, Color and Advance.

## Emulators

Tested with **SameBoy**. BGB, Emulicious, Gambatte and mGBA should play the sound
correctly. **PyBoy and some simple emulators stay silent** because they don't
emulate the master volume register.

## How it works

The Game Boy can't decode MP3 itself (its CPU runs at about 1 MHz), so the converter
does the work. It decodes the audio, applies EQ (presence boost, compensation for
the treble loss caused by sample-and-hold), evens out the loudness, resamples to
16384 Hz and quantizes symmetrically to 8 steps per stereo channel. Noise shaping
pushes the quantization noise into low frequencies, where the music masks it.
Silence sits exactly on one step, so quiet passages have no hiss.

On the Game Boy, channel 3 (wave) outputs a constant level. A timer interrupt
writes one byte 16384 times per second into the master volume register NR50
(bits 6–4 left, 2–0 right), modulating that level into PCM audio. The interrupt
runs as self-modifying code from HRAM (36 of 64 available cycles). The audio data
lives in 16 KB MBC5 banks (= 1 second each).

## Building from source (optional)

`src/` contains the assembly source (`player.asm`), the font generator, the web app
template (`web_template.html`) and `build.sh`. Building requires
[RGBDS](https://rgbds.gbdev.io). `build.sh` regenerates `mp3boy.py` and `index.html`
with the embedded player ROM.
