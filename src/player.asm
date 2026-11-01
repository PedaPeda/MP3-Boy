; =====================================================================
;  MP3 BOY  -  Game Boy DMG, MBC5, bis 8 MB Audio
;  Wiedergabe: 16384 Hz (oder 8192 Hz) Stereo-PCM ueber NR50.
;  Kanal 3 liefert einen konstanten Pegel, NR50 moduliert ihn pro Sample
;  (3 Bit je Seite). Ein Datenbyte = ein Stereo-Sample = direkt NR50.
;  Tracks beginnen an Bankgrenzen; Ende = Startbank + Bankanzahl.
;
;  Tracktabelle (vom Konverter geschrieben) in Bank 0:
;    $3000        Anzahl Tracks
;    $3001        Modus: 0 = 16384 Hz, 1 = 8192 Hz
;    $3100 + 32*n Eintrag: +0 Startbank(16) +2 Bankanzahl(16)
;                          +4 Dauer in s (16)  +8 Name (24 Zeichen)
; =====================================================================

DEF rP1    EQU $FF00
DEF rTIMA  EQU $FF05
DEF rTMA   EQU $FF06
DEF rTAC   EQU $FF07
DEF rIF    EQU $FF0F
DEF rNR30  EQU $FF1A
DEF rNR31  EQU $FF1B
DEF rNR32  EQU $FF1C
DEF rNR33  EQU $FF1D
DEF rNR34  EQU $FF1E
DEF rNR50  EQU $FF24
DEF rNR51  EQU $FF25
DEF rNR52  EQU $FF26
DEF rLCDC  EQU $FF40
DEF rSTAT  EQU $FF41
DEF rSCY   EQU $FF42
DEF rSCX   EQU $FF43
DEF rLY    EQU $FF44
DEF rBGP   EQU $FF47
DEF rIE    EQU $FFFF

DEF TRACK_COUNT EQU $3000
DEF TRACK_MODE  EQU $3001
DEF TRACK_TABLE EQU $3100
DEF LIST_ROWS   EQU 11
DEF LIST_TOP    EQU 2

DEF T_BAR0  EQU 128
DEF T_BAR1  EQU 129
DEF T_ARROW EQU 130
DEF T_NOTE  EQU 131
DEF T_PLAY  EQU 132
DEF T_PAUSE EQU 133
DEF T_STOP  EQU 134
DEF T_LINE  EQU 135

DEF PAD_RIGHT  EQU 0
DEF PAD_LEFT   EQU 1
DEF PAD_UP     EQU 2
DEF PAD_DOWN   EQU 3
DEF PAD_A      EQU 4
DEF PAD_B      EQU 5
DEF PAD_SELECT EQU 6
DEF PAD_START  EQU 7

; ---------------------------------------------------------------------
SECTION "vec_timer", ROM0[$50]
    jp hISR

SECTION "header", ROM0[$100]
    nop
    jp Start
    ds $150 - @, 0

; ---------------------------------------------------------------------
SECTION "hram", HRAM
hBankL: db
hBankH: db
hEnd:   db
hEndL:  db
hEndH:  db
hTMA:   db
hMode:  db              ; 0 = 16384 Hz (1 Bank = 1 s), 1 = 8192 Hz (2 s)

SECTION "wram", WRAM0
wCount:     db
wCursor:    db
wScroll:    db
wPlaying:   db      ; $FF = gestoppt
wPaused:    db
wJoyPrev:   db
wJoyNew:    db
wJoyHeld:   db
wRepeat:    db
wStartL:    db
wStartH:    db
wNBanksL:   db
wNBanksH:   db
wDurL:      db
wDurH:      db
wLastSecL:  db
wLastSecH:  db
wSecL:      db
wSecH:      db
wLine:      ds 20

; ---------------------------------------------------------------------
SECTION "isr", ROM0
; Schneller Pfad liegt im HRAM (selbstmodifizierend, 36 Takte inkl. Dispatch).
; Hier nur der seltene Pfad: alle 256 Samples, bzw. Bankwechsel.
IsrCarry:
    ldh a, [hSmpHi]
    inc a
    cp $80
    jr z, .bank
    ldh [hSmpHi], a
    pop af
    reti
.bank
    ld a, $40
    ldh [hSmpHi], a
    ldh a, [hBankL]
    inc a
    ldh [hBankL], a
    ld [$2000], a
    jr nz, .nb
    ldh a, [hBankH]
    inc a
    ldh [hBankH], a
    ld [$3000], a
.nb
    push bc
    ldh a, [hBankL]
    ld b, a
    ldh a, [hEndL]
    cp b
    jr nz, .cont
    ldh a, [hBankH]
    ld b, a
    ldh a, [hEndH]
    cp b
    jr nz, .cont
    ld a, 1                 ; Track-Ende
    ldh [hEnd], a
    xor a
    ldh [rIE], a
    ld a, $33
    ldh [rNR50], a
.cont
    pop bc
    pop af
    reti

HramCode:
LOAD "hram_isr", HRAM
hISR:
    push af
    db $FA                  ; ld a, [nnnn]
hSmpLo: db $00
hSmpHi: db $40
    ldh [rNR50], a
    ldh a, [hSmpLo]
    inc a
    ldh [hSmpLo], a
    jr z, .carry
    pop af
    reti
.carry
    jp IsrCarry
ENDL
HramCodeEnd:

; ---------------------------------------------------------------------
SECTION "main", ROM0
Start:
    di
    ld sp, $E000
.waitvb
    ldh a, [rLY]
    cp 144
    jr c, .waitvb
    xor a
    ldh [rLCDC], a          ; LCD aus

    ; Font laden
    ld hl, FontData
    ld de, $8000
    ld bc, FontDataEnd - FontData
.cpy
    ld a, [hl+]
    ld [de], a
    inc de
    dec bc
    ld a, b
    or c
    jr nz, .cpy

    ; BG-Map mit Leerzeichen fuellen
    ld hl, $9800
    ld bc, 1024
.clr
    ld a, " "
    ld [hl+], a
    dec bc
    ld a, b
    or c
    jr nz, .clr

    ; WRAM-Variablen
    ld hl, wCount
    ld b, wLine - wCount
    xor a
.zw
    ld [hl+], a
    dec b
    jr nz, .zw
    ld a, $FF
    ld [wPlaying], a
    ld [wLastSecL], a
    ld a, [TRACK_COUNT]
    ld [wCount], a
    xor a
    ldh [hEnd], a

    ; Statischer Text
    ld hl, TxtTitle
    ld de, $9800
    call PrintZ
    ld hl, $9800 + 32*1
    call DrawRule
    ld hl, $9800 + 32*13
    call DrawRule
    ld hl, TxtHelp1
    ld de, $9800 + 32*17
    call PrintZ

    xor a
    ldh [rSCX], a
    ldh [rSCY], a
    ld a, %11100100
    ldh [rBGP], a
    ld a, %10010001         ; LCD an, BG an, Tiles $8000
    ldh [rLCDC], a

    call SoundInit

    ; ISR ins HRAM kopieren
    ld hl, HramCode
    ld c, LOW(hISR)
    ld b, HramCodeEnd - HramCode
.hc
    ld a, [hl+]
    ldh [c], a
    inc c
    dec b
    jr nz, .hc

    ; Timer: 262144 Hz / 16 = 16384 Hz  bzw. / 32 = 8192 Hz
    ld a, [TRACK_MODE]
    ldh [hMode], a
    or a
    ld a, 256 - 16
    jr z, .tm
    ld a, 256 - 32
.tm
    ldh [hTMA], a
    ldh [rTMA], a
    ldh [rTIMA], a
    ld a, %101
    ldh [rTAC], a
    xor a
    ldh [rIF], a
    ldh [rIE], a
    ei

    call DrawList
    call DrawStatus

    ld a, [wCount]
    or a
    jr nz, MainLoop
    ld hl, TxtEmpty
    ld de, $9800 + 32*5
    call PrintZ

MainLoop:
.w1
    ldh a, [rLY]
    cp 144
    jr z, .w1
.w2
    ldh a, [rLY]
    cp 144
    jr nz, .w2

    call ReadPad

    ; Track zu Ende?
    ldh a, [hEnd]
    or a
    jr z, .noEnd
    xor a
    ldh [hEnd], a
    call NextTrack
.noEnd
    ld a, [wJoyNew]
    ld b, a

    bit PAD_UP, b
    call nz, CursorUp
    ld a, [wJoyNew]
    bit PAD_DOWN, a
    call nz, CursorDown
    ld a, [wJoyNew]
    bit PAD_A, a
    call nz, PressA
    ld a, [wJoyNew]
    bit PAD_B, a
    call nz, StopPlayback
    ld a, [wJoyNew]
    bit PAD_START, a
    call nz, TogglePause
    ld a, [wJoyNew]
    bit PAD_RIGHT, a
    call nz, NextTrack
    ld a, [wJoyNew]
    bit PAD_LEFT, a
    call nz, PrevTrack
    ld a, [wJoyNew]
    bit PAD_SELECT, a
    call nz, JumpToPlaying

    call UpdateTime
    jr MainLoop

; ---------------------------------------------------------------------
SoundInit:
    ld a, $80
    ldh [rNR52], a
    ld a, $44               ; nur Kanal 3, links + rechts
    ldh [rNR51], a
    ld a, $33
    ldh [rNR50], a
    xor a
    ldh [rNR30], a          ; DAC aus, Wave-RAM beschreibbar
    ld hl, $FF30
    ld b, 16
    ld a, $FF
.w
    ld [hl+], a
    dec b
    jr nz, .w
    ld a, $80
    ldh [rNR30], a
    xor a
    ldh [rNR31], a
    ld a, $20               ; 100 %
    ldh [rNR32], a
    ld a, $FF
    ldh [rNR33], a
    ld a, $87               ; Trigger, keine Laengenbegrenzung
    ldh [rNR34], a
    ret

; ---------------------------------------------------------------------
; Joypad, mit Auto-Repeat fuer Hoch/Runter
ReadPad:
    ld a, $20
    ldh [rP1], a
    ldh a, [rP1]
    ldh a, [rP1]
    cpl
    and $0F
    swap a
    ld b, a
    ld a, $10
    ldh [rP1], a
    ldh a, [rP1]
    ldh a, [rP1]
    ldh a, [rP1]
    ldh a, [rP1]
    ldh a, [rP1]
    cpl
    and $0F
    or b
    ld b, a                 ; b = Start Select B A Down Up Left Right
    ld a, $30
    ldh [rP1], a
    ; b ist anders herum: high nibble = D-Pad, low = Buttons -> tauschen
    ld a, b
    swap a
    ld b, a
    ld a, [wJoyPrev]
    cpl
    and b
    ld c, a                 ; neu gedrueckt
    ld a, b
    ld [wJoyPrev], a
    ; Auto-Repeat (Up/Down)
    ld a, b
    and %00001100
    jr z, .noRep
    ld a, c
    and %00001100
    jr z, .held
    ld a, 20
    ld [wRepeat], a
    jr .out
.held
    ld a, [wRepeat]
    dec a
    ld [wRepeat], a
    jr nz, .out
    ld a, 5
    ld [wRepeat], a
    ld a, b
    and %00001100
    or c
    ld c, a
    jr .out
.noRep
.out
    ld a, c
    ld [wJoyNew], a
    ret

; ---------------------------------------------------------------------
CursorUp:
    ld a, [wCursor]
    or a
    ret z
    dec a
    ld [wCursor], a
    jr FixScroll
CursorDown:
    ld a, [wCount]
    or a
    ret z
    dec a
    ld b, a
    ld a, [wCursor]
    cp b
    ret nc
    inc a
    ld [wCursor], a
    ; fallthrough
FixScroll:
    ld a, [wScroll]
    ld b, a
    ld a, [wCursor]
    cp b
    jr nc, .notAbove
    ld [wScroll], a
    jp DrawList
.notAbove
    ; cursor >= scroll + LIST_ROWS ?
    ld a, b
    add LIST_ROWS
    ld c, a
    ld a, [wCursor]
    cp c
    jp c, DrawList
    sub LIST_ROWS - 1
    ld [wScroll], a
    jp DrawList

JumpToPlaying:
    ld a, [wPlaying]
    cp $FF
    ret z
    ld [wCursor], a
    jr FixScroll

PressA:
    ld a, [wCount]
    or a
    ret z
    ld a, [wPlaying]
    ld b, a
    ld a, [wCursor]
    cp b
    jp z, TogglePause
    jp PlayTrack

NextTrack:
    ld a, [wPlaying]
    cp $FF
    ret z
    inc a
    ld b, a
    ld a, [wCount]
    cp b
    ld a, b
    jr nz, .ok
    xor a
.ok
    ld [wCursor], a
    call PlayTrack
    jr FixScroll

PrevTrack:
    ld a, [wPlaying]
    cp $FF
    ret z
    or a
    jr nz, .dec
    ld a, [wCount]
.dec
    dec a
    ld [wCursor], a
    call PlayTrack
    jr FixScroll

; ---------------------------------------------------------------------
; HL = Zeiger auf Tabelleneintrag A
EntryPtr:
    ld l, a
    ld h, 0
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    ld de, TRACK_TABLE
    add hl, de
    ret

; A = Tracknummer
PlayTrack:
    di
    ld [wPlaying], a
    call EntryPtr
    ld a, [hl+]
    ld [wStartL], a
    ldh [hBankL], a
    ld [$2000], a
    ld a, [hl+]
    ld [wStartH], a
    ldh [hBankH], a
    ld [$3000], a
    ld a, [hl+]
    ld [wNBanksL], a
    ld a, [hl+]
    ld [wNBanksH], a
    ; Endbank = Start + Anzahl
    ld a, [wNBanksL]
    ld b, a
    ld a, [wStartL]
    add b
    ldh [hEndL], a
    ld a, [wNBanksH]
    ld b, a
    ld a, [wStartH]
    adc b
    ldh [hEndH], a
    ld a, [hl+]
    ld [wDurL], a
    ld a, [hl+]
    ld [wDurH], a
    xor a
    ldh [hSmpLo], a
    ldh [hEnd], a
    ld [wPaused], a
    ld a, $40
    ldh [hSmpHi], a
    ldh a, [hTMA]
    ldh [rTIMA], a
    xor a
    ldh [rIF], a
    ld a, %100              ; Timer-IRQ
    ldh [rIE], a
    ld a, $FF
    ld [wLastSecL], a
    ei
    call DrawList
    jp DrawStatus

StopPlayback:
    xor a
    ldh [rIE], a
    ld a, $FF
    ld [wPlaying], a
    ld [wLastSecL], a
    xor a
    ld [wPaused], a
    call DrawList
    jp DrawStatus

TogglePause:
    ld a, [wPlaying]
    cp $FF
    jr nz, .playing
    ; gestoppt -> markierten Track starten
    ld a, [wCount]
    or a
    ret z
    ld a, [wCursor]
    jp PlayTrack
.playing
    ld a, [wPaused]
    xor 1
    ld [wPaused], a
    jr z, .resume
    xor a
    ldh [rIE], a
    jp DrawStatus
.resume
    xor a
    ldh [rIF], a
    ld a, %100
    ldh [rIE], a
    jp DrawStatus

; ---------------------------------------------------------------------
; Spielzeit aus aktueller Bank berechnen (1 Bank = 16384 Samples)
UpdateTime:
    ld a, [wPlaying]
    cp $FF
    ret z
    di
    ldh a, [hBankL]
    ld l, a
    ldh a, [hBankH]
    ld h, a
    ldh a, [hSmpHi]
    ld b, a
    ei
    ld a, [wStartL]
    ld e, a
    ld a, [wStartH]
    ld d, a
    ; hl = bank - start
    ld a, l
    sub e
    ld l, a
    ld a, h
    sbc d
    ld h, a
    push hl                 ; gespielte Baenke
    ldh a, [hMode]
    or a
    jr z, .lo               ; 16 kHz: 1 Bank = 1 s
    add hl, hl              ; 8 kHz: 1 Bank = 2 s
    ld a, b
    cp $60
    jr c, .lo
    inc hl
.lo
    ld a, l
    ld [wSecL], a
    ld c, a
    ld a, h
    ld [wSecH], a
    ld b, a
    pop de                  ; de = gespielte Baenke
    ld a, [wLastSecL]
    cp c
    jr nz, .changed
    ld a, [wLastSecH]
    cp b
    ret z
.changed
    ld a, c
    ld [wLastSecL], a
    ld a, b
    ld [wLastSecH], a
    push de
    call DrawTimeRow
    pop de
    jp DrawProgress

; DE = gespielte Baenke -> Balken (20 Tiles)
DrawProgress:
    ; hl = de * 20
    ld h, d
    ld l, e
    add hl, hl
    add hl, hl              ; *4
    ld b, h
    ld c, l
    add hl, hl
    add hl, hl              ; *16
    add hl, bc              ; *20
    ld a, [wNBanksL]
    ld c, a
    ld a, [wNBanksH]
    ld b, a
    ld e, 0                 ; Ergebnis
    ld a, b
    or c
    jr z, .done
.div
    ld a, l
    sub c
    ld a, h
    sbc b
    jr c, .done
    ld a, l
    sub c
    ld l, a
    ld a, h
    sbc b
    ld h, a
    inc e
    ld a, e
    cp 20
    jr nz, .div
.done
    ; wLine fuellen
    ld hl, wLine
    ld b, 20
.fill
    ld a, e
    or a
    ld a, T_BAR0
    jr z, .emp
    dec e
    ld a, T_BAR1
.emp
    ld [hl+], a
    dec b
    jr nz, .fill
    ld hl, wLine
    ld de, $9800 + 32*16
    ld c, 20
    jp PrintN

; Zeile 15: Symbol  MM:SS / MM:SS   NNN
DrawTimeRow:
    call ClearLine
    ld a, [wPlaying]
    cp $FF
    jr nz, .p
    ld a, T_STOP
    ld [wLine], a
    ld hl, TxtStopped
    ld de, wLine + 2
    call CopyZ
    jr .out
.p
    ld a, [wPaused]
    or a
    ld a, T_PLAY
    jr z, .ic
    ld a, T_PAUSE
.ic
    ld [wLine], a
    ld a, [wSecL]
    ld l, a
    ld a, [wSecH]
    ld h, a
    ld de, wLine + 2
    call FmtTime
    ld a, "/"
    ld [de], a
    inc de
    ld a, [wDurL]
    ld l, a
    ld a, [wDurH]
    ld h, a
    call FmtTime
    ; Tracknummer rechts: "NNN"
    ld a, [wPlaying]
    inc a
    ld de, wLine + 17
    call Fmt3
.out
    ld hl, wLine
    ld de, $9800 + 32*15
    ld c, 20
    jp PrintN

; HL = Sekunden -> "MM:SS" nach DE (DE danach hinter Text)
FmtTime:
    ld b, 0                 ; Minuten
.m
    ld a, l
    sub 60
    ld c, a
    ld a, h
    sbc 0
    jr c, .mdone
    ld h, a
    ld l, c
    inc b
    jr .m
.mdone
    ld a, b
    cp 100
    jr c, .ok
    ld a, 99
.ok
    call Fmt2
    ld a, ":"
    ld [de], a
    inc de
    ld a, l
    jp Fmt2

; A (0..99) -> zwei Ziffern nach DE
Fmt2:
    ld c, "0"
.t
    cp 10
    jr c, .u
    sub 10
    inc c
    jr .t
.u
    ld b, a
    ld a, c
    ld [de], a
    inc de
    ld a, b
    add "0"
    ld [de], a
    inc de
    ret

; A (0..255) -> drei Ziffern nach DE
Fmt3:
    ld c, "0"
.h
    cp 100
    jr c, .t
    sub 100
    inc c
    jr .h
.t
    ld b, a
    ld a, c
    ld [de], a
    inc de
    ld a, b
    jr Fmt2

; ---------------------------------------------------------------------
DrawStatus:
    ; Zeile 14: Name des laufenden Titels
    call ClearLine
    ld a, [wPlaying]
    cp $FF
    jr z, .none
    call EntryPtr
    ld de, 8
    add hl, de
    ld de, wLine
    ld b, 20
.c
    ld a, [hl+]
    ld [de], a
    inc de
    dec b
    jr nz, .c
    jr .pr
.none
    ld hl, TxtNothing
    ld de, wLine
    call CopyZ
.pr
    ld hl, wLine
    ld de, $9800 + 32*14
    ld c, 20
    call PrintN
    call DrawTimeRow
    ; Fortschritt neu
    ld a, [wPlaying]
    cp $FF
    jr nz, .bar
    ld de, 0
    ld a, 1
    ld [wNBanksL], a
    jp DrawProgress
.bar
    ld a, $FF
    ld [wLastSecL], a       ; erzwingt Neuzeichnen in UpdateTime
    ret

; ---------------------------------------------------------------------
DrawList:
    ld a, [wCount]
    or a
    ret z
    ld b, 0                 ; Zeile
.row
    push bc
    call ClearLine
    ld a, [wScroll]
    add b
    ld c, a                 ; Index
    ld a, [wCount]
    cp c
    jr z, .emit
    jr c, .emit
    ; Cursor
    ld a, [wCursor]
    cp c
    jr nz, .nocur
    ld a, T_ARROW
    ld [wLine], a
.nocur
    ld a, [wPlaying]
    cp c
    jr nz, .nonote
    ld a, T_NOTE
    ld [wLine + 19], a
.nonote
    ld a, c
    call EntryPtr
    ld de, 8
    add hl, de
    ld de, wLine + 1
    ld b, 18
.cp
    ld a, [hl+]
    ld [de], a
    inc de
    dec b
    jr nz, .cp
.emit
    pop bc
    push bc
    ; Ziel = $9800 + (LIST_TOP + b) * 32
    ld a, b
    add LIST_TOP
    ld l, a
    ld h, 0
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    add hl, hl
    ld de, $9800
    add hl, de
    ld d, h
    ld e, l
    ld hl, wLine
    ld c, 20
    call PrintN
    pop bc
    inc b
    ld a, b
    cp LIST_ROWS
    jr nz, .row
    ret

; ---------------------------------------------------------------------
ClearLine:
    ld hl, wLine
    ld a, " "
    ld c, 20
.l
    ld [hl+], a
    dec c
    jr nz, .l
    ret

; HL = Quelle (0-terminiert) -> DE (WRAM)
CopyZ:
    ld a, [hl+]
    or a
    ret z
    ld [de], a
    inc de
    jr CopyZ

; HL = Ziel in VRAM: 20 Trennlinien-Tiles
DrawRule:
    ld b, 20
    ld a, T_LINE
.l
    ld [hl+], a
    dec b
    jr nz, .l
    ret

; HL = 0-terminierter Text -> DE (VRAM, nur bei LCD aus!)
PrintZ:
    ld a, [hl+]
    or a
    ret z
    ld [de], a
    inc de
    jr PrintZ

; HL = Quelle, DE = VRAM-Ziel, C = Laenge. VRAM-sicher bei LCD an.
PrintN:
    ld a, [hl+]
    ld b, a
.w
    di
    ldh a, [rSTAT]
    and 2
    jr z, .ok
    ei
    jr .w
.ok
    ld a, b
    ld [de], a
    ei
    inc de
    dec c
    jr nz, PrintN
    ret

; ---------------------------------------------------------------------
TxtTitle:   db "    ", T_NOTE, " MP3 BOY ", T_NOTE, 0
TxtHelp1:   db "A:PLAY ST:", T_PAUSE, " <>:SKIP", 0
TxtStopped: db "STOPPED", 0
TxtNothing: db "  - NOT PLAYING -", 0
TxtEmpty:   db "  NO SONGS IN ROM", 0

SECTION "font", ROM0[$1000]
FontData:
    INCBIN "font.2bpp"
FontDataEnd:

SECTION "tracks", ROM0[$3000]
    db 0
