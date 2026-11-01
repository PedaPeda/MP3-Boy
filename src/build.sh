#!/bin/sh
# Baut player_base.gb (RGBDS noetig) und erzeugt daraus ../mp3boy.py
set -e
cd "$(dirname "$0")"
RGB=${RGBDS:-/tmp/rgbds}
python3 makefont.py font.2bpp
$RGB/rgbasm -o player.o player.asm
$RGB/rgblink -o player_base.gb -n player.sym player.o
$RGB/rgbfix -v -m 0x19 -t "MP3 BOY" -p 0xFF player_base.gb
python3 - <<'EOF'
import base64, zlib
b = base64.b64encode(zlib.compress(open("player_base.gb","rb").read()[:0x4000], 9)).decode()
lines = "\n".join(b[i:i+76] for i in range(0, len(b), 76))
t = open("mp3gb_template.py").read().replace('"@@BASE@@"', "\n".join('"%s"' % l for l in lines.split("\n")))
open("../mp3boy.py", "w").write(t)
EOF
echo "ok"
