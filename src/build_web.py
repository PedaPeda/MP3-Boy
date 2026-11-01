#!/usr/bin/env python3
"""Erzeugt ../index.html (Web-Frontend) aus web_template.html + player_base.gb + Font."""
import base64, os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import makefont
base = open(os.path.join(here, "player_base.gb"), "rb").read()[:0x4000]
font2 = makefont.build()
font1 = font2[0::2]                      # beide Bitplanes sind gleich -> 1 Bit pro Pixel
t = open(os.path.join(here, "web_template.html"), encoding="utf-8").read()
t = t.replace("@@BASE_ROM@@", base64.b64encode(base).decode())
t = t.replace("@@FONT@@", base64.b64encode(font1).decode())
open(os.path.join(here, "..", "index.html"), "w", encoding="utf-8").write(t)
print("index.html ok")
