#!/usr/bin/env python3
"""
vCat — a tiny black cat that lives on your desktop.

She wanders along the bottom of your screen, stalks and pounces on your mouse
cursor when you play near her, scratches the edges of your windows, climbs on
top of them, paws at your desktop icons, naps, and needs a little bit of food,
water and affection (right-click her).

Run directly:    python vcat.py
Sprite preview:  python vcat.py --sheet     (writes sprite_sheet.png, needs Pillow)
"""

import ctypes
import ctypes.wintypes as wt
import json
import math
import os
import random
import sys
import time
import tkinter as tk

# ---------------------------------------------------------------------------
# Art: palette + pixel-art frames (26 x 20 character grids)
# ---------------------------------------------------------------------------

KEY = "#fe00fe"  # transparency color key (never used in the art)

PAL = {
    "K": "#16161e",  # body (fur color, remapped per variant)
    "D": "#46465a",  # fur highlight / closed eyes (remapped per variant)
    "W": "#f4f4f8",  # socks, chest, tail tip (remapped per variant)
    "E": "#90e860",  # eyes (remapped per variant)
    "P": "#f7a8bc",  # pink ears / nose / tongue
    "O": "#ff9a3d",  # fish / food
    "B": "#62b8ff",  # water
    "R": "#ff5d76",  # hearts
    "G": "#8a8a98",  # fixed gray: bowls, the mouse
    # furniture / decor colors (never used by the cat frames)
    "n": "#8a5a3c",  # wood / cardboard brown
    "t": "#5a3a24",  # dark wood / soil shadow
    "m": "#caa46a",  # sisal / light wood / box tape
    "u": "#f0a6c0",  # cushion pink
    "i": "#d98a9e",  # cushion pink shadow
    "v": "#5cc05a",  # leaf green
    "j": "#3f9a46",  # leaf green shadow
    "l": "#8fe06a",  # leaf green highlight
    "b": "#a6dcff",  # water highlight
    "q": "#2f6fb0",  # deep water
    "c": "#b9c2cf",  # bowl rim light
    "y": "#e8c84a",  # gold / yellow (crown, pee puddle, sparkles)
    "z": "#8a5cc0",  # purple (wizard hat)
    "s": "#caa46a",  # litter sand (alias of m tone)
    "x": "#c23b3b",  # devil / costume red accent
    ".": KEY,
}

# fur variants: per-color overrides of the base palette
PALETTES = {
    "black":  {},
    "ginger": {"K": "#e0863c", "D": "#c06a28", "E": "#7cd84e"},
    "gray":   {"K": "#74748a", "D": "#5e5e72", "E": "#ffd24a"},
    "snow":   {"K": "#e6e6ee", "D": "#c5c5d2", "W": "#9c9cb0", "E": "#6ab8ff"},
    "choco":  {"K": "#6b4a38", "D": "#56392a", "E": "#ffd24a"},
}


def variant_pal(color):
    pal = dict(PAL)
    pal.update(PALETTES.get(color, {}))
    return pal

GW, GH = 26, 20  # frame grid size


def _blank():
    return [["."] * GW for _ in range(GH)]


def _blit(grid, art, x, y):
    """Stamp a small string-list onto a grid, skipping '.' pixels."""
    for r, row in enumerate(art):
        for c, ch in enumerate(row):
            if ch != "." and 0 <= y + r < GH and 0 <= x + c < GW:
                grid[y + r][x + c] = ch


def _rows(grid):
    return ["".join(r) for r in grid]


# --- reusable parts (all face RIGHT; frames get mirrored for LEFT) ---------

HEAD = [          # front-facing head, 10 x 7
    ".DKK..KKD.",   # pointed ears with shaded outer edge
    ".KPK..KPK.",   # pink inner ears
    ".KKKKKKKK.",
    "KKKKKKKKKK",
    "KEWKKKKWEK",   # bright eyes, shines turned inward (cuter)
    "KKKDPPDKKK",   # pink nose with a hint of muzzle
    ".KKKKKKKK.",
]
HEAD_BLINK = HEAD[:4] + ["KDDKKKKDDK"] + HEAD[5:]
HEAD_SLEEPY = HEAD_BLINK
HEAD_SAD = [      # droopy ears, dull eyes
    "..........",
    "KK......KK",
    "KPKKKKKKPK",
    "KKKKKKKKKK",
    "KEEKKKKEEK",
    "KKKKPPKKKK",
    ".KKKKKKKK.",
]
HEAD_MAD = [      # ears pinned back, narrowed furious eyes
    ".K......K.",
    "KKK....KKK",
    ".KKKKKKKK.",
    "KKKKKKKKKK",
    "KEKKKKKKEK",
    "KKKKPPKKKK",
    ".KKKKKKKK.",
]

TORSO = [         # horizontal torso, 18 x 5, white chest at front
    ".KKKDDDDDDDDDKKKK.",   # soft sheen along the upper back
    "KKKKKKKKKKKKKWWKKK",
    "KKKKKKKKKKKKKWWKKK",
    "KKKKKKKKKKKKKKKKKK",
    ".KKKKKKKKKKKKKKKK.",
]

TAIL_UP = [       # raised tail with white tip, 4 x 5
    ".WW.",
    ".KK.",
    ".KK.",
    "..KK",
    "..KK",
]
TAIL_UP2 = [      # waved variant
    "WW..",
    "KK..",
    ".KK.",
    ".KK.",
    "..KK",
]

LEGS_TOGETHER = [
    ".....KK.........KK........",
    ".....KK.........KK........",
    ".....KK.........KK........",
    ".....KWW........KWW.......",
]
LEGS_SPREAD = [
    "....KK..KK.....KK..KK.....",
    "....KK..KK.....KK..KK.....",
    "....KK..KK.....KK..KK.....",
    "....KWW.KWW....KWW.KWW....",
]
LEGS_CROUCH = [
    "..........................",
    "..........................",
    ".....KK.........KK........",
    ".....KWW........KWW.......",
]

BOWL_FOOD = [
    ".OOOO.",
    "GGGGGG",
    ".GGGG.",
]
BOWL_WATER = [
    ".BBBB.",
    "GGGGGG",
    ".GGGG.",
]

HEAD_DOWN = [     # profile head lowered into bowl, 7 x 5
    ".KK....",
    ".KKKK..",
    "KKKKKK.",
    "KKKKKKP",
    ".KKKKK.",
]


def _rehead(orig, hx, hy, head=None):
    """Replace a frame's 10x7 head region with the current HEAD, so these
    poses pick up the polished face and each species' ears."""
    head = head if head is not None else HEAD
    g = [list(r) for r in orig]
    for r in range(hy, hy + 7):
        if 0 <= r < len(g):
            for c in range(hx, hx + 10):
                if 0 <= c < len(g[r]):
                    g[r][c] = "."
    _blit(g, head, hx, hy)
    return _rows(g)


def _frame_stand(legs, tail, head=None, bob=0):
    head = head if head is not None else HEAD
    g = _blank()
    _blit(g, tail, 2, 7 + bob)
    _blit(g, TORSO, 3, 11 + bob)
    _blit(g, legs, 0, 16)
    _blit(g, head, 13, 4 + bob)
    return _rows(g)


def _frame_sit(head=None, tail="rest"):
    head = head if head is not None else HEAD
    g = _blank()
    body = [
        ".............KKKKKKKK.....",
        "...........KKKKKWWKKK.....",
        "..........DKKKKKWWKKK.....",
        ".........DKKKKKKWWKKK.....",
        ".........DKKKKKKKKKKK.....",
        "........DKKKKKKKKKKKK.....",
        "........DKKKKKKKKKKKK.....",
        "........KKKKKKKKKKKKK.....",
        "........KKKKKKKKKKKKK.....",
        "........KWWK...KWWK.......",
    ]
    _blit(g, body, 0, 10)
    if tail == "rest":     # lying along the ground, white tip
        _blit(g, ["WWKKKKK"], 1, 18)
    elif tail == "up":     # flicked up
        _blit(g, [".WW..", ".KK..", "KK...", "KKKKK"], 3, 14)
    elif tail == "flat":   # sad: flat and limp
        _blit(g, ["KKKKKKK", "WW....."], 1, 18)
    _blit(g, head, 13, 3)
    return _rows(g)


def _frame_groom(phase):
    rows = _frame_sit()
    g = [list(r) for r in rows]
    if phase == 0:  # paw raised to face, tongue out
        g[9][19] = "P"
        _blit(g, ["WW", "KW"], 19, 10)
    else:
        _blit(g, ["KW", "WW"], 19, 11)
    return _rows(g)


def _frame_bat(phase):
    rows = _frame_sit(tail="up")
    g = [list(r) for r in rows]
    if phase == 0:  # paw raised high
        _blit(g, ["WW.", "KW.", ".KK"], 20, 9)
    else:           # paw swiping low/forward
        _blit(g, [".KK", "KWW"], 20, 14)
    return _rows(g)


def _frame_squat(phase=0):
    # hunched, doing its business (side view), tail up, head tucked
    g = _blank()
    b = phase
    _blit(g, [".WW", ".KK", "KK.", "KKK"], 3, 6 + b)         # raised tail at back
    body = [
        "......DDDDDDDDD...",
        ".....KKKKKKKKKKKK.",
        "....KKKKKKKKKKKKKK",
        "....KKKKKKKKKKKKKK",
        "....KKKKKKKKKKKKKK",
        ".....KKKKKKKKKKKK.",
    ]
    _blit(g, body, 4, 9 + b)
    _blit(g, HEAD_DOWN, 17, 11 + b)                          # head lowered, front
    _blit(g, ["KK.....KK", "KWW....KWW"], 6, 17)             # tucked legs on the ground
    return _rows(g)


def _frame_flipoff(phase=0):
    # sitting, furious, one front paw thrust up with a single rude digit
    rows = _frame_sit(head=HEAD_MAD)
    g = [list(r) for r in rows]
    x = 19 + (1 if phase else 0)
    _blit(g, [
        ".W.",   # the offending claw
        ".K.",
        ".K.",
        "KKK",
        "KKK",
        "KKK",
        "KKK",
    ], x, 5)
    return _rows(g)


def _frame_crouch(phase):
    g = _blank()
    _blit(g, TORSO, 3, 13)
    _blit(g, LEGS_CROUCH, 0, 16)
    _blit(g, HEAD, 13, 6)
    if phase == 0:
        _blit(g, [".WW.", ".KK.", "KK..", "KK..", "KKKK"], 1, 9)
    else:
        _blit(g, ["WW..", "KK..", ".KK.", ".KK.", ".KKK"], 2, 9)
    return _rows(g)


POUNCE = [
    "..........................",
    "..........................",
    "................KK....KK..",
    "................KPK..KPK..",
    "................KKKKKKKK..",
    "...............KKKKKKKKKK.",
    "...............KEWKKKKEWK.",
    "...............KKKKPPKKKK.",
    "................KKKKKKKK..",
    "..........KKKKKKKKKKKKWW..",
    ".........KKKKKKKKKKKKKKW..",
    "........KKKKKKKKKKKKK.....",
    ".......KKKKKKKKKKKK.......",
    "..WWKKKKKKKKKKKK..........",
    "...KKKKKKKKKKK............",
    "......KK...KK.............",
    ".....KK...KK..............",
    "....WW...WW...............",
    "..........................",
    "..........................",
]


def _frame_scratch(phase):
    g = _blank()
    body = [
        ".............KKKKKKKK.....",
        ".............KKKKKKKK.....",
        ".............KKWWKKKK.....",
        ".............KKWWKKKK.....",
        ".............KKKKKKKK.....",
        ".............KKKKKKKK.....",
        ".............KKKKKKKK.....",
        "........KKKKKKKKKKKKK.....",
        ".........KKKKKKKKKKK......",
        ".........KKKK..KKKK.......",
        ".........KWWK..KWWK.......",
    ]
    _blit(g, body, 0, 9)
    _blit(g, ["...KKK", "KKKK..", "WW...."], 2, 16)    # tail curls along the ground
    _blit(g, HEAD, 13, 2)
    if phase == 0:
        _blit(g, ["KWW"], 21, 9)    # right paw up
        _blit(g, ["KWW"], 21, 13)   # left paw mid
    else:
        _blit(g, ["KWW"], 21, 11)
        _blit(g, ["KWW"], 21, 15)
    return _rows(g)


SLEEP1 = [
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    ".............KK..KK.......",
    "........KKKKKKKKKKKK......",
    "......KKKKKKKKKKKKKKK.....",
    ".....KKKKKKKKKKKKKKKKK....",
    "....KKKKKKKKKKKDDKKKKK....",
    "....KKKKKKKKKKKKKPKKKK....",
    "....KKWWKKKKKKKKKKKKK.....",
    ".....KKKKKKKKKKKKKK.......",
]
SLEEP2 = SLEEP1[:12] + [
    "..........................",
    ".............KK..KK.......",
    ".......KKKKKKKKKKKKK......",
    ".....KKKKKKKKKKKKKKKK.....",
    "....KKKKKKKKKKKDDKKKKK....",
    "....KKKKKKKKKKKKKPKKKK....",
    "....KKWWKKKKKKKKKKKKK.....",
    ".....KKKKKKKKKKKKKK.......",
]

LIE = [
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..............KK....KK....",
    "..............KPK..KPK....",
    "..............KKKKKKKK....",
    ".............KKKKKKKKKK...",
    ".............KEWKKKKEWK...",
    ".............KKKKPPKKKK...",
    "..............KKKKKKKK....",
    ".............KKKKKKKK.....",
    ".WW.......KKKKKKKKKKK.....",
    "..KKKKKKKKKKKKKKKKKKK.....",
    "...KKKKKKKKKKKKKKKKKK.....",
    "...KKKKKKKKKKKKKKKKKK.....",
    "....KKKKKKKKKKKKKKKKKWW...",
    "..........................",
    "..........................",
]


def _frame_tailchase(phase):
    """Head swung back over the rear, batting at its own flicking tail."""
    g = _blank()
    _blit(g, TORSO, 3, 11)
    _blit(g, LEGS_TOGETHER, 0, 16)
    _blit(g, HEAD, 1, 4)
    if phase == 0:
        _blit(g, ["WW.", "KK.", "KK.", ".KK", ".KK"], 12, 6)
    else:
        _blit(g, ["..WW", "..KK", ".KK.", ".KK.", "KK.."], 12, 6)
    return _rows(g)


def _frame_stretch():
    """Classic wake-up stretch: butt up, front low, paws forward."""
    g = _blank()
    _blit(g, [".WW", ".KK", "KK.", "KK."], 3, 4)        # tail up
    rump = [
        "....KKKK.....",
        "..KKKKKKKK...",
        ".KKKKKKKKKK..",
        ".KKKKKKKKKKK.",
        ".KKKKKKKKKKKK",
        ".KKKKKKKKKKKK",
    ]
    _blit(g, rump, 1, 7)
    _blit(g, ["KKKKKKK......", "KKKKKKKKKKKK."], 12, 12)  # back slope
    _blit(g, HEAD, 14, 10)                                 # head held low
    _blit(g, ["KKK", "KKK", "KKK", "KKK", "KKK", "KWW"], 3, 14)   # hind legs
    _blit(g, ["KKK......", ".KKKKKK..", "...KKKWW."], 16, 17)     # front legs stretched
    return _rows(g)


def _frame_eat(bowl, bob):
    g = _blank()
    _blit(g, [".WW", ".KK", "KK.", "KKK"], 3, 9)        # tail up
    body = [
        "...KKKKKKKKKKKK...",
        "..KKKKKKKKKKKKKKK.",
        "..KKKKKKKKKKKKKKKK",
    ]
    _blit(g, body, 2, 12)
    legs = [
        ".....KK........KK.........",
        ".....KK........KK.........",
        ".....KK........KK.........",
        ".....KK........KK.........",
        ".....KWW.......KWW........",
    ]
    _blit(g, legs, 0, 15)
    _blit(g, HEAD_DOWN, 16, 12 + bob)
    _blit(g, bowl, 19, 17)
    return _rows(g)


DANGLE = [
    "..........................",
    "..........KK....KK........",
    "..........KPK..KPK........",
    "..........KKKKKKKK........",
    ".........KKKKKKKKKK.......",
    ".........KEWKKKKEWK.......",
    ".........KKKKPPKKKK.......",
    "..........KKKKKKKK........",
    "..........KKKKKKKK........",
    "..........KKKWWKKK........",
    "..........KKKWWKKK........",
    "..........KKKKKKKK........",
    "..........KKKKKKKK.....KK.",
    "...........KKKKKK.....KK..",
    "...........KK..KK....KK...",
    "...........KK..KK...KK....",
    "...........WW..WW...KW....",
    "....................WW....",
    "..........................",
    "..........................",
]

FALL = [
    "..........................",
    "..........................",
    "....WW....................",
    "....KK....KK....KK........",
    ".....KK...KPK..KPK........",
    ".....KK...KKKKKKKK........",
    "......KK.KKKKKKKKKK.......",
    "......KKKKEWKKKKEWK.......",
    ".........KKKKPPKKKK.......",
    "..........KKKKKKKK........",
    "......KKKKKKKKKKKKKK......",
    "....KKKKKKKKKKKKKKKKKK....",
    "...KWKKKKKKKKKKKKKKKKWK...",
    "...WW..KK........KK..WW...",
    ".......KW........KW.......",
    ".......WW........WW.......",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
]

LAND = [
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..........................",
    "..............KK....KK....",
    "..............KPK..KPK....",
    "..............KKKKKKKK....",
    ".............KKKKKKKKKK...",
    ".............KDDKKKKDDK...",
    ".............KKKKPPKKKK...",
    ".WW...........KKKKKKKK....",
    "..KKK....KKKKKKKKKKKK.....",
    "..KKKKKKKKKKKKKKKKKKKK....",
    ".KWWKKKKKKKKKKKKKKKKKKK...",
    "..KWW...KWW....KWW..KWW...",
]

# small icons (8 x 8) for thought bubbles
ICON_FISH = [
    "........",
    "..OO....",
    ".OOOO.O.",
    "OOEOOOO.",
    ".OOOO.O.",
    "..OO....",
    "........",
    "........",
]
ICON_DROP = [
    "...B....",
    "...B....",
    "..BBB...",
    ".BBBBB..",
    ".BBBBB..",
    ".BBBWB..",
    "..BBB...",
    "........",
]
ICON_HEART = [
    "........",
    ".RR..RR.",
    "RRRRRRRR",
    "RRRRRRRR",
    ".RRRRRR.",
    "..RRRR..",
    "...RR...",
    "........",
]
ICON_VEG = [          # a little carrot, for what the herbivores would rather eat
    "..l.v...",
    ".vlvv...",
    "..OOO...",
    "..OOO...",
    "...OO...",
    "...O....",
    "........",
    "........",
]
ICON_ZZZ = [
    "........",
    ".WWWW...",
    "...W....",
    "..W.....",
    ".WWWW...",
    ".....WW.",
    "....W...",
    "...WWW..",
]

FRAMES = {
    "sit":       _frame_sit(),
    "sit_tail":  _frame_sit(tail="up"),
    "blink":     _frame_sit(head=HEAD_BLINK),
    "sad":       _frame_sit(head=HEAD_SAD, tail="flat"),
    "groom1":    _frame_groom(0),
    "groom2":    _frame_groom(1),
    "walk1":     _frame_stand(LEGS_SPREAD, TAIL_UP),
    "walk2":     _frame_stand(LEGS_TOGETHER, TAIL_UP2, bob=1),
    "walk3":     _frame_stand(LEGS_SPREAD, TAIL_UP2),
    "walk4":     _frame_stand(LEGS_TOGETHER, TAIL_UP, bob=1),
    "stand":     _frame_stand(LEGS_TOGETHER, TAIL_UP),
    "crouch1":   _frame_crouch(0),
    "crouch2":   _frame_crouch(1),
    "pounce":    _rehead(POUNCE, 15, 2),
    "bat1":      _frame_bat(0),
    "bat2":      _frame_bat(1),
    "scratch1":  _frame_scratch(0),
    "scratch2":  _frame_scratch(1),
    "sleep1":    SLEEP1,
    "sleep2":    SLEEP2,
    "lie":       _rehead(LIE, 13, 5),
    "eat1":      _frame_eat(BOWL_FOOD, 0),
    "eat2":      _frame_eat(BOWL_FOOD, 1),
    "drink1":    _frame_eat(BOWL_WATER, 0),
    "drink2":    _frame_eat(BOWL_WATER, 1),
    "dangle":    _rehead(DANGLE, 9, 1),
    "fall":      _rehead(FALL, 9, 3),
    "land":      _rehead(LAND, 13, 9, HEAD_BLINK),
    "tailchase1": _frame_tailchase(0),
    "tailchase2": _frame_tailchase(1),
    "stretch":   _frame_stretch(),
    "tuck0": [   # curled into a ball, for mid-air flips
        "..........................",
        "..........................",
        "..........................",
        "..........................",
        "..........................",
        "..........................",
        ".....KK......KK...........",
        "....KKKKKKKKKKKK..........",
        "...KKKKKKKKKKKKKK.........",
        "..KKKKKKKKKKKKKKKK........",
        "..KKKKKKKKKKKKKKKK........",
        "..KKWWKKKKKKKDDKKK........",
        "..KKKKKKKKKKKKKPKK........",
        "..KKKKKKKKKKKKKKKK........",
        "..KKWWKKKKKKKKKKKK........",
        "...KKKKKKKKKKKKKK.........",
        "....KKWWKKKKKKKK..........",
        ".....KKKKKKKKK............",
        "..........................",
        "..........................",
    ],
    "flipoff1": _frame_flipoff(0),
    "flipoff2": _frame_flipoff(1),
    "munch1":   _frame_eat([], 0),
    "munch2":   _frame_eat([], 1),
    "squat1":   _frame_squat(0),
    "squat2":   _frame_squat(1),
}

# a ball of yarn (10 x 10, deliberately asymmetric so rolling reads)
YARN_FRAMES_BASE = [
    "...RRRR...",
    "..RRRRWR..",
    ".RRWRRWRR.",
    ".RWRRRWRR.",
    ".RRWWRRRR.",
    ".RRRRWWRR.",
    ".RRWRRRWR.",
    "..RWRRRR..",
    "...RRRR...",
    ".......RR.",
]

LASER_DOT = [
    "........",
    "...RR...",
    "..RWWR..",
    ".RWWWWR.",
    ".RWWWWR.",
    "..RWWR..",
    "...RR...",
    "........",
]

# the little mouse (12 x 8 grids)
CRITTER_FRAMES = {
    "mouse1": [
        "............",
        "............",
        "......GG....",
        "...GGGGG....",
        "..GGGGGGGG..",
        "PPGGGGGGKGP.",
        "..GG...GG...",
        "............",
    ],
    "mouse2": [
        "............",
        "............",
        "......GG....",
        "...GGGGG....",
        "..GGGGGGGG..",
        "PPGGGGGGKGP.",
        "...GG...GG..",
        "............",
    ],
    "flat": [
        "............",
        "............",
        "............",
        "............",
        "............",
        "..PP........",
        "PPGGGGGGGG..",
        ".GGGGGGGGGP.",
    ],
    "bug1": [
        "............",
        "...n.KK.n...",
        "...KKKKKK...",
        "..KKKxKKK...",
        "..KKKxKKK...",
        "..KKKKKKK...",
        ".K.K.KK.K.K.",
        "............",
    ],
    "bug2": [
        "............",
        "...n.KK.n...",
        "...KKKKKK...",
        "..KKKxKKK...",
        "..KKKxKKK...",
        "..KKKKKKK...",
        "..KK.KK.KK..",
        "............",
    ],
    "bugflat": [
        "............",
        "............",
        "............",
        "............",
        "...n....n...",
        "..KKKxxKKK..",
        ".KKKKKKKKKK.",
        ".KKKKKKKKKK.",
    ],
}

# the wandering critter comes in a few flavours; bug is a distinct silhouette,
# vole/field-mouse are recolours of the mouse. pal overrides recolour 'G'.
CRITTER_TYPES = {
    "mouse": {"a": "mouse1", "b": "mouse2", "flat": "flat", "pal": None},
    "vole":  {"a": "mouse1", "b": "mouse2", "flat": "flat",
              "pal": {"G": "#9a6b4a", "P": "#e8b0a0"}},   # brown field mouse
    "white": {"a": "mouse1", "b": "mouse2", "flat": "flat",
              "pal": {"G": "#e8e8ee"}},                   # white mouse
    "bug":   {"a": "bug1", "b": "bug2", "flat": "bugflat", "pal": None},
}

# birds come in several colours so the sky isn't all one species (B = body)
BIRD_PALS = [
    None,                                  # sky-blue (default)
    {"B": "#e0584a"},                      # robin red
    {"B": "#f0c83a"},                      # canary yellow
    {"B": "#6ad0a0"},                      # green finch
    {"B": "#c98ae0"},                      # violet exotic
    {"B": "#eef0f4"},                      # white dove
]

ICONS = {"fish": ICON_FISH, "drop": ICON_DROP, "heart": ICON_HEART, "zzz": ICON_ZZZ,
         "veg": ICON_VEG}

# sanity-check the art at import time
for _name, _f in FRAMES.items():
    assert len(_f) == GH, f"frame {_name}: {len(_f)} rows"
    for _i, _r in enumerate(_f):
        assert len(_r) == GW, f"frame {_name} row {_i}: {len(_r)} cols"
        assert all(ch in PAL for ch in _r), f"frame {_name} row {_i}: bad char"
for _name, _f in CRITTER_FRAMES.items():
    assert len(_f) == 8, f"critter {_name}: {len(_f)} rows"
    for _i, _r in enumerate(_f):
        assert len(_r) == 12, f"critter {_name} row {_i}: {len(_r)} cols"
        assert all(ch in PAL for ch in _r), f"critter {_name} row {_i}: bad char"

# ---------------------------------------------------------------------------
# Furniture the user can place so the cat feels at home
# ---------------------------------------------------------------------------

DECOR_ART = {
    "bed": [
        "....mmmmmmmmmm....",
        "..mmuuuuuuuuuumm..",
        ".muuuuuuuuuuuuuum.",
        "nmuuiiiiiiiiiiuumn",
        "nnmmmmmmmmmmmmmmnn",
        ".nnnnnnnnnnnnnnnn.",
    ],
    "food": [
        "..OOOOOOOO..",
        ".OOOOOOOOOO.",
        "cccccccccccc",
        "cGGGGGGGGGGc",
        ".cGGGGGGGGc.",
        "..cccccccc..",
    ],
    "water": [
        "............",
        "..BBBBBBBB..",
        "cBBBBBBBBBBc",
        "cGGGGGGGGGGc",
        ".cGGGGGGGGc.",
        "..cccccccc..",
    ],
    "post": [
        "....RR......",
        "...RRRR.....",
        "...RRRR.....",
        "....mm......",
        "...tmmt.....",
        "...tmmt.....",
        "...tmmt.....",
        "...tmmt.....",
        "...tmmt.....",
        "...tmmt.....",
        "...tmmt.....",
        "...tmmt.....",
        "...tmmt.....",
        "...tmmt.....",
        "..nnnnnn....",
        ".nnnnnnnn...",
        "nnnnnnnnnn..",
        "nnnnnnnnnn..",
    ],
    "plant": [
        "...l..l.R...",
        "..lvllvv....",
        ".lvvvvvvj...",
        "lvvllvvjvj..",
        ".lvvvvvjj...",
        "..lvvvjj....",
        "...lvjj.....",
        "....vv......",
        "...tttt.....",
        "..mmmmmm....",
        "..mnttnm....",
        "..mntttm....",
        "...nnnn.....",
    ],
    "box": [
        "n..nnnn..nnnn..n",
        "nnnnnnnnnnnnnnnn",
        "nmmmmmmmmmmmmmmn",
        "nmnnnnnnnnnnnnmn",
        "nmnnnnnnnnnnnnmn",
        "nmnnnnnnnnnnnnmn",
        "nmnnnnnnnnnnnnmn",
        "nmmmmmmmmmmmmmmn",
        "nnnnnnnnnnnnnnnn",
        ".nnnnnnnnnnnnnn.",
    ],
    "litter": [
        "c" * 16,
        "c" + "s" * 14 + "c",
        "c" + "s" * 4 + "t" + "s" * 9 + "c",
        "c" + "s" * 9 + "t" + "s" * 4 + "c",
        "c" + "G" + "s" * 12 + "G" + "c",
        "c" + "G" * 14 + "c",
        "." + "c" + "G" * 12 + "c" + ".",
        "." * 2 + "c" * 12 + "." * 2,
    ],
    "grass": [
        "..l....l......l...",
        ".lvl..lvl....lvl..",
        ".vvl..vvl.R..vvl.l",
        "lvvvllvvvllyvvvllv",
        "vvvvvvvvvvvlvvvvvv",
        "vjvvjvvvjvvvvjvvvj",
        "jjvjjjvjjjvjjjvjjj",
        "tjtjtjtjtjtjtjtjtj",
    ],
    "tree": [
        "......llvvvj......",
        "....llvvvvvvjj....",
        "...lvvvvvvvvvjj...",
        "..lvvvvvvvvvvvjj..",
        ".lvvvvvvvvvvvvvjj.",
        ".lvvvllvvvvvvvvjj.",
        "lvvvvvvvvvvvvvvvjj",
        "lvvvvvvvvvvvvvvjjj",
        ".lvvvvvvvvvvvvjjj.",
        "..jvvvvvvvvvvjjj..",
        "...jjvvvvvvjjjj...",
        ".....jjvvvjjj.....",
        "." * 7 + "ntn" + "." * 8,
        "." * 7 + "ntn" + "." * 8,
        "." * 7 + "ntn" + "." * 8,
        "." * 6 + "nttn" + "." * 8,
        "." * 6 + "nttn" + "." * 8,
        "." * 5 + "nnttnn" + "." * 7,
        "." * 4 + "nnnnnnnn" + "." * 6,
        "." * 3 + "nnnnnnnnnn" + "." * 5,
    ],
    "pond": [
        "....bbbbbbbbbbbb....",
        "..bbBBBBBBBBBBBBbb..",
        ".bBBBBWBBBBBBBBBBBb.",
        "bBBBBBBBBBBBWBBBBBBb",
        "qBBBBBBBBBBBBBBBBBBq",
        ".qqBBBBBBBBBBBBBBqq.",
        "..qqqqqqqqqqqqqqqq..",
    ],
}

# label, what the cat does there, how many rows from the top are "solid"
# (used for the box the cat perches on)
DECOR_META = {
    "bed":   {"label": "🛏  Cat bed",        "act": "bedsleep"},
    "food":  {"label": "🍗  Food bowl",      "act": "munch"},
    "water": {"label": "💧  Water bowl",     "act": "lap"},
    "post":  {"label": "🪵  Scratching post", "act": "scratchpost"},
    "plant": {"label": "🪴  Potted plant",   "act": "plantbat"},
    "box":   {"label": "📦  Cardboard box",  "act": "boxhop"},
    "litter": {"label": "🚽  Litter box",    "act": "litter"},
    "grass": {"label": "🌿  Grass patch",    "act": "scenery"},
    "tree":  {"label": "🌳  Tree",           "act": "scenery"},
    "pond":  {"label": "💧  Pond",           "act": "scenery"},
}

for _name, _f in DECOR_ART.items():
    _w = len(_f[0])
    for _i, _r in enumerate(_f):
        assert len(_r) == _w, f"decor {_name} row {_i}: ragged ({len(_r)} vs {_w})"
        assert all(ch in PAL for ch in _r), f"decor {_name} row {_i}: bad char"


# ---------------------------------------------------------------------------
# Vegetation: every patch/tree/bush/flower gets a random variant when placed
# and GROWS from a sprout to full size over time.
# ---------------------------------------------------------------------------

def _veg(rows):
    """Pad a vegetation grid to a rectangle so hand-drawn art can't go ragged."""
    w = max(len(r) for r in rows)
    return [r.ljust(w, ".") for r in rows]


VEG_VARIANTS = {
    "grass": [
        DECOR_ART["grass"],                       # the original clumpy patch
        _veg([
            ".l...l....l..",
            "lvl.lvl..lvl.",
            "vvl.vvl.Rvvl.",
            "vvvlvvvlyvvvl",
            "vvvvvvvvvvvvv",
            "jvjjvjjvjjvjj",
            "tjtjtjtjtjtjt",
        ]),
        _veg([
            "..l.......l....",
            ".lvl.W...lvl...",
            ".vvl.y.W.vvl.W.",
            "lvvvl.lyl.vvvly",
            "vvvvvllvvlvvvvv",
            "jvjvjvjvjvjvjvj",
            "tjtjtjtjtjtjtjt",
        ]),
    ],
    "bush": [
        _veg([
            "...llvvvll...",
            "..lvvvvvvvl..",
            ".lvvvvvvvvvl.",
            "lvvvvvvvvvvvl",
            "lvvvjvvvjvvvl",
            ".jvvvvvvvvvj.",
            "..jjvvvvvjj..",
            "...jjjvjjj...",
            ".....ttt.....",
        ]),
        _veg([                                    # berry bush
            "...lvvvvl...",
            "..lvvRvvvl..",
            ".lvvvvvRvvl.",
            "lvRvvvvvvvRl",
            "lvvvvRvvvvvl",
            ".jvvvvvRvvj.",
            "..jvRvvvvj..",
            "...jjvvjj...",
            "....nttn....",
        ]),
        _veg([                                    # flowering bush
            "...lvyvvl...",
            "..lvRvvyvl..",
            ".lvvvyvvRvl.",
            "lvyvvvvvyvvl",
            "lvvvRvvvvvvl",
            ".jvvvyvRvvj.",
            "..jvvvvyvj..",
            "...jjvvjj...",
            "....nttn....",
        ]),
    ],
    "flower": [
        _veg([                                    # tulips
            ".R...O...z...R..",
            "RRR.OOO.zzz.RRR.",
            ".v...v...v...v..",
            ".v.l.v.l.v.l.v.l",
            ".vvl.vvl.vvl.vvl",
            ".v...v...v...v..",
            "tjtjtjtjtjtjtjtj",
        ]),
        _veg([                                    # daisies
            ".W...W...W..",
            "WyW.WyW.WyW.",
            ".W.l.W.l.W.l",
            ".v.l.v.l.v.l",
            ".vvl.vvl.vvl",
            ".v...v...v..",
            "tjtjtjtjtjtj",
        ]),
        _veg([                                    # mixed wildflowers
            ".y..R...z...W.",
            "lyl.RRR.zzz.WW.",
            ".v...v...v...v.",
            "lvl.lv..lvl.lv.",
            ".v...vl..v...v.",
            ".v...v...v...v.",
            "tjtjtjtjtjtjtjt",
        ]),
    ],
    "tree": [
        DECOR_ART["tree"],                        # the original round tree
        _veg([                                    # tall slim tree
            "...llvvj...",
            "..lvvvvvj..",
            ".lvvvvvvvj.",
            "lvvvvvvvvvj",
            ".lvvvvvvvj.",
            "..lvvvvvj..",
            ".lvvvvvvvj.",
            "lvvvvvvvvvj",
            ".lvvvvvvvj.",
            "..jvvvvvj..",
            "...jvvvj...",
            "....ntn....",
            "....ntn....",
            "....ntn....",
            "...nnttn...",
            "..nnnnnnnn.",
        ]),
        _veg([                                    # wide bushy tree
            "...lvvj..llvvj...",
            "..lvvvvjlvvvvvj..",
            ".lvvvvvvvvvvvvvj.",
            "lvvvvvvvvvvvvvvvj",
            "lvvvllvvvvvllvvvj",
            "lvvvvvvvvvvvvvvvj",
            ".jvvvvvvvvvvvvvj.",
            "..jjvvvvvvvvvjj..",
            "...jjjvvvvvjjj...",
            ".....jjvvjjj.....",
            "........ntn......",
            "........ntn......",
            ".......nnttn.....",
            "......nnnnnnnn...",
        ]),
    ],
}

# bush & flower are brand-new kinds — register a base grid + menu metadata so
# they validate and behave everywhere the older decor kinds do.
DECOR_ART.setdefault("bush", VEG_VARIANTS["bush"][0])
DECOR_ART.setdefault("flower", VEG_VARIANTS["flower"][0])
DECOR_META["bush"] = {"label": "🌳  Bush", "act": "scenery"}
DECOR_META["flower"] = {"label": "🌸  Flowers", "act": "scenery"}

VEG_GROW_KINDS = set(VEG_VARIANTS)          # have variants AND grow in over time
EDIBLE_VEG = ("grass", "plant", "bush")     # herbivores graze/browse these
VEG_GROW_SECS = {"grass": 18.0, "flower": 24.0, "bush": 40.0, "tree": 85.0}

for _name, _variants in VEG_VARIANTS.items():
    for _vi, _grid in enumerate(_variants):
        _w = len(_grid[0])
        for _i, _r in enumerate(_grid):
            assert len(_r) == _w, f"veg {_name}#{_vi} row {_i}: ragged"
            assert all(ch in PAL for ch in _r), f"veg {_name}#{_vi} row {_i}: bad char"

# ---------------------------------------------------------------------------
# Birds (fly across the top; the cat tries to catch them)
# ---------------------------------------------------------------------------

BIRD_FRAMES = {
    "up": [
        "....BB......",
        "...BBBB.....",
        "..BBBBBB....",
        ".BBBBBBKBO..",
        "..BBBBBB....",
        "...B..B.....",
        "............",
        "............",
    ],
    "down": [
        "............",
        "............",
        "..BBBBBB....",
        ".BBBBBBKBO..",
        "..BBBBBBB...",
        "...BBBB.....",
        "....BB......",
        "...B..B.....",
    ],
}

# the stork that delivers mammal babies (carries a little bundle)
STORK_FRAMES = {
    "up": [
        "......WW........",
        ".....WWWWW......",
        "....WWWWWWW.....",
        "...WWWWWWWWWO...",
        "....WWWWWWW.....",
        ".....WW.WW......",
        "......O.O.......",
        "......O.O.......",
        ".....uuuu.......",
        ".....uuuu.......",
        "......uu........",
        "................",
    ],
    "down": [
        "................",
        "................",
        "....WWWWW.......",
        "...WWWWWWWWWO...",
        "...WWWWWWWW.....",
        "....WWWWWW......",
        ".....WW.WW......",
        "......O.O.......",
        "......O.O.......",
        ".....uuuu.......",
        ".....uuuu.......",
        "......uu........",
    ],
}

# floor messes (when there is no clean litter box)
MESS_ART = {
    "poop": [
        "...tt...",
        "..tttt..",
        ".tnnnnt.",
        ".nnnnnn.",
        "..tttt..",
    ],
    "pee": [
        "..........",
        "...yyyy...",
        ".yyyyyyyy.",
        "..yyyyyy..",
    ],
}

# ---------------------------------------------------------------------------
# Costumes: palette tweak + accessory overlays (front=on top, behind=behind)
# ---------------------------------------------------------------------------

_CROWN = [
    "y..y..y..y",
    "yyyyyyyyyy",
    "yxyyyyyyxy",
    "yyyyyyyyyy",
]
_WIZHAT = [
    "....z.....",
    "...zzz....",
    "...zzz....",
    "..zzzzz...",
    "..zzyzz...",
    ".zzzzzzz..",
    "zzzzzzzzz.",
    "zzzzzzzzz.",
]
_HORNS = [
    "x........x",
    "xx......xx",
    ".x......x.",
]
def _mirror(left):
    return left + left[::-1]


def _compose_arts(arts):
    """Overlay several pixel grids centered on a common canvas (for combining
    a species feature with a costume accessory). Returns None if all empty."""
    arts = [a for a in arts if a]
    if not arts:
        return None
    w = max(len(a[0]) for a in arts)
    h = max(len(a) for a in arts)
    g = [["."] * w for _ in range(h)]
    for a in arts:
        ox = (w - len(a[0])) // 2
        oy = (h - len(a)) // 2
        for r, row in enumerate(a):
            for c, ch in enumerate(row):
                if ch != ".":
                    g[oy + r][ox + c] = ch
    return ["".join(x) for x in g]


# symmetric wings/legs (each row = a 14/15-char left half, mirrored to full width)
_BATWINGS = [_mirror(s) for s in (
    "K.............",
    "KK............",
    "DKK...........",
    "DDKKK.........",
    "DDDDKKK.......",
    "DDDDDDKKKK....",
    "DDDDDDDDDKKK..",
    ".DDDDDDDDDDDK.",
    "..DDDDDDDDDD..",
    "....DDDDDD....",
)]
_SPIDERLEGS = [_mirror(s) for s in (
    "K..............",
    ".KK............",
    "...KK..........",
    ".....KKK.......",
    ".......KKKK....",
    "..........KKK..",
    ".............K.",
    "...............",
)]

COSTUMES = {
    "none":   {"pal": {},                  "front": None,    "behind": None},
    "bat":    {"pal": {"E": "#ff5d3a"},    "front": None,    "behind": _BATWINGS},
    "spider": {"pal": {"E": "#ff3a3a"},    "front": None,    "behind": _SPIDERLEGS},
    "wizard": {"pal": {},                  "front": _WIZHAT, "behind": None},
    "king":   {"pal": {},                  "front": _CROWN,  "behind": None},
    "devil":  {"pal": {"E": "#ff5d3a"},    "front": _HORNS,  "behind": None},
}

for _grp, _d in (("bird", BIRD_FRAMES), ("mess", MESS_ART), ("stork", STORK_FRAMES)):
    for _name, _f in _d.items():
        _w = len(_f[0])
        for _i, _r in enumerate(_f):
            assert len(_r) == _w, f"{_grp} {_name} row {_i}: ragged"
            assert all(ch in PAL for ch in _r), f"{_grp} {_name} row {_i}: bad char"
for _cn, _c in COSTUMES.items():
    for _slot in ("front", "behind"):
        _art = _c[_slot]
        if _art is not None:
            _w = len(_art[0])
            for _i, _r in enumerate(_art):
                assert len(_r) == _w, f"costume {_cn}/{_slot} row {_i}: ragged"
                assert all(ch in PAL for ch in _r), f"costume {_cn}/{_slot} row {_i}: bad char"


# rotated frames (added after validation; their dimensions differ)
def _rot_ccw(rows):
    h, w = len(rows), len(rows[0])
    return ["".join(rows[c][w - 1 - r] for c in range(h)) for r in range(w)]


def _rot_cw(rows):
    h, w = len(rows), len(rows[0])
    return ["".join(rows[h - 1 - c][r] for c in range(h)) for r in range(w)]


def _rot_180(rows):
    return [r[::-1] for r in reversed(rows)]


def _center_pad(rows, out_w=26, out_h=20, cx=9.5, cy=11.5):
    """Re-pad a frame so its content bbox is centered on (cx, cy).

    Keeps the flip rotations concentric, so the spinning ball doesn't wobble.
    """
    coords = [(r, c) for r, row in enumerate(rows)
              for c, ch in enumerate(row) if ch != "."]
    r0, r1 = min(r for r, _ in coords), max(r for r, _ in coords)
    c0, c1 = min(c for _, c in coords), max(c for _, c in coords)
    h, w = r1 - r0 + 1, c1 - c0 + 1
    top = max(0, min(out_h - h, round(cy - h / 2)))
    left = max(0, min(out_w - w, round(cx - w / 2)))
    g = [["."] * out_w for _ in range(out_h)]
    for r in range(h):
        for c in range(w):
            ch = rows[r0 + r][c0 + c]
            if ch != ".":
                g[top + r][left + c] = ch
    return ["".join(x) for x in g]


FRAMES["climb1"] = _rot_ccw(FRAMES["walk1"])   # head up, wall to the right
FRAMES["climb2"] = _rot_ccw(FRAMES["walk3"])
FRAMES["tuck0"] = _center_pad(FRAMES["tuck0"])
FRAMES["tuck90"] = _center_pad(_rot_ccw(FRAMES["tuck0"]))   # backflip spins ccw
FRAMES["tuck180"] = _center_pad(_rot_180(FRAMES["tuck0"]))
FRAMES["tuck270"] = _center_pad(_rot_cw(FRAMES["tuck0"]))


def _egg_frame(phase=0, crack=0):
    # a speckled egg in fixed colors (c/m/t) so every species' egg looks alike
    g = _blank()
    egg = [
        "..cccc..",
        ".cccccc.",
        ".cccccc.",
        "cccccccc",
        "cccmcccc",
        "cccccccc",
        "ccccccmc",
        "cccccccc",
        "cccccccc",
        ".cccccc.",
        ".cccccc.",
        "..cccc..",
    ]
    _blit(g, egg, 9 + (1 if phase else 0), 7)
    if crack:
        _blit(g, ["..tt..", ".t..t.", "t...t."], 10, 11)
    return _rows(g)


FRAMES["egg1"] = _egg_frame(0)
FRAMES["egg2"] = _egg_frame(1)
FRAMES["eggcrack"] = _egg_frame(0, crack=1)
YARN_FRAMES = [YARN_FRAMES_BASE, _rot_cw(YARN_FRAMES_BASE),
               _rot_180(YARN_FRAMES_BASE), _rot_ccw(YARN_FRAMES_BASE)]

# ---------------------------------------------------------------------------
# Species: different animals built by swapping the EARS on the shared face,
# plus a palette, a signature accessory, a voice, and a way of arriving.
# ---------------------------------------------------------------------------

_FACE = [".KKKKKKKK.", "KKKKKKKKKK", "KEWKKKKWEK", "KKKDPPDKKK", ".KKKKKKKK."]
_FACE_BLINK = [".KKKKKKKK.", "KKKKKKKKKK", "KDDKKKKDDK", "KKKDPPDKKK", ".KKKKKKKK."]
_FACE_SAD = [".KKKKKKKK.", "KKKKKKKKKK", "KEEKKKKEEK", "KKKKPPKKKK", ".KKKKKKKK."]
_FACE_MAD = [".KKKKKKKK.", "KKKKKKKKKK", "KEKKKKKKEK", "KKKKPPKKKK", ".KKKKKKKK."]

SPECIES_EARS = {
    "cat":     [".DKK..KKD.", ".KPK..KPK."],
    "dog":     ["KKK....KKK", "KKKK..KKKK"],   # big floppy
    "dragon":  ["K.K....K.K", ".KK....KK."],   # little horns
    "bunny":   [".KK....KK.", ".KP....PK."],   # tall straight ears, pink inner
    "fox":     ["DKK....KKD", "KKKK..KKKK"],   # big pointy
    "goat":    [".KK....KK.", ".KK....KK."],   # upright (horns added on top)
    "pig":     ["KK......KK", ".KK....KK."],   # triangle floppy
    "cow":     ["KKK....KKK", "KKKK..KKKK"],   # floppy (horns on top)
    "bear":    ["KKKK..KKKK", "KKKK..KKKK"],   # big round
    "panda":   ["DDDD..DDDD", "DDDD..DDDD"],   # round black ears (D=black)
    "frog":    ["KKK....KKK", ".KK....KK."],   # eye bumps
    "penguin": ["..K....K..", "..K....K.."],   # barely any
    "chick":   [".K......K.", ".K......K."],   # tiny tuft
    "hamster": ["KKK....KKK", "KKKK..KKKK"],   # round
}


# muzzle/snout/beak per species (10x5) so they don't all wear a cat's face.
# row 2 is the eye row (swapped per mood); rows 3-4 are the species' nose/mouth.
SPECIES_FACE = {
    "chick":   [".KKKKKKKK.", "KKKKKKKKKK", "KEWKKKKWEK", "KKKOOOOKKK", ".KKOOOOKK."],
    "penguin": [".KKKKKKKK.", "KKKKKKKKKK", "KEWKKKKWEK", "KKKOOOOKKK", ".KKOOOOKK."],
    "pig":     [".KKKKKKKK.", "KKKKKKKKKK", "KEWKKKKWEK", "KKPPPPPPKK", "KKPDPPDPKK"],
    "cow":     [".KKKKKKKK.", "KKKKKKKKKK", "KEWKKKKWEK", "KKWWWWWWKK", "KKWDWWDWKK"],
    "dog":     [".KKKKKKKK.", "KKKKKKKKKK", "KEWKKKKWEK", "KKKWWWWKKK", "KKKKDDKKKK"],
    "fox":     [".KKKKKKKK.", "KKKKKKKKKK", "KEWKKKKWEK", "KKKKWWKKKK", "KKKKDDKKKK"],
    "bunny":   [".KKKKKKKK.", "KKKKKKKKKK", "KEWKKKKWEK", "KKKDPPDKKK", "KKKKWWKKKK"],
    "frog":    [".KKKKKKKK.", "KKKKKKKKKK", "KEWKKKKWEK", "KKKKKKKKKK", "KWWWWWWWWK"],
}


def _faces_for(face):
    """Derive the (normal, blink, sad, mad) faces from a species' normal face by
    swapping only the eye row, so the muzzle/beak stays put across moods."""
    blink = face[:2] + ["KDDKKKKDDK"] + face[3:]
    sad = face[:2] + ["KEEKKKKEEK"] + face[3:]
    mad = face[:2] + ["KEKKKKKKEK"] + face[3:]
    return (face, blink, sad, mad)


def _heads_for(ears, faces=None):
    f, b, s, m = faces or (_FACE, _FACE_BLINK, _FACE_SAD, _FACE_MAD)
    return (ears + f, ears + b, ears + s, ears + m)


def species_frame_overrides(species):
    """Rebuild the head-dependent frames with this species' ears + muzzle."""
    if species == "cat" or species not in SPECIES_EARS:
        return {}
    global HEAD, HEAD_BLINK, HEAD_SAD, HEAD_MAD
    save = (HEAD, HEAD_BLINK, HEAD_SAD, HEAD_MAD)
    faces = _faces_for(SPECIES_FACE[species]) if species in SPECIES_FACE else None
    HEAD, HEAD_BLINK, HEAD_SAD, HEAD_MAD = _heads_for(SPECIES_EARS[species], faces)
    try:
        ov = {
            "sit": _frame_sit(), "sit_tail": _frame_sit(tail="up"),
            "blink": _frame_sit(head=HEAD_BLINK),
            "sad": _frame_sit(head=HEAD_SAD, tail="flat"),
            "groom1": _frame_groom(0), "groom2": _frame_groom(1),
            "walk1": _frame_stand(LEGS_SPREAD, TAIL_UP),
            "walk2": _frame_stand(LEGS_TOGETHER, TAIL_UP2, bob=1),
            "walk3": _frame_stand(LEGS_SPREAD, TAIL_UP2),
            "walk4": _frame_stand(LEGS_TOGETHER, TAIL_UP, bob=1),
            "stand": _frame_stand(LEGS_TOGETHER, TAIL_UP),
            "crouch1": _frame_crouch(0), "crouch2": _frame_crouch(1),
            "bat1": _frame_bat(0), "bat2": _frame_bat(1),
            "scratch1": _frame_scratch(0), "scratch2": _frame_scratch(1),
            "tailchase1": _frame_tailchase(0), "tailchase2": _frame_tailchase(1),
            "stretch": _frame_stretch(),
            "flipoff1": _frame_flipoff(0), "flipoff2": _frame_flipoff(1),
            "pounce": _rehead(POUNCE, 15, 2),
            "lie": _rehead(LIE, 13, 5),
            "dangle": _rehead(DANGLE, 9, 1),
            "fall": _rehead(FALL, 9, 3),
            "land": _rehead(LAND, 13, 9, HEAD_BLINK),
        }
        ov["climb1"] = _rot_ccw(ov["walk1"])
        ov["climb2"] = _rot_ccw(ov["walk3"])
    finally:
        HEAD, HEAD_BLINK, HEAD_SAD, HEAD_MAD = save
    return ov


# wings for the dragon (reuse the bat-wing silhouette), behind the body
_DRAGON_WINGS = [_mirror(s) for s in (
    "v.............",
    "vv............",
    "jvv...........",
    "jjvv..........",
    "jjjvvv........",
    "jjjjjvvv......",
    "jjjjjjjvvv....",
    ".jjjjjjjjjjv..",
    "..jjjjjjjjj...",
    "....jjjjjj....",
)]

# little horns worn on the head (front accessory)
_GOAT_HORNS = ["m........m", ".m......m.", ".m......m."]
_COW_HORNS = ["c........c", "cc......cc", ".........."]

# species: pal override, ears(implicit), accessories, voice, how it's born
SPECIES = {
    "cat":     {"name": "Cat",     "pal": {},
                "behind": None, "voice": "meow",   "spawn": "stork"},
    "dog":     {"name": "Dog",     "pal": {"K": "#9b6b3e", "D": "#6f4a28",
                                           "W": "#efe6d4", "E": "#4a3018"},
                "behind": None, "voice": "woof",   "spawn": "stork"},
    "dragon":  {"name": "Dragon",  "pal": {"K": "#3f8a4a", "D": "#2c6a36",
                                           "W": "#e6e85a", "E": "#ffd24a"},
                "behind": _DRAGON_WINGS, "voice": "roar", "spawn": "egg"},
    "bunny":   {"name": "Bunny",   "pal": {"K": "#e7e7ef", "D": "#c3c3d2",
                                           "W": "#f7b9cb", "E": "#ff6f8f"},
                "behind": None, "voice": "squeak", "spawn": "stork"},
    "fox":     {"name": "Fox",     "pal": {"K": "#e08a3c", "D": "#b5651a",
                                           "W": "#f7f2e8", "E": "#3a2410"},
                "behind": None, "voice": "yip",    "spawn": "egg"},
    "goat":    {"name": "Goat",    "pal": {"K": "#e8e2cc", "D": "#bfb79a",
                                           "W": "#fffaf0", "E": "#7a5a2a"},
                "behind": None, "front": _GOAT_HORNS, "voice": "baa", "spawn": "stork"},
    "pig":     {"name": "Pig",     "pal": {"K": "#f0a0b4", "D": "#d77f95",
                                           "W": "#ffd5e0", "E": "#6a3040"},
                "behind": None, "voice": "oink",   "spawn": "stork"},
    "cow":     {"name": "Cow",     "pal": {"K": "#f0f0f4", "D": "#3a3a44",
                                           "W": "#fffaf2", "E": "#2a1a10"},
                "behind": None, "front": _COW_HORNS, "voice": "moo", "spawn": "stork"},
    "bear":    {"name": "Bear",    "pal": {"K": "#7a5236", "D": "#5a3a22",
                                           "W": "#caa46a", "E": "#2a1a0a"},
                "behind": None, "voice": "roar",   "spawn": "stork"},
    "panda":   {"name": "Panda",   "pal": {"K": "#f2f2f4", "D": "#22222a",
                                           "W": "#ffffff", "E": "#22222a"},
                "behind": None, "voice": "squeak", "spawn": "stork"},
    "frog":    {"name": "Frog",    "pal": {"K": "#5aa84a", "D": "#3f8a36",
                                           "W": "#d8e84a", "E": "#16161e"},
                "behind": None, "voice": "ribbit", "spawn": "egg"},
    "penguin": {"name": "Penguin", "pal": {"K": "#2a2a36", "D": "#16161e",
                                           "W": "#f4f4f8", "E": "#e8a83a"},
                "behind": None, "voice": "squeak", "spawn": "egg"},
    "chick":   {"name": "Chick",   "pal": {"K": "#f4d24a", "D": "#d8b03a",
                                           "W": "#fffbe6", "E": "#2a2a2a"},
                "behind": None, "voice": "squeak", "spawn": "egg"},
    "hamster": {"name": "Hamster", "pal": {"K": "#d8a86a", "D": "#b5854a",
                                           "W": "#f4ecd8", "E": "#2a1a0a"},
                "behind": None, "voice": "squeak", "spawn": "stork"},
}

# who eats what, in the ecosystem
SPECIES_DIET = {
    "cat": "carn", "dog": "carn", "dragon": "carn", "fox": "carn", "bear": "carn",
    "frog": "carn", "penguin": "carn", "pig": "carn",          # omnivores hunt too
    "goat": "herb", "cow": "herb", "bunny": "herb", "hamster": "herb",
    "chick": "herb", "panda": "herb",
}

SPECIES_EMOJI = {
    "cat": "🐈", "dog": "🐕", "dragon": "🐉", "bunny": "🐇", "fox": "🦊",
    "goat": "🐐", "pig": "🐷", "cow": "🐄", "bear": "🐻", "panda": "🐼",
    "frog": "🐸", "penguin": "🐧", "chick": "🐤", "hamster": "🐹",
}

# how each animal MOVES — so a frog doesn't trot like a cat
SPECIES_GAIT = {
    "bunny": "hop", "frog": "hop", "hamster": "hop", "chick": "hop",
    "penguin": "waddle", "pig": "waddle", "goat": "waddle",
    "cow": "waddle", "bear": "waddle", "panda": "waddle",
    "dragon": "flutter",
}                                  # cat / dog / fox fall through to a normal walk

# What each species naturally DOES, so a cow doesn't pounce on birds. These gate
# the main pet's cat-built behaviours; anything not granted simply never fires,
# leaving the universal set (idle/wander/lie/groom/sleep/beg/eat-from-bowl/come/nap).
#   hunt     - stalk & pounce the cursor and the wandering critter (predators)
#   birds    - leap to snatch a passing bird out of the air (agile predators)
#   toy      - chase & bat the yarn ball
#   laser    - chase the laser dot
#   climb    - scale the side of a window
#   scratch  - claw window edges / scratch post, paw desktop icons & the plant
#   box      - hop into and perch on the cardboard box
#   tailchase- spin chasing its own tail
#   zoomies  - sudden sprint back and forth
#   flip     - backflip trick
#   litter   - uses the litter box / relieves itself on the floor
SPECIES_TRAITS = {
    "cat":     {"hunt", "birds", "toy", "laser", "climb", "scratch", "box",
                "tailchase", "zoomies", "flip", "litter"},
    "dog":     {"hunt", "birds", "toy", "laser", "tailchase", "zoomies", "flip"},
    "fox":     {"hunt", "birds", "climb", "tailchase", "zoomies", "flip"},
    "dragon":  {"hunt", "birds", "zoomies", "flip"},
    "bear":    {"hunt", "climb"},
    "frog":    {"hunt"},
    "goat":    {"climb", "zoomies"},
    "bunny":   {"box", "zoomies"},
    "hamster": {"box", "climb", "zoomies"},
    "panda":   {"climb"},
    "penguin": set(),
    "pig":     set(),
    "cow":     set(),
    "chick":   set(),
}


def traits_of(species):
    return SPECIES_TRAITS.get(species, set())


def gait_of(species):
    return SPECIES_GAIT.get(species, "walk")


def gait_render(species, anim, t, scale, moving):
    """Return (vertical_offset, anim_override) so movement reads per-species."""
    g = gait_of(species)
    if g == "flutter":             # birds/dragons hover and bob, always airborne
        off = -(3.0 + 1.6 * math.sin(t * 11)) * scale
        return off, ("sit" if anim in ("walk", "run", "idle") else None)
    if not moving:
        return 0.0, None
    if g == "hop":                 # spring up in arcs; tuck the legs (no walk cycle)
        return -abs(math.sin(t * 7.5)) * 7 * scale, "crouch1"
    if g == "waddle":              # low rocking bob
        return -abs(math.sin(t * 9)) * 2.2 * scale, None
    return 0.0, None

# breeding-unlock abilities (mutations passed to / rolled for babies)
ABILITIES = ("swift", "big", "tiny", "glow")

# a little pink bow worn by females (front overlay)
_BOW = ["u.uu.u", ".uiiu.", "u.uu.u"]


def _blend_hex(a, b):
    """Average two #rrggbb colors, with a small random mutation."""
    out = "#"
    for i in (1, 3, 5):
        va, vb = int(a[i:i + 2], 16), int(b[i:i + 2], 16)
        v = (va + vb) // 2 + random.randint(-18, 18)
        out += f"{max(0, min(255, v)):02x}"
    return out


def _shiny_pal():
    return {"K": "#e8c84a", "D": "#c79a2a", "W": "#fff6c8", "E": "#ff5d76"}


def breed_genes(g1, g2):
    """Mix two animals' genes into a baby's — with rare shiny/ability/ultra rolls."""
    keys = ("K", "D", "W", "E")
    p1, p2 = g1.get("pal", {}), g2.get("pal", {})
    pal = {}
    for k in keys:
        c1, c2 = p1.get(k), p2.get(k)
        if c1 and c2:
            pal[k] = _blend_hex(c1, c2)
        elif c1 or c2:
            pal[k] = c1 or c2
    shiny = random.random() < 0.05 or (g1.get("shiny") and g2.get("shiny"))
    ultra = random.random() < 0.012
    ability = None
    if random.random() < 0.30:
        ability = random.choice([a for a in (g1.get("ability"), g2.get("ability"))
                                 if a] or list(ABILITIES))
    elif random.random() < 0.12:
        ability = random.choice(ABILITIES)
    size = (g1.get("size", 1.0) + g2.get("size", 1.0)) / 2
    if ultra:
        shiny = True
        ability = "glow"
        size *= 1.25
    if ability == "big":
        size = min(1.6, size * 1.25)
    elif ability == "tiny":
        size = max(0.6, size * 0.8)
    genes = {"pal": pal, "shiny": shiny, "ability": ability,
             "size": round(max(0.5, min(1.8, size)), 2), "ultra": ultra}
    return genes


def base_genes(species):
    return {"pal": dict(SPECIES[species]["pal"]), "shiny": False,
            "ability": None, "size": 1.0, "ultra": False}

# animations: name -> (frame list, fps, loop)
ANIMS = {
    "idle":    (["sit", "sit", "sit_tail", "sit", "blink", "sit", "sit_tail", "sit"], 1.6, True),
    "sad":     (["sad", "sad", "sad", "blink"], 1.0, True),
    "groom":   (["groom1", "groom2"], 2.5, True),
    "walk":    (["walk1", "walk2", "walk3", "walk4"], 6, True),
    "run":     (["walk1", "walk2", "walk3", "walk4"], 11, True),
    "stalk":   (["crouch1", "crouch2"], 2.2, True),
    "pounce":  (["pounce"], 1, True),
    "bat":     (["bat1", "bat2"], 4.5, True),
    "scratch": (["scratch1", "scratch2"], 4, True),
    "sleep":   (["sleep1", "sleep2"], 0.9, True),
    "lie":     (["lie"], 1, True),
    "eat":     (["eat1", "eat2"], 3, True),
    "drink":   (["drink1", "drink2"], 3, True),
    "dangle":  (["dangle"], 1, True),
    "fall":    (["fall"], 1, True),
    "land":    (["land"], 1, True),
    "tailchase": (["tailchase1", "tailchase2"], 5, True),
    "stretch": (["stretch"], 1, True),
    "blink":   (["blink"], 1, True),
    "climb":   (["climb1", "climb2"], 4, True),
    "flip":    (["tuck0", "tuck90", "tuck180", "tuck270"], 11, True),
    "flipoff": (["flipoff1", "flipoff2"], 5, True),
    "munch":   (["munch1", "munch2"], 3, True),
    "potty":   (["squat1", "squat2"], 2.5, True),
    "birdwatch": (["crouch1", "crouch1", "crouch2"], 3, True),
    "egg":     (["egg1", "egg2"], 2.5, True),
    "hatch":   (["eggcrack", "egg2", "eggcrack"], 6, True),
    # static single-frame poses used as gait_render anim overrides
    "sit":     (["sit"], 1, True),       # flutter (dragon hovers in a sit pose)
    "crouch1": (["crouch1"], 1, True),   # hop (legs tucked between bounces)
}


def _scale_ratio(scale):
    """Integer (zoom, subsample) approximating a possibly-fractional px/cell."""
    from fractions import Fraction
    fr = Fraction(scale).limit_denominator(4)
    return max(1, fr.numerator), max(1, fr.denominator)


def frame_to_photo(rows, scale, flip=False, pal=None):
    """Build a tk.PhotoImage from a string grid ('.' becomes the key color).

    scale may be fractional (for age-based growth); rendered via zoom/subsample.
    """
    pal = pal or PAL
    if flip:
        rows = [r[::-1] for r in rows]
    data = " ".join(
        "{" + " ".join(pal[ch] for ch in row) + "}" for row in rows
    )
    img = tk.PhotoImage(width=len(rows[0]), height=len(rows))
    img.put(data)
    z, sub = _scale_ratio(scale)
    if z > 1:
        img = img.zoom(z, z)
    if sub > 1:
        img = img.subsample(sub)
    return img


# ---------------------------------------------------------------------------
# Win32 helpers
# ---------------------------------------------------------------------------

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
try:
    dwmapi = ctypes.windll.dwmapi
except OSError:
    dwmapi = None

user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.SendMessageTimeoutW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM,
                                       wt.UINT, wt.UINT, ctypes.POINTER(ctypes.c_size_t)]
user32.SendMessageTimeoutW.restype = ctypes.c_ssize_t
user32.FindWindowW.argtypes = [wt.LPCWSTR, wt.LPCWSTR]
user32.FindWindowW.restype = wt.HWND
user32.FindWindowExW.argtypes = [wt.HWND, wt.HWND, wt.LPCWSTR, wt.LPCWSTR]
user32.FindWindowExW.restype = wt.HWND
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.VirtualAllocEx.argtypes = [wt.HANDLE, wt.LPVOID, ctypes.c_size_t, wt.DWORD, wt.DWORD]
kernel32.VirtualAllocEx.restype = wt.LPVOID
kernel32.VirtualFreeEx.argtypes = [wt.HANDLE, wt.LPVOID, ctypes.c_size_t, wt.DWORD]
kernel32.ReadProcessMemory.argtypes = [wt.HANDLE, wt.LPCVOID, wt.LPVOID, ctypes.c_size_t,
                                       ctypes.POINTER(ctypes.c_size_t)]

WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def set_dpi_aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def cursor_pos():
    pt = wt.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def work_area():
    r = wt.RECT()
    user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0)  # SPI_GETWORKAREA
    return r.left, r.top, r.right, r.bottom


def window_rect(hwnd):
    """Visual rect of a window (DWM extended frame bounds when available)."""
    if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
        return None
    r = wt.RECT()
    got = False
    if dwmapi is not None:
        if dwmapi.DwmGetWindowAttribute(wt.HWND(hwnd), 9, ctypes.byref(r),
                                        ctypes.sizeof(r)) == 0:  # EXTENDED_FRAME_BOUNDS
            got = True
    if not got and not user32.GetWindowRect(hwnd, ctypes.byref(r)):
        return None
    return r.left, r.top, r.right, r.bottom


_SKIP_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
                 "Windows.UI.Core.CoreWindow", "XamlExplorerHostIslandWindow",
                 "NotifyIconOverflowWindow", "TopLevelWindowForOverflowXamlIsland"}


def list_app_windows(exclude_hwnd=0):
    """Visible, titled, non-cloaked top-level app windows, in z-order (top first)."""
    out = []

    @WNDENUMPROC
    def cb(hwnd, _):
        try:
            if hwnd == exclude_hwnd:
                return True
            if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
                return True
            if user32.GetWindowTextLengthW(hwnd) == 0:
                return True
            buf = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, buf, 64)
            if buf.value in _SKIP_CLASSES:
                return True
            if dwmapi is not None:
                cloaked = wt.DWORD(0)
                dwmapi.DwmGetWindowAttribute(wt.HWND(hwnd), 14, ctypes.byref(cloaked),
                                             ctypes.sizeof(cloaked))
                if cloaked.value:
                    return True
            rect = window_rect(hwnd)
            if rect is None:
                return True
            l, t, rr, b = rect
            if rr - l < 250 or b - t < 160:
                return True
            out.append((hwnd, rect))
        except Exception:
            pass
        return True

    user32.EnumWindows(cb, 0)
    return out


def _send_timeout(hwnd, msg, wp, lp, timeout_ms=200):
    """SendMessage that gives up if the target (explorer) hangs."""
    res = ctypes.c_size_t()
    ok = user32.SendMessageTimeoutW(hwnd, msg, wp, lp, 0x3,  # ABORTIFHUNG | BLOCK
                                    timeout_ms, ctypes.byref(res))
    return res.value if ok else None


def desktop_icon_rects(max_icons=120):
    """Screen rects of desktop icons, via the desktop ListView. Best effort."""
    try:
        progman = user32.FindWindowW("Progman", None)
        defview = user32.FindWindowExW(progman, None, "SHELLDLL_DefView", None)
        if not defview:
            hits = []

            @WNDENUMPROC
            def cb(hwnd, _):
                v = user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
                if v:
                    hits.append(v)
                return True

            user32.EnumWindows(cb, 0)
            defview = hits[0] if hits else None
        if not defview:
            return []
        lv = user32.FindWindowExW(defview, None, "SysListView32", None)
        if not lv:
            return []
        count = _send_timeout(lv, 0x1004, 0, 0)  # LVM_GETITEMCOUNT
        if not count:
            return []
        spacing = _send_timeout(lv, 0x1033, 0, 0) or 0  # LVM_GETITEMSPACING
        cw = spacing & 0xFFFF or 76
        chh = (spacing >> 16) & 0xFFFF or 96
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(lv, ctypes.byref(pid))
        hproc = kernel32.OpenProcess(0x38, False, pid.value)  # VM_OP | VM_READ | VM_WRITE
        if not hproc:
            return []
        rects = []
        try:
            remote = kernel32.VirtualAllocEx(hproc, None, ctypes.sizeof(wt.POINT),
                                             0x3000, 4)  # COMMIT|RESERVE, READWRITE
            if not remote:
                return []
            pt = wt.POINT()
            n = ctypes.c_size_t()
            for i in range(min(count, max_icons)):
                if _send_timeout(lv, 0x1010, i, remote) is None:  # LVM_GETITEMPOSITION
                    break
                if not kernel32.ReadProcessMemory(hproc, remote, ctypes.byref(pt),
                                                  ctypes.sizeof(pt), ctypes.byref(n)):
                    continue
                spt = wt.POINT(pt.x, pt.y)
                user32.ClientToScreen(lv, ctypes.byref(spt))
                rects.append((spt.x, spt.y, spt.x + cw, spt.y + chh))
            kernel32.VirtualFreeEx(hproc, remote, 0, 0x8000)  # MEM_RELEASE
        finally:
            kernel32.CloseHandle(hproc)
        return rects
    except Exception:
        return []


def acquire_single_instance():
    handle = kernel32.CreateMutexW(None, False, "vCat_single_instance_mutex")
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        return None
    return handle


# ---------------------------------------------------------------------------
# Tiny 8-bit sounds, synthesized in memory (no asset files)
# ---------------------------------------------------------------------------

_SND_CACHE = {}


def _wav_bytes(samples, sr=22050):
    import io
    import wave
    import array
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(sr)
    a = array.array("h", (int(max(-1.0, min(1.0, v)) * 32767) for v in samples))
    w.writeframes(a.tobytes())
    w.close()
    return buf.getvalue()


def _synth(kind):
    sr = 22050
    s = []
    if kind in ("meow", "mew"):
        dur = 0.34 if kind == "meow" else 0.20
        mul = 1.0 if kind == "meow" else 1.55
        n = int(sr * dur)
        ph = 0.0
        for i in range(n):
            prog = i / n
            f = mul * (480 + 430 * math.sin(math.pi * min(1.0, prog * 1.15)))
            f *= 1 + 0.035 * math.sin(2 * math.pi * 8 * i / sr)   # vibrato
            ph += 2 * math.pi * f / sr
            env = min(1.0, prog * 9) * (1 - prog) ** 1.4
            s.append(0.15 * env * (math.sin(ph) + 0.35 * math.sin(2 * ph)))
    elif kind == "purr":
        n = int(sr * 1.0)
        ph = 0.0
        for i in range(n):
            prog = i / n
            ph += 2 * math.pi * 52 / sr
            am = 0.55 + 0.45 * math.sin(2 * math.pi * 21 * i / sr)  # rumble pulses
            env = min(1.0, prog * 6) * min(1.0, (1 - prog) * 4)
            s.append(0.10 * env * am * math.sin(ph))
    elif kind == "chirp":
        n = int(sr * 0.14)
        ph = 0.0
        for i in range(n):
            prog = i / n
            ph += 2 * math.pi * (750 + 800 * prog) / sr
            env = min(1.0, prog * 10) * (1 - prog)
            s.append(0.14 * env * math.sin(ph))
    elif kind == "hiss":
        n = int(sr * 0.5)
        prev = 0.0
        for i in range(n):
            prog = i / n
            env = min(1.0, prog * 6) * (1 - prog) ** 1.3
            # band-passed-ish white noise reads as an angry hiss
            white = random.uniform(-1, 1)
            prev = 0.6 * prev + 0.4 * white
            s.append(0.13 * env * (white - prev) * (0.7 + 0.3 * math.sin(2 * math.pi * 60 * i / sr)))
    elif kind == "woof":           # dog: two short low barks
        ph = 0.0
        for k in range(2):
            for i in range(int(sr * 0.12)):
                prog = i / (sr * 0.12)
                f = 180 + 90 * (1 - prog)
                ph += 2 * math.pi * f / sr
                env = min(1.0, prog * 12) * (1 - prog) ** 1.2
                s.append(0.16 * env * (math.sin(ph) + 0.4 * math.sin(2 * ph)))
            for _ in range(int(sr * 0.05)):
                s.append(0.0)
    elif kind == "roar":           # dragon: low growl sweep
        ph = 0.0
        n = int(sr * 0.55)
        for i in range(n):
            prog = i / n
            f = 90 + 70 * math.sin(math.pi * prog)
            ph += 2 * math.pi * f / sr
            env = min(1.0, prog * 6) * (1 - prog)
            growl = 0.6 + 0.4 * math.sin(2 * math.pi * 28 * i / sr)
            s.append(0.16 * env * growl * (math.sin(ph) + 0.5 * math.sin(3 * ph)))
    elif kind in ("yip", "squeak"):  # fox yip / bunny squeak: tiny high blip
        ph = 0.0
        n = int(sr * (0.1 if kind == "yip" else 0.08))
        base = 900 if kind == "yip" else 1300
        for i in range(n):
            prog = i / n
            ph += 2 * math.pi * (base + 700 * prog) / sr
            env = min(1.0, prog * 12) * (1 - prog) ** 1.5
            s.append(0.13 * env * math.sin(ph))
    elif kind == "baa":            # goat bleat: wavery mid tone
        ph = 0.0
        n = int(sr * 0.4)
        for i in range(n):
            prog = i / n
            f = 380 * (1 + 0.12 * math.sin(2 * math.pi * 18 * i / sr))  # tremolo
            ph += 2 * math.pi * f / sr
            env = min(1.0, prog * 8) * (1 - prog) ** 1.2
            s.append(0.14 * env * (math.sin(ph) + 0.4 * math.sin(2 * ph)))
    elif kind == "oink":           # pig: two short nasal grunts
        ph = 0.0
        for _ in range(2):
            for i in range(int(sr * 0.1)):
                prog = i / (sr * 0.1)
                ph += 2 * math.pi * (220 - 40 * prog) / sr
                env = min(1.0, prog * 10) * (1 - prog)
                s.append(0.15 * env * (math.sin(ph) + 0.5 * math.sin(3 * ph)))
            for _ in range(int(sr * 0.04)):
                s.append(0.0)
    elif kind == "moo":            # cow: long low rise-and-fall
        ph = 0.0
        n = int(sr * 0.7)
        for i in range(n):
            prog = i / n
            f = 150 + 50 * math.sin(math.pi * prog)
            ph += 2 * math.pi * f / sr
            env = min(1.0, prog * 5) * min(1.0, (1 - prog) * 4)
            s.append(0.16 * env * (math.sin(ph) + 0.4 * math.sin(2 * ph)))
    elif kind == "ribbit":         # frog: two croaky blips
        for k in range(2):
            ph = 0.0
            for i in range(int(sr * 0.09)):
                prog = i / (sr * 0.09)
                ph += 2 * math.pi * (140 + 60 * k) / sr
                buzz = 0.5 + 0.5 * math.sin(2 * math.pi * 45 * i / sr)
                env = min(1.0, prog * 10) * (1 - prog)
                s.append(0.15 * env * buzz * math.sin(ph))
            for _ in range(int(sr * 0.05)):
                s.append(0.0)
    return _wav_bytes(s, sr)


_winmm = None


def play_sound(kind):
    # winsound forbids SND_MEMORY | SND_ASYNC, so call winmm directly.
    # Safe because _SND_CACHE keeps the bytes alive for the process lifetime.
    global _winmm
    try:
        if kind not in _SND_CACHE:
            _SND_CACHE[kind] = _synth(kind)
        if _winmm is None:
            _winmm = ctypes.WinDLL("winmm")
            _winmm.PlaySoundW.argtypes = [ctypes.c_char_p, wt.HMODULE, wt.DWORD]
            _winmm.PlaySoundW.restype = wt.BOOL
        _winmm.PlaySoundW(_SND_CACHE[kind], None,
                          0x1 | 0x2 | 0x4)  # SND_ASYNC | SND_NODEFAULT | SND_MEMORY
    except Exception as e:
        log_error(f"play_sound({kind}): {e!r}")


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

SAVE_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "vCat")
SAVE_PATH = os.path.join(SAVE_DIR, "vcat.json")
LOG_PATH = os.path.join(SAVE_DIR, "vcat.log")

DECAY = {"hunger": 100 / (8 * 3600), "thirst": 100 / (6 * 3600), "love": 100 / (16 * 3600)}


def log_error(msg):
    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(time.strftime("[%Y-%m-%d %H:%M:%S] ") + msg + "\n")
    except Exception:
        pass


def load_state():
    state = {"hunger": 90.0, "thirst": 90.0, "love": 80.0, "scale": 3, "ts": time.time(),
             "color": "black", "sounds": True, "kitten": False, "kitten_color": "",
             "decor": [], "name": "", "kitten_name": "", "costume": "none",
             "potty": 80.0, "messes": [], "animals": [],
             "species": "cat", "created_ts": None, "immortal": False}
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k in ("hunger", "thirst", "love"):
            if isinstance(data.get(k), (int, float)) and not isinstance(data.get(k), bool):
                state[k] = float(min(100, max(0, data[k])))
        s = data.get("scale")
        if isinstance(s, int) and not isinstance(s, bool) and s in (2, 3, 4, 6, 8):
            state["scale"] = s
        if data.get("color") in PALETTES:
            state["color"] = data["color"]
        if data.get("kitten_color") in PALETTES:
            state["kitten_color"] = data["kitten_color"]
        state["sounds"] = bool(data.get("sounds", True))
        state["kitten"] = bool(data.get("kitten", False))
        dec = data.get("decor")
        if isinstance(dec, list):
            out = []
            for d in dec[:30]:
                if (isinstance(d, dict) and d.get("kind") in DECOR_ART
                        and isinstance(d.get("x"), (int, float))
                        and not isinstance(d.get("x"), bool)):
                    entry = {"kind": d["kind"], "x": float(d["x"])}
                    u = d.get("uses")
                    if isinstance(u, int) and not isinstance(u, bool):
                        entry["uses"] = max(0, min(99, u))
                    v = d.get("variant")
                    if isinstance(v, int) and not isinstance(v, bool):
                        entry["variant"] = max(0, min(9, v))
                    elif d["kind"] in VEG_GROW_KINDS:
                        entry["variant"] = 0            # legacy plant: keep original art
                    gr = d.get("grow")
                    if isinstance(gr, (int, float)) and not isinstance(gr, bool):
                        entry["grow"] = max(0.05, min(1.0, float(gr)))
                    elif d["kind"] in VEG_GROW_KINDS:
                        entry["grow"] = 1.0             # legacy plant: was placed full-grown
                    out.append(entry)
            state["decor"] = out
        mess = data.get("messes")
        if isinstance(mess, list):
            out = []
            for m in mess[:20]:
                if (isinstance(m, dict) and m.get("kind") in MESS_ART
                        and isinstance(m.get("x"), (int, float))
                        and not isinstance(m.get("x"), bool)):
                    out.append({"kind": m["kind"], "x": float(m["x"])})
            state["messes"] = out
        ani = data.get("animals")
        if isinstance(ani, list):
            # animals don't age while the app is closed (freeze their clock)
            away = max(0.0, time.time() - float(data.get("ts", time.time())))

            def _num(v):
                return (float(v) if isinstance(v, (int, float))
                        and not isinstance(v, bool) else None)
            out = []
            for a in ani[:20]:
                if isinstance(a, dict) and a.get("species") in SPECIES:
                    b = _num(a.get("birth"))
                    out.append({
                        "species": a["species"],
                        "gender": a.get("gender") if a.get("gender") in ("m", "f") else None,
                        "genes": a.get("genes") if isinstance(a.get("genes"), dict) else None,
                        "name": (a.get("name") or "")[:16],
                        "birth": (b + away) if b is not None else None,
                        "hunger": _num(a.get("hunger")),
                        "lifespan": _num(a.get("lifespan"))})
            state["animals"] = out
        for nk in ("name", "kitten_name"):
            v = data.get(nk)
            if isinstance(v, str):
                state[nk] = v.strip()[:16]
        if data.get("costume") in COSTUMES:
            state["costume"] = data["costume"]
        if (isinstance(data.get("potty"), (int, float))
                and not isinstance(data.get("potty"), bool)):
            state["potty"] = float(min(100, max(0, data["potty"])))
        if data.get("species") in SPECIES:
            state["species"] = data["species"]
        state["immortal"] = bool(data.get("immortal", False))
        ct = data.get("created_ts")
        if isinstance(ct, (int, float)) and not isinstance(ct, bool):
            state["created_ts"] = float(ct)
        # gentle offline decay (quarter rate, and never drop below 25 from it)
        away = max(0.0, time.time() - float(data.get("ts", time.time())))
        for k, rate in DECAY.items():
            decayed = state[k] - away * rate * 0.25
            state[k] = max(min(state[k], 25.0), decayed)
        state["potty"] = max(0.0, state["potty"] - away * (100 / (5 * 3600)) * 0.25)
    except FileNotFoundError:
        pass
    except Exception as e:
        log_error(f"load_state: {e!r}")
    return state


def save_state(state):
    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
        state = dict(state, ts=time.time())
        tmp = SAVE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp, SAVE_PATH)
    except Exception as e:
        log_error(f"save_state: {e!r}")


# ---------------------------------------------------------------------------
# The mouse
# ---------------------------------------------------------------------------

def _pet_window(master):
    """A borderless, topmost, color-keyed toplevel."""
    win = tk.Toplevel(master)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.config(bg=KEY)
    try:
        win.attributes("-transparentcolor", KEY)
    except tk.TclError:
        pass
    return win


class Critter:
    """A little mouse that scurries across the screen (and may become a gift)."""

    def __init__(self, app):
        self.app = app
        s = self.scale = max(2, app.scale - 1)
        self.win = _pet_window(app)
        self.cw, self.ch = 14 * s, 10 * s
        self.canvas = tk.Canvas(self.win, width=self.cw, height=self.ch,
                                bg=KEY, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.type = random.choice(list(CRITTER_TYPES))
        self.fr = CRITTER_TYPES[self.type]
        self._pal = dict(PAL, **self.fr["pal"]) if self.fr["pal"] else None
        self.images = {}
        for name in CRITTER_FRAMES:
            self.images[(name, 1)] = frame_to_photo(CRITTER_FRAMES[name], s, pal=self._pal)
            self.images[(name, -1)] = frame_to_photo(CRITTER_FRAMES[name], s, flip=True,
                                                     pal=self._pal)
        self.item = self.canvas.create_image(self.cw // 2, self.ch, anchor="s")
        wa = app.wa
        self.dir = random.choice((1, -1))
        self.x = float(wa[0] + 6) if self.dir == 1 else float(wa[2] - 6)
        self.y = float(wa[3])
        self.alive = True
        self.caught = False
        self.dropped_t = None
        self.move_t = random.uniform(0.4, 0.9)
        self.pause_t = 0.0
        self.anim_t = 0.0
        self._place()

    def scared(self):
        return abs(self.app.x - self.x) < 260

    def tick(self, dt):
        if not self.alive:
            return
        if self.caught:
            if self.dropped_t is not None and time.monotonic() > self.dropped_t:
                self.despawn()
            return
        self.anim_t += dt
        if self.pause_t > 0:
            self.pause_t -= dt
            if self.pause_t <= 0:
                self.move_t = random.uniform(0.35, 0.9)
                if random.random() < 0.15:
                    self.dir = -self.dir
        else:
            self.x += self.dir * (240 if self.scared() else 150) * dt
            self.move_t -= dt
            if self.move_t <= 0:
                self.pause_t = (random.uniform(0.08, 0.25) if self.scared()
                                else random.uniform(0.3, 0.9))
            wa = self.app.wa
            if self.x < wa[0] - 20 or self.x > wa[2] + 20:
                self.despawn()
                return
        moving = self.pause_t <= 0
        frame = self.fr["b"] if moving and int(self.anim_t * 12) % 2 else self.fr["a"]
        self.canvas.itemconfig(self.item, image=self.images[(frame, self.dir)])
        self._place()

    def _place(self):
        self.win.geometry(f"+{int(self.x - self.cw / 2 + self.app.sdx)}"
                          f"+{int(self.y - self.ch + self.app.sdy)}")

    def catch(self):
        self.caught = True
        self.win.withdraw()

    def drop_at(self, x, y):
        self.caught = True
        self.x, self.y = float(x), float(y)
        self.canvas.itemconfig(self.item, image=self.images[(self.fr["flat"], self.dir)])
        self._place()
        self.win.deiconify()
        self.win.attributes("-topmost", True)
        self.dropped_t = time.monotonic() + 7
    def rescale(self):
        s = self.scale = max(2, self.app.scale - 1)
        self.cw, self.ch = 14 * s, 10 * s
        self.canvas.config(width=self.cw, height=self.ch)
        for name in CRITTER_FRAMES:
            self.images[(name, 1)] = frame_to_photo(CRITTER_FRAMES[name], s, pal=self._pal)
            self.images[(name, -1)] = frame_to_photo(CRITTER_FRAMES[name], s, flip=True,
                                                     pal=self._pal)
        self.canvas.coords(self.item, self.cw // 2, self.ch)
        frame = self.fr["flat"] if (self.caught and self.dropped_t is not None) else self.fr["a"]
        self.canvas.itemconfig(self.item, image=self.images[(frame, self.dir)])
        if not self.caught or self.dropped_t is not None:
            self._place()

    def despawn(self):
        self.alive = False
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# ---------------------------------------------------------------------------
# The laser dot
# ---------------------------------------------------------------------------

class Laser:
    """A red dot that trails the cursor. Famously uncatchable."""

    def __init__(self, app):
        self.app = app
        s = 2
        self.win = _pet_window(app)
        self.cw = self.ch = 8 * s
        self.canvas = tk.Canvas(self.win, width=self.cw, height=self.ch,
                                bg=KEY, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.img = frame_to_photo(LASER_DOT, s)
        self.canvas.create_image(self.cw // 2, self.ch // 2, image=self.img)
        self.x, self.y = (float(c) for c in app.cur)
        self._place()
        # the dot sits at the cursor: make the whole window click-through
        # (WS_EX_TRANSPARENT) so it never swallows the user's clicks
        try:
            self.win.update_idletasks()
            hwnd = user32.GetAncestor(self.win.winfo_id(), 2)  # GA_ROOT
            GWL_EXSTYLE = -20
            style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE,
                                     style | 0x80000 | 0x20)  # LAYERED | TRANSPARENT
        except Exception:
            pass

    def tick(self, dt):
        tx, ty = self.app.cur
        k = min(1.0, dt * 9)  # smooth trailing follow
        self.x += (tx - self.x) * k
        self.y += (ty - self.y) * k
        self._place()

    def _place(self):
        try:
            self.win.geometry(f"+{int(self.x - self.cw / 2)}+{int(self.y - self.ch / 2)}")
        except tk.TclError:
            pass

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# ---------------------------------------------------------------------------
# The yarn ball
# ---------------------------------------------------------------------------

class Toy:
    """A ball of yarn with physics. Grab it and fling it!"""

    def __init__(self, app, x, y, vx, vy):
        self.app = app
        s = self.scale = max(2, app.scale - 1)
        self.win = _pet_window(app)
        self.cw = self.ch = 10 * s
        self.canvas = tk.Canvas(self.win, width=self.cw, height=self.ch,
                                bg=KEY, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.images = [frame_to_photo(f, s) for f in YARN_FRAMES]
        self.item = self.canvas.create_image(self.cw // 2, self.ch // 2,
                                             image=self.images[0])
        self.x, self.y = float(x), float(y)   # y = ball center
        self.vx, self.vy = float(vx), float(vy)
        self.roll = 0.0
        self.held = False
        self.hist = []                        # (t, x, y) while held, for flinging
        self.user_touch = time.monotonic()    # drives the auto-despawn timer
        self.kick_grace = 0.0                 # ignore cat kicks for the 'fast' check
        self.last_touch = time.monotonic()
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._dragm)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self._place()

    def floor(self):
        return self.app.ground() - self.ch / 2

    def tick(self, dt):
        if self.held:
            self.last_touch = time.monotonic()
            self.user_touch = self.last_touch
            return
        wa = self.app.wa
        self.vy += 2400 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y >= self.floor():            # floor bounce, then roll
            self.y = self.floor()
            # threshold scales with the per-tick gravity impulse so a
            # resting ball stays at rest instead of micro-bouncing
            if abs(self.vy) > 90 + 2400 * dt:
                self.vy = -self.vy * 0.55
            else:
                self.vy = 0.0
            self.vx *= math.exp(-dt * 1.6)    # rolling friction
            if abs(self.vx) < 8:
                self.vx = 0.0
        if self.y < wa[1] + self.ch:
            self.y = wa[1] + self.ch
            self.vy = abs(self.vy) * 0.5
        if self.x < wa[0] + self.cw / 2:
            self.x = wa[0] + self.cw / 2
            self.vx = abs(self.vx) * 0.7
        elif self.x > wa[2] - self.cw / 2:
            self.x = wa[2] - self.cw / 2
            self.vx = -abs(self.vx) * 0.7
        self.roll += self.vx * dt
        idx = int(self.roll / (6 * self.scale)) % 4
        self.canvas.itemconfig(self.item, image=self.images[idx])
        self._place()

    def kick(self, vx, vy):
        self.vx, self.vy = float(vx), float(vy)
        self.last_touch = time.monotonic()
        self.kick_grace = self.last_touch + 2.5

    def moving(self):
        return abs(self.vx) > 25 or abs(self.vy) > 25

    def _place(self):
        try:
            self.win.geometry(f"+{int(self.x - self.cw / 2 + self.app.sdx)}"
                              f"+{int(self.y - self.ch / 2 + self.app.sdy)}")
        except tk.TclError:
            pass

    def _press(self, ev):
        self.held = True
        self.hist = []
        self.user_touch = time.monotonic()

    def _dragm(self, ev):
        if not self.held:
            return
        now = time.monotonic()
        self.x, self.y = float(ev.x_root), float(ev.y_root)
        self.hist.append((now, self.x, self.y))
        self.hist = [h for h in self.hist if now - h[0] < 0.12]
        self._place()

    def _release(self, ev):
        if not self.held:
            return
        self.held = False
        now = time.monotonic()
        # only samples from just before release count — a drag that pauses
        # before letting go must not fling with the stale earlier velocity
        hist = [h for h in self.hist if now - h[0] < 0.12]
        if len(hist) >= 2:
            (t0, x0, y0), (t1, x1, y1) = hist[0], hist[-1]
            span = max(0.016, t1 - t0)
            self.vx = max(-1500, min(1500, (x1 - x0) / span))
            self.vy = max(-1500, min(1500, (y1 - y0) / span))
            self.kick_grace = 0.0             # a real user fling always counts
        else:
            self.vx = self.vy = 0.0
        self.last_touch = now
        self.user_touch = now

    def rescale(self):
        s = self.scale = max(2, self.app.scale - 1)
        self.cw = self.ch = 10 * s
        self.canvas.config(width=self.cw, height=self.ch)
        self.images = [frame_to_photo(f, s) for f in YARN_FRAMES]
        self.canvas.coords(self.item, self.cw // 2, self.ch // 2)
        self.canvas.itemconfig(self.item, image=self.images[0])
        self._place()

    def despawn(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# ---------------------------------------------------------------------------
# The kitten
# ---------------------------------------------------------------------------

class Kitten:
    """A smaller companion cat that tags along with the big one."""

    def __init__(self, app, color):
        self.app = app
        self.color = color
        self.name = ""
        s = self.scale = max(2, app.scale - 1)
        self.win = _pet_window(app)
        self.cw, self.ch = 42 * s, 36 * s
        self.canvas = tk.Canvas(self.win, width=self.cw, height=self.ch,
                                bg=KEY, highlightthickness=0, bd=0)
        self.canvas.pack()
        pal = variant_pal(color)
        self.images = {}
        for name, rows in FRAMES.items():
            self.images[(name, 1)] = frame_to_photo(rows, s, pal=pal)
            self.images[(name, -1)] = frame_to_photo(rows, s, flip=True, pal=pal)
        self.heart_img = frame_to_photo(ICONS["heart"], 2)
        self.item = self.canvas.create_image(self.cw // 2, self.ch, anchor="s")
        self.x = min(max(app.x + random.choice((-1, 1)) * 90,
                         app.wa[0] + 30), app.wa[2] - 30)
        self.y = app.ground()
        self.facing = 1
        self.state, self.anim = "idle", "idle"
        self.state_t, self.plan = 0.0, 1.5
        self.target, self.then, self.run = self.x, None, False
        self.jump = None
        self.vy = 0.0
        self.effects = []
        self.pressxy = None
        self.dragging = False
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._dragm)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<ButtonPress-3>", app.on_menu)
        self._draw()

    def set(self, state, anim=None, dur=2.0):
        self.state, self.anim = state, anim or state
        self.state_t, self.plan = 0.0, dur

    def walk_to(self, x, then=None, run=False):
        self.target = min(max(x, self.app.wa[0] + 14), self.app.wa[2] - 14)
        self.then, self.run = then, run
        self.set("walk", "run" if run else "walk", 20)

    def decide(self):
        a = self.app
        d = a.x - self.x
        if a.state == "sleep":
            if abs(d) > 26 * a.scale:
                self.walk_to(a.x - (1 if d > 0 else -1) * 18 * a.scale, then="sleep")
            else:
                self.set("sleep", "sleep", random.uniform(30, 90))
        elif a.laser is not None and random.random() < 0.7:
            self.walk_to(a.laser.x + random.uniform(-30, 30), run=True)
        elif a.toy is not None and not a.toy.held and random.random() < 0.45:
            self.walk_to(a.toy.x, then="toy", run=True)
        elif a.state in ("zoomies", "chase", "hunt", "carry"):
            self.walk_to(a.x + random.uniform(-40, 40), run=True)
        elif abs(d) > 170:
            self.walk_to(a.x - (1 if d > 0 else -1) * random.uniform(30, 90))
        else:
            r = random.random()
            if r < 0.38:
                self.set("idle", "idle", random.uniform(2, 5))
            elif r < 0.53:
                self.set("groom", "groom", random.uniform(2, 4))
            elif r < 0.67:
                self.set("tailchase", "tailchase", random.uniform(1.8, 3.2))
            elif r < 0.79 and abs(d) < 220:
                self.jump = (self.x, self.y, a.x + random.uniform(-10, 10),
                             a.ground(), 0.5, 0.0)
                self.set("jump", "pounce")
            elif r < 0.9:
                self.set("lie", "lie", random.uniform(3, 7))
            else:
                self.walk_to(self.x + random.uniform(-130, 130))
        if self.state in ("idle", "lie") and random.random() < 0.6:
            self.facing = 1 if d > 0 else -1

    def tick(self, dt):
        self.state_t += dt
        a = self.app
        if self.state == "dangle":
            self._tick_fx(dt)
            self._draw()
            return
        # re-pin to the floor if the work area changed under us
        if self.state not in ("fall", "jump"):
            if self.y > a.ground():
                self.y = a.ground()
            elif self.y < a.ground():
                self.vy = 0.0
                self.set("fall", "fall")
        if self.state == "fall":
            self.vy += 2600 * dt
            self.y += self.vy * dt
            if self.y >= a.ground():
                self.y = a.ground()
                self.set("idle", "idle", 1.5)
        elif self.state == "walk":
            d = self.target - self.x
            self.facing = 1 if d > 0 else -1
            self.x += self.facing * min(abs(d), (66 if self.run else 40) * self.scale * dt)
            self.x = min(max(self.x, a.wa[0] + 14), a.wa[2] - 14)
            if abs(d) < 5 or self.state_t > self.plan:
                if self.then == "sleep":
                    self.set("sleep", "sleep", random.uniform(30, 90))
                elif self.then == "toy":
                    t = a.toy
                    if (t is not None and not t.held
                            and abs(t.x - self.x) < 16 * self.scale
                            and t.y > a.ground() - 20 * self.scale):
                        away = 1 if t.x >= self.x else -1
                        t.kick(away * random.uniform(140, 280),
                               -random.uniform(60, 150))
                        self._heart()
                    self.set("idle", "idle", random.uniform(1, 2.5))
                else:
                    self.set("idle", "idle", random.uniform(1.5, 4))
                self.then = None
        elif self.state == "jump":
            x0, y0, x1, y1, dur, t = self.jump
            t += dt
            f = min(1.0, t / dur)
            self.x = x0 + (x1 - x0) * f
            self.y = y0 + (y1 - y0) * f - math.sin(math.pi * f) * 60
            self.facing = 1 if x1 >= x0 else -1
            self.jump = (x0, y0, x1, y1, dur, t)
            if f >= 1.0:
                self.y = a.ground()
                self.jump = None
                self._heart()
                a._float_icon("heart")
                if a.state == "idle" and random.random() < 0.5:
                    a._say("mrrp!")
                self.set("idle", "idle", 2.5)
        elif self.state == "tailchase":
            self.facing = 1 if int(self.state_t * 3) % 2 == 0 else -1
            if self.state_t > self.plan:
                self.set("idle", "blink", 1.2)
        elif self.state_t >= self.plan:
            self.decide()
        self._tick_fx(dt)
        self._draw()

    def _draw(self):
        frames, fps, loop = ANIMS.get(self.anim, ANIMS["idle"])
        idx = int(self.state_t * fps)
        idx = idx % len(frames) if loop else min(idx, len(frames) - 1)
        self.canvas.itemconfig(self.item, image=self.images[(frames[idx], self.facing)])
        self.win.geometry(f"+{int(self.x - self.cw / 2 + self.app.sdx)}"
                          f"+{int(self.y - self.ch + self.app.sdy)}")

    def _heart(self):
        iid = self.canvas.create_image(self.cw / 2, self.ch - 22 * self.scale,
                                       image=self.heart_img)
        self.effects.append({"id": iid, "t": 1.2, "vy": -24})

    def _tick_fx(self, dt):
        for fx in self.effects[:]:
            fx["t"] -= dt
            self.canvas.move(fx["id"], 0, fx["vy"] * dt)
            if fx["t"] <= 0:
                self.canvas.delete(fx["id"])
                self.effects.remove(fx)

    def _press(self, ev):
        self.pressxy = (ev.x_root, ev.y_root)
        self.dragging = False

    def _dragm(self, ev):
        if self.pressxy is None:
            return
        if not self.dragging and math.dist((ev.x_root, ev.y_root), self.pressxy) > 9:
            self.dragging = True
            self.jump = None
            self.set("dangle", "dangle")
        if self.dragging:
            self.x = float(ev.x_root)
            self.y = float(ev.y_root) + 26 * self.scale
            self._draw()

    def _release(self, ev):
        if self.dragging:
            self.vy = 0.0
            self.set("fall", "fall")
        else:
            self._heart()
            self.app.needs["love"] = min(100.0, self.app.needs["love"] + 2)
            self.app.play_snd("mew")
        self.pressxy = None
        self.dragging = False

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# ---------------------------------------------------------------------------
# Ecosystem animals — a companion flock that lives on its own
# ---------------------------------------------------------------------------

class Animal:
    """A free-living companion: grazes or hunts, flees, breeds, ages and dies."""

    def __init__(self, app, species, gender=None, genes=None, name="",
                 birth=None, hunger=None, x=None, lifespan=None):
        self.app = app
        self.species = species if species in SPECIES else "cat"
        self.gender = gender if gender in ("m", "f") else random.choice(("m", "f"))
        self.genes = genes or base_genes(self.species)
        self.name = name
        self.diet = SPECIES_DIET.get(self.species, "carn")
        self.birth = float(birth) if birth is not None else time.time()
        self.lifespan = float(lifespan) if lifespan else random.uniform(900, 1500)
        self.hunger = float(hunger) if hunger is not None else random.uniform(55, 90)
        self.alive = True
        self.dying = False
        self.dead_t = 0.0
        self.win = _pet_window(app)
        self.facing = random.choice((1, -1))
        wa = app.wa
        self.x = min(max(float(x) if x is not None else app.x + random.uniform(-220, 220),
                         wa[0] + 30), wa[2] - 30)
        self.y = app.ground()
        self.vy = 0.0
        self.state, self.anim = "idle", "idle"
        self.state_t, self.plan = 0.0, random.uniform(1, 3)
        self.target = self.x
        self.jump = None
        self.breed_cd = random.uniform(25, 60)
        self.want_baby = None        # set to a mate when a birth should happen
        self.urge = None             # right-click command (graze/hunt/mate/come/play/rest)
        self.urge_t = 0.0
        self.effects = []
        self.pressxy = None
        self.dragging = False
        self._last_stage = None
        self.canvas = None
        self._build()
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._dragm)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<ButtonPress-3>", self._menu)
        self._draw()

    # ---- looks ----
    def stage(self):
        age = time.time() - self.birth
        if age < 90:
            return "baby"
        if age > self.lifespan * 0.8:
            return "elder"
        return "adult"

    def is_adult(self):
        return self.stage() == "adult"

    def _build(self):
        st = self._last_stage = self.stage()
        factor = {"baby": 0.6, "adult": 1.0, "elder": 0.9}[st]
        base = max(2, int(self.app.base_scale))
        s = self.scale = round(max(1.6, base * factor * self.genes.get("size", 1.0)), 2)
        self.cw, self.ch = int(42 * s), int(36 * s)
        if self.canvas is None:
            self.canvas = tk.Canvas(self.win, width=self.cw, height=self.ch,
                                    bg=KEY, highlightthickness=0, bd=0)
            self.canvas.pack()
        else:
            self.canvas.config(width=self.cw, height=self.ch)
        pal = dict(PAL, **(self.genes.get("pal") or {}))
        if self.genes.get("shiny") or self.genes.get("ability") == "glow":
            pal = dict(pal, **_shiny_pal())     # glow & shiny both shimmer gold
        frames = dict(FRAMES)
        frames.update(species_frame_overrides(self.species))
        self.images = {}
        for n, rows in frames.items():
            self.images[(n, 1)] = frame_to_photo(rows, s, pal=pal)
            self.images[(n, -1)] = frame_to_photo(rows, s, flip=True, pal=pal)
        spec = SPECIES[self.species]
        behind = _compose_arts([spec.get("behind")])
        fronts = [spec.get("front")]
        if self.gender == "f":
            fronts.append(_BOW)
        front = _compose_arts(fronts)
        self.acc_img = {}
        if behind:
            self.acc_img[("behind", 1)] = frame_to_photo(behind, s)
            self.acc_img[("behind", -1)] = frame_to_photo(behind, s, flip=True)
        if front:
            self.acc_img[("front", 1)] = frame_to_photo(front, s)
            self.acc_img[("front", -1)] = frame_to_photo(front, s, flip=True)
        self.heart_img = frame_to_photo(ICONS["heart"], 2)
        self.canvas.delete("all")
        self.acc_behind = (self.canvas.create_image(0, 0, anchor="c")
                           if ("behind", 1) in self.acc_img else None)
        self.item = self.canvas.create_image(self.cw // 2, self.ch, anchor="s")
        self.acc_front = (self.canvas.create_image(0, 0, anchor="c")
                          if ("front", 1) in self.acc_img else None)
        self.effects = []
        self._place()

    def rescale(self):
        self._build()

    def set(self, state, anim=None, dur=2.0):
        self.state, self.anim = state, anim or state
        self.state_t, self.plan = 0.0, dur

    def voice(self):
        return SPECIES[self.species]["voice"]

    # ---- the brain ----
    def tick(self, dt):
        if self.dying:
            self.state_t += dt
            if random.random() < 0.3:
                self._fx(random.choice(("💀", "✦", "·")), -26, 1.2)
            if time.monotonic() > self.dead_t:
                self.alive = False
            self._tick_fx(dt)
            self._draw()
            return
        self.state_t += dt
        self._dt = dt
        self.hunger = max(0.0, self.hunger - dt * (100 / 240))   # empty in ~4 min
        a = self.app
        g = a.ground()
        if self.breed_cd > 0:
            self.breed_cd -= dt

        if self.stage() != self._last_stage:
            self._build()

        # starvation / old age (hardcore, but only starve if food it could have
        # reached actually exists — a lone pet in an empty world won't silently die)
        if self.state != "dangle":
            starved = self.hunger <= 0 and a.has_food_for(self.diet, self)
            too_old = (time.time() - self.birth) > self.lifespan
            if starved or too_old:
                self._die()
                return

        if self.state == "dangle":
            self._tick_fx(dt)
            self._draw()
            return
        # gravity if off the floor
        if self.state not in ("fall", "jump") and self.y < g:
            self.vy = 0.0
            self.set("fall", "fall")
        if self.state == "fall":
            self.vy += 2600 * dt
            self.y += self.vy * dt
            if self.y >= g:
                self.y = g
                self.set("idle", "idle", 1.0)
            self._tick_fx(dt)
            self._draw()
            return
        if self.y > g:
            self.y = g

        # --- decide ---
        if self.state in ("idle", "walk", "run", "graze", "sleep", "lie",
                          "look", "groom", "stretch", "play"):
            self._brain(dt)
        elif self.state == "eat":
            if self.state_t >= self.plan:
                self.set("idle", "idle", random.uniform(1, 3))
        self._tick_fx(dt)
        self._draw()

    def _brain(self, dt):
        a = self.app
        # 1) flee a predator (herbivores only) — survival always wins
        if self.diet == "herb":
            threat = a.nearest_threat(self)
            if threat is not None:
                self.facing = 1 if self.x > threat.x else -1
                self.anim = "run"
                self.x += self.facing * 110 * self._swift() * self.scale / 3 * dt
                self._clamp()
                return
        # 1b) a player-issued command (right-click) takes priority over autopilot
        if self.urge and self._do_urge(dt):
            return
        # 2) eat when hungry
        if self.hunger < 45:
            if self.diet == "herb":
                food = a.nearest_food(self.x)
                if food is not None:
                    if abs(food.x - self.x) > 12 * self.scale:
                        self._approach(food.x, 90)
                        self.anim = "walk"
                    else:
                        self.set("graze", "munch", 2.0)
                        food.graze()
                        self.hunger = min(100.0, self.hunger + 28)
                    return
            else:
                prey = a.nearest_prey(self)
                if prey is not None:
                    if abs(prey.x - self.x) > 14 * self.scale:
                        self._approach(prey.x, 130)
                        self.anim = "run"
                    else:
                        prey._die(eaten=True)
                        self.hunger = 100.0
                        self._fx("✦", -20, 0.6)
                        a.play_snd(self.voice())
                        self.set("eat", "bat", 1.2)
                    return
        # 3) breed when well-fed adult
        if (self.gender == "f" and self.is_adult() and self.breed_cd <= 0
                and self.hunger > 60 and len(a.animals) < a.animal_cap):
            mate = a.nearest_mate(self)
            if mate is not None:
                if abs(mate.x - self.x) > 16 * self.scale:
                    self._approach(mate.x, 80)
                    self.anim = "walk"
                else:
                    self.want_baby = mate
                    self.breed_cd = random.uniform(60, 120)
                    mate.breed_cd = random.uniform(60, 120)
                    self.hunger -= 20
                    self._heart()
                    self.set("idle", "idle", 2)
                return
        # 4) lots of little idle behaviours so a flock never looks static
        if self.state_t >= self.plan:
            r = random.random()
            if r < 0.22:
                self.set("idle", "idle", random.uniform(2, 5))
                if random.random() < 0.5:
                    self.facing = random.choice((1, -1))
            elif r < 0.34:
                self.set("look", "blink", random.uniform(1.5, 3))   # glance around
            elif r < 0.48:
                self.set("groom", "groom", random.uniform(2, 4))
            elif r < 0.58:
                self.set("lie", "lie", random.uniform(3, 8))
            elif r < 0.66 and self.stage() != "baby":
                self.set("stretch", "stretch", 1.3)
            elif r < 0.76:
                self.set("play", "tailchase", random.uniform(1.6, 3))  # zoomy play
            elif r < 0.85 and self.stage() != "baby":
                self.set("sleep", "sleep", random.uniform(8, 20))
            else:
                self.target = min(max(self.x + random.uniform(-220, 220),
                                      a.wa[0] + 16), a.wa[2] - 16)
                self.set("walk", "walk", 8)
        elif self.state == "look":
            if random.random() < 0.04:
                self.facing = -self.facing
            if self.state_t >= self.plan:
                self.set("idle", "idle", random.uniform(1, 3))
        elif self.state in ("groom", "stretch", "play"):
            if self.state == "play":
                self.facing = 1 if int(self.state_t * 3) % 2 == 0 else -1
            if self.state_t >= self.plan:
                self.set("idle", "idle", random.uniform(1, 3))
        elif self.state == "walk":
            if abs(self.target - self.x) < 5:
                self.set("idle", "idle", random.uniform(1.5, 4))
            else:
                self._approach(self.target, 40)

    def _do_urge(self, dt):
        """Carry out a player command from the right-click menu. Returns True if
        it consumed this tick (so tick() should stop here), False if the urge is
        finished / not applicable so the normal brain can take over."""
        a = self.app
        self.urge_t -= dt
        if self.urge_t <= 0:
            self.urge = None
            return False
        u = self.urge
        if u == "graze":
            if self.diet != "herb":
                self.urge = None
                return False
            food = a.nearest_food(self.x)
            if food is None:
                self._fx("?", -18, 0.8)
                self.urge = None
                return False
            if abs(food.x - self.x) > 12 * self.scale:
                self._approach(food.x, 90)
                self.anim = "walk"
            else:
                self.set("graze", "munch", 1.6)
                food.graze()
                self.hunger = min(100.0, self.hunger + 28)
                self.urge = None     # one commanded bite; autopilot eats on if hungry
            return True
        if u == "hunt":
            if self.diet != "carn":
                self.urge = None
                return False
            prey = a.nearest_prey(self)
            if prey is None:
                self._fx("?", -18, 0.8)
                self.urge = None
                return False
            if abs(prey.x - self.x) > 14 * self.scale:
                self._approach(prey.x, 130)
                self.anim = "run"
            else:
                prey._die(eaten=True)
                self.hunger = 100.0
                self._fx("✦", -20, 0.6)
                a.play_snd(self.voice())
                self.set("eat", "bat", 1.2)
                self.urge = None
            return True
        if u == "mate":
            if not (self.gender == "f" and self.is_adult() and self.hunger > 60
                    and self.breed_cd <= 0 and len(a.animals) < a.animal_cap):
                self._fx("?", -18, 0.8)
                self.urge = None
                return False
            mate = a.nearest_mate(self)
            if mate is None:
                self._fx("?", -18, 0.8)
                self.urge = None
                return False
            if abs(mate.x - self.x) > 16 * self.scale:
                self._approach(mate.x, 80)
                self.anim = "walk"
            else:
                self.want_baby = mate
                self.breed_cd = random.uniform(60, 120)
                mate.breed_cd = random.uniform(60, 120)
                self.hunger -= 20
                self._heart()
                self.set("idle", "idle", 2)
                self.urge = None
            return True
        if u == "come":
            cx = min(max(float(a.cur[0]), a.wa[0] + 12), a.wa[2] - 12)
            if abs(cx - self.x) > 10 * self.scale:
                self._approach(cx, 110)
                self.anim = "run"
                return True
            self._heart()
            self.set("look", "blink", 1.5)
            self.urge = None
            return True
        if u == "play":
            self.set("play", "tailchase", random.uniform(2, 3.5))
            self.urge = None
            return True
        if u == "rest":
            self.set("sleep", "sleep", random.uniform(10, 25))
            self.urge = None
            return True
        self.urge = None
        return False

    def _approach(self, tx, spd):
        self.facing = 1 if tx > self.x else -1
        self.x += self.facing * spd * self._swift() * self.scale / 3 * self._dt
        self._clamp()

    def _swift(self):
        return 1.35 if self.genes.get("ability") == "swift" else 1.0

    def _clamp(self):
        self.x = min(max(self.x, self.app.wa[0] + 12), self.app.wa[2] - 12)

    def _die(self, eaten=False):
        if self.dying:
            return
        self.dying = True
        self.dead_t = time.monotonic() + (0.8 if eaten else 1.6)
        self.anim = "lie"
        self._fx("💀", -22, 1.4)

    # ---- fx / draw ----
    def _heart(self):
        self._fx_img(self.heart_img, -24, 1.2)

    def _fx_img(self, img, vy, t):
        iid = self.canvas.create_image(self.cw / 2, self.ch - 22 * self.scale, image=img)
        self.effects.append({"id": iid, "t": t, "vy": vy})

    def _fx(self, text, vy, t):
        iid = self.canvas.create_text(self.cw / 2, self.ch - 22 * self.scale, text=text,
                                      fill="#f4f4f8", font=("Segoe UI", 4 + int(2 * self.scale)))
        self.effects.append({"id": iid, "t": t, "vy": vy})

    def _tick_fx(self, dt):
        for fx in self.effects[:]:
            fx["t"] -= dt
            self.canvas.move(fx["id"], 0, fx["vy"] * dt)
            if fx["t"] <= 0:
                self.canvas.delete(fx["id"])
                self.effects.remove(fx)

    def _draw(self):
        moving = self.anim in ("walk", "run")
        gdy, anim2 = gait_render(self.species, self.anim, self.state_t,
                                 self.scale, moving)
        self._gait_dy = gdy
        anim = anim2 or self.anim
        frames, fps, loop = ANIMS.get(anim, ANIMS["idle"])
        idx = int(self.state_t * fps)
        idx = idx % len(frames) if loop else min(idx, len(frames) - 1)
        self.canvas.itemconfig(self.item, image=self.images[(frames[idx], self.facing)])
        hide = anim in _ACC_HIDE_ANIMS
        if self.acc_behind is not None:
            self.canvas.itemconfig(self.acc_behind, state="hidden" if hide else "normal")
            if not hide:
                self.canvas.coords(self.acc_behind, self.cw / 2, self.ch - 12 * self.scale)
                self.canvas.itemconfig(self.acc_behind,
                                       image=self.acc_img[("behind", self.facing)])
        if self.acc_front is not None:
            self.canvas.itemconfig(self.acc_front, state="hidden" if hide else "normal")
            if not hide:
                self.canvas.coords(self.acc_front, self.cw / 2 + self.facing * 4 * self.scale,
                                   self.ch - 19 * self.scale)
                self.canvas.itemconfig(self.acc_front,
                                       image=self.acc_img[("front", self.facing)])
        self._place()

    def _place(self):
        self.win.geometry(f"+{int(self.x - self.cw / 2 + self.app.sdx)}"
                          f"+{int(self.y - self.ch + getattr(self, '_gait_dy', 0) + self.app.sdy)}")

    # ---- interaction ----
    def _press(self, ev):
        self.pressxy = (ev.x_root, ev.y_root)
        self.dragging = False

    def _dragm(self, ev):
        if self.pressxy is None or self.dying:
            return
        if not self.dragging and math.dist((ev.x_root, ev.y_root), self.pressxy) > 9:
            self.dragging = True
            self.jump = None
            self.set("dangle", "dangle")
        if self.dragging:
            self.x = float(ev.x_root)
            self.y = float(ev.y_root) + 26 * self.scale
            self._draw()

    def _release(self, ev):
        if self.dragging:
            self.vy = 0.0
            self.set("fall", "fall")
        elif not self.dying:
            self.hunger = min(100.0, self.hunger + 6)
            self._heart()
            self.app.play_snd(self.voice())
        self.pressxy = None
        self.dragging = False

    def _menu(self, ev):
        self.app.animal_menu(self, ev)

    def to_save(self):
        return {"species": self.species, "gender": self.gender, "genes": self.genes,
                "name": self.name, "birth": self.birth, "hunger": round(self.hunger, 1),
                "lifespan": round(self.lifespan, 1)}

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# ---------------------------------------------------------------------------
# Furniture / decorations
# ---------------------------------------------------------------------------

class Decor:
    """A placed piece of furniture: floor-anchored, draggable, removable."""

    def __init__(self, app, kind, x, uses=0, variant=None, grow=None):
        self.app = app
        self.kind = kind
        self.uses = uses               # litter-box dirtiness (uses since scoop)
        self.lushness = 100.0          # food in grass/plant/bush (regrows over time)
        # pick a random look once; persisted so it stays the same across runs
        pool = VEG_VARIANTS.get(kind)
        if pool:
            self.variant = (variant if isinstance(variant, int) and 0 <= variant < len(pool)
                            else random.randrange(len(pool)))
        else:
            self.variant = 0
        # growth: vegetation rises from a sprout to full; everything else is full
        if kind in VEG_GROW_KINDS:
            self.grow = float(grow) if grow is not None else 0.12
            self.grow = max(0.05, min(1.0, self.grow))
        else:
            self.grow = 1.0
        art = self._art()
        self.gw, self.gh = len(art[0]), len(art)
        self.scale = app.scale
        self.win = _pet_window(app)
        self._drawn_grow = -1.0
        self.x = float(x)              # provisional; clamped once we know our width
        self.canvas = tk.Canvas(self.win, width=1, height=1,
                                bg=KEY, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.item = self.canvas.create_image(0, 0, anchor="s")
        self._render()
        wa = app.wa
        self.x = min(max(self.x, wa[0] + self.cw / 2), wa[2] - self.cw / 2)
        self.pressxy = None
        self.dragging = False
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._dragm)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<ButtonPress-3>", self._menu)
        self._place()

    def _art(self):
        """The art grid this decor currently shows (its random variant, if any)."""
        pool = VEG_VARIANTS.get(self.kind)
        if pool:
            return pool[self.variant % len(pool)]
        return DECOR_ART[self.kind]

    def _eff_scale(self):
        """Pixel scale, shrunk while a plant is still growing in."""
        if self.kind in VEG_GROW_KINDS and self.grow < 1.0:
            return max(1.0, self.scale * (0.32 + 0.68 * self.grow))
        return float(self.scale)

    def _render(self):
        """(Re)build the photo at the current variant + growth and resize the box."""
        art = self._art()
        self.gw, self.gh = len(art[0]), len(art)
        self.img = frame_to_photo(art, self._eff_scale())
        self.cw, self.ch = self.img.width(), self.img.height()
        self.canvas.config(width=self.cw, height=self.ch)
        self.canvas.coords(self.item, self.cw // 2, self.ch)
        self.canvas.itemconfig(self.item, image=self.img)
        self._drawn_grow = self.grow
        # re-clamp on every (re)render so a plant that grows wider near a screen
        # edge stays fully on-screen instead of spilling off
        if hasattr(self, "x"):
            wa = self.app.wa
            half = min(self.cw / 2, (wa[2] - wa[0]) / 2)
            self.x = min(max(self.x, wa[0] + half), wa[2] - half)
        self._place()

    def top_y(self):
        """Screen-y of the top solid surface (for perching on the box)."""
        return self.app.ground() - (self.gh - 1) * self.scale

    def _place(self):
        try:
            self.win.geometry(
                f"+{int(self.x - self.cw / 2 + self.app.sdx)}"
                f"+{int(self.app.ground() - self.ch + self.app.sdy)}")
        except tk.TclError:
            pass

    def rescale(self):
        self.scale = self.app.scale
        self._render()

    def _press(self, ev):
        self.pressxy = (ev.x_root, ev.y_root)
        self.dragging = False

    def _dragm(self, ev):
        if self.pressxy is None:
            return
        if not self.dragging and abs(ev.x_root - self.pressxy[0]) > 6:
            self.dragging = True
        if self.dragging:
            wa = self.app.wa
            self.x = min(max(float(ev.x_root), wa[0] + self.cw / 2),
                         wa[2] - self.cw / 2)
            self._place()

    def _release(self, ev):
        if self.dragging:
            self.app._stash_save()
        self.pressxy = None
        self.dragging = False

    def _menu(self, ev):
        self.app.decor_menu(self, ev)

    def edible(self):
        # a sprout has nothing to graze yet — let it grow in first
        return (self.kind in EDIBLE_VEG and self.lushness > 8
                and self.grow > 0.35)

    def graze(self):
        self.lushness = max(0.0, self.lushness - 35.0)

    def regrow(self, dt):
        if self.kind in EDIBLE_VEG:
            self.lushness = min(100.0, self.lushness + dt * 4.0)  # full in ~25s
        if self.kind in VEG_GROW_KINDS and self.grow < 1.0:
            self.grow = min(1.0, self.grow + dt / VEG_GROW_SECS.get(self.kind, 60.0))
            if self.grow - self._drawn_grow >= 0.05 or self.grow >= 1.0:
                self._render()

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


class Mess:
    """A puddle/pile on the floor when there's no clean litter box. Click to clean."""

    def __init__(self, app, kind, x):
        self.app = app
        self.kind = kind
        art = MESS_ART[kind]
        self.gw, self.gh = len(art[0]), len(art)
        s = self.scale = app.scale
        self.win = _pet_window(app)
        self.cw, self.ch = self.gw * s, self.gh * s
        self.canvas = tk.Canvas(self.win, width=self.cw, height=self.ch,
                                bg=KEY, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.img = frame_to_photo(art, s)
        self.canvas.create_image(self.cw // 2, self.ch, anchor="s", image=self.img)
        wa = app.wa
        self.x = min(max(float(x), wa[0] + self.cw / 2), wa[2] - self.cw / 2)
        self.canvas.bind("<ButtonPress-1>", lambda e: app.clean_mess(self))
        self.canvas.bind("<ButtonPress-3>", lambda e: app.clean_mess(self))
        self._place()

    def _place(self):
        try:
            self.win.geometry(
                f"+{int(self.x - self.cw / 2 + self.app.sdx)}"
                f"+{int(self.app.ground() - self.ch + self.app.sdy)}")
        except tk.TclError:
            pass

    def rescale(self):
        s = self.scale = self.app.scale
        self.cw, self.ch = self.gw * s, self.gh * s
        self.canvas.config(width=self.cw, height=self.ch)
        self.img = frame_to_photo(MESS_ART[self.kind], s)
        self.canvas.delete("all")
        self.canvas.create_image(self.cw // 2, self.ch, anchor="s", image=self.img)
        self._place()

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


class Bird:
    """Flies across the upper screen; the cat tries to pounce it when it swoops."""

    def __init__(self, app):
        self.app = app
        s = self.scale = max(2, app.scale - 1)
        self.gw, self.gh = 12, 8
        self.win = _pet_window(app)
        self.cw, self.ch = self.gw * s, self.gh * s
        self.canvas = tk.Canvas(self.win, width=self.cw, height=self.ch,
                                bg=KEY, highlightthickness=0, bd=0)
        self.canvas.pack()
        ov = random.choice(BIRD_PALS)
        self._pal = dict(PAL, **ov) if ov else None
        self.images = {(n, d): frame_to_photo(BIRD_FRAMES[n], s, flip=(d < 0), pal=self._pal)
                       for n in BIRD_FRAMES for d in (1, -1)}
        self.item = self.canvas.create_image(self.cw // 2, self.ch // 2,
                                              image=self.images[("up", 1)])
        wa = app.wa
        self.dir = random.choice((1, -1))
        self.x = float(wa[0] - 20 if self.dir == 1 else wa[2] + 20)
        span = wa[3] - wa[1]
        self.base_y = float(wa[1] + random.uniform(0.10, 0.30) * span)
        self.y = self.base_y
        self.alive = True
        self.caught = False
        self.t = 0.0
        self.anim_t = 0.0
        # one chance partway across to swoop down into the cat's reach
        self.swoop_t = random.uniform(2.5, 6.0)
        self.swoop_dur = 1.8
        self._place()

    def reach_y(self):
        # within a desperate leap from the floor
        return self.app.ground() - 200 * self.app.scale

    def swooping(self):
        return self.swoop_t <= self.t <= self.swoop_t + self.swoop_dur

    def low_enough(self):
        # only catchable during its dip, never while cruising (any scale)
        return self.swooping() and self.y >= self.reach_y()

    def tick(self, dt):
        if not self.alive or self.caught:
            return
        self.t += dt
        self.anim_t += dt
        self.x += self.dir * 165 * dt
        swoop = 0.0
        if self.swooping():
            f = (self.t - self.swoop_t) / self.swoop_dur
            # dip down into the cat's reach at the nadir
            drop = (self.app.ground() - 150 * self.app.scale) - self.base_y
            swoop = math.sin(f * math.pi) * max(0.0, drop)
        self.y = self.base_y + math.sin(self.t * 3.0) * 9 * self.scale + swoop
        frame = "up" if int(self.anim_t * 9) % 2 else "down"
        self.canvas.itemconfig(self.item, image=self.images[(frame, self.dir)])
        self._place()
        wa = self.app.wa
        if self.x < wa[0] - 50 or self.x > wa[2] + 50:
            self.despawn()

    def _place(self):
        try:
            self.win.geometry(
                f"+{int(self.x - self.cw / 2 + self.app.sdx)}"
                f"+{int(self.y - self.ch / 2 + self.app.sdy)}")
        except tk.TclError:
            pass

    def catch(self):
        self.caught = True
        try:
            self.win.withdraw()
        except tk.TclError:
            pass

    def rescale(self):
        s = self.scale = max(2, self.app.scale - 1)
        self.cw, self.ch = self.gw * s, self.gh * s
        self.canvas.config(width=self.cw, height=self.ch)
        self.images = {(n, d): frame_to_photo(BIRD_FRAMES[n], s, flip=(d < 0), pal=self._pal)
                       for n in BIRD_FRAMES for d in (1, -1)}
        self.canvas.coords(self.item, self.cw // 2, self.ch // 2)
        self.canvas.itemconfig(self.item, image=self.images[("up", self.dir)])
        self._place()

    def despawn(self):
        self.alive = False
        try:
            self.win.destroy()
        except tk.TclError:
            pass


class Stork:
    """Flies across the top once to deliver a new (mammal) baby. Cosmetic."""

    def __init__(self, app, drop_x):
        self.app = app
        s = self.scale = max(3, int(app.base_scale) + 1)   # readable on hi-res
        self.gw, self.gh = 16, 12
        self.win = _pet_window(app)
        self.cw, self.ch = self.gw * s, self.gh * s
        self.canvas = tk.Canvas(self.win, width=self.cw, height=self.ch,
                                bg=KEY, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.images = {(n, d): frame_to_photo(STORK_FRAMES[n], s, flip=(d < 0))
                       for n in STORK_FRAMES for d in (1, -1)}
        self.item = self.canvas.create_image(self.cw // 2, self.ch // 2,
                                              image=self.images[("up", 1)])
        wa = app.wa
        self.drop_x = min(max(drop_x, wa[0] + 30), wa[2] - 30)
        self.dropped = False
        self.dir = 1                                    # always fly in from the left
        self.x = float(wa[0] - 30)
        self.y = float(wa[1] + 0.16 * (wa[3] - wa[1]))
        self.speed = max(360.0, (wa[2] - wa[0]) / 6.0)  # cross any screen in ~6s
        self.alive = True
        self.t = 0.0
        self._place()

    def tick(self, dt):
        if not self.alive:
            return
        self.t += dt
        self.x += self.dir * self.speed * dt
        self.y += math.sin(self.t * 2.5) * 12 * dt * self.scale
        frame = "up" if int(self.t * 7) % 2 else "down"
        self.canvas.itemconfig(self.item, image=self.images[(frame, self.dir)])
        self._place()
        wa = self.app.wa
        if not self.dropped and self.x >= self.drop_x:   # release the bundle!
            self.dropped = True
            self.app._stork_drop(self.drop_x, self.y + self.ch / 2)
        if self.x < wa[0] - 60 or self.x > wa[2] + 60:
            self.despawn()

    def _place(self):
        try:
            self.win.geometry(f"+{int(self.x - self.cw / 2 + self.app.sdx)}"
                              f"+{int(self.y - self.ch / 2 + self.app.sdy)}")
        except tk.TclError:
            pass

    def despawn(self):
        self.alive = False
        try:
            self.win.destroy()
        except tk.TclError:
            pass


# ---------------------------------------------------------------------------
# The cat
# ---------------------------------------------------------------------------

TICK_MS = 40  # 25 fps

# states where the cat is intentionally off the floor (skip floor re-pinning)
AIR_STATES = ("jump", "fall", "dangle", "catch", "wallclimb", "madfall",
              "perchsit", "perchsleep", "delivering")

# censored grumbles for when you mess with her window
ANGRY_WORDS = ("#$@%!", "@!#?*&", "%$#@!", "*!#@&!", "$#@*!!", "#@$%&!", "!?@#*")

# per-voice little speech words (so every animal "talks" in character)
VOICE_WORDS = {
    "meow":   ("purrr~", "prrr", "mrrp", "meow!"),
    "woof":   ("woof!", "arf~", "wrf", "bork!"),
    "roar":   ("rawr~", "grrr", "rrr", "roaar"),
    "squeak": ("squeak!", "eee~", "mp!", "sqk"),
    "yip":    ("yip!", "yorf", "ree", "yip~"),
    "baa":    ("baa~", "mehh", "baaa", "bleh"),
    "oink":   ("oink~", "snrf", "oink!", "grnt"),
    "moo":    ("moo~", "mrrr", "mooo", "mboo"),
    "ribbit": ("ribbit~", "brrp", "croak", "rbt!"),
}

# anims where a costume hat/wings would visibly detach from the body
_ACC_HIDE_ANIMS = frozenset((
    "sleep", "lie", "eat", "drink", "munch", "flip", "climb", "potty",
    "stretch", "tailchase", "pounce", "egg", "hatch"))

# ---- lifecycle (real-time aging, Tamagotchi-style) ----
EGG_DUR = 90                       # egg-species incubate this long before hatching
STAGE_BOUNDS = (("baby", 1800), ("kid", 7200), ("teen", 28800),
                ("adult", 345600), ("elder", 604800))   # secs since hatch
STAGE_ORDER = ("egg", "baby", "kid", "teen", "adult", "elder", "passing")
STAGE_FACTOR = {"egg": 0.7, "baby": 0.55, "kid": 0.72, "teen": 0.86,
                "adult": 1.0, "elder": 0.9, "passing": 0.85}
STAGE_LABEL = {"egg": "🥚 egg", "baby": "👶 baby", "kid": "🐾 kid",
               "teen": "🧒 teen", "adult": "🐈 adult", "elder": "👴 elder",
               "passing": "🌈 …"}
ADULT_AGE = 30000                  # migrate old saves to a healthy adult


class VCat(tk.Tk):
    def __init__(self, state):
        super().__init__()
        self.persist = state
        self.needs = {k: state[k] for k in ("hunger", "thirst", "love")}
        self.potty = float(state.get("potty", 80.0))
        self.name = state.get("name", "")
        # ---- lifecycle / species ----
        self.species = state.get("species", "cat")
        if self.species not in SPECIES:
            self.species = "cat"
        self.immortal = bool(state.get("immortal", False))
        self.base_scale = state["scale"]          # the user's chosen Size tier
        ct = state.get("created_ts")
        if ct is None:                            # old save / first run: an adult
            ct = time.time() - ADULT_AGE
        self.created_ts = float(ct)
        self.stage = self.life_stage()
        self.scale = self._age_scale(self.stage)  # effective (age-adjusted) scale
        self.stork = None                         # delivery animation, if any
        self._delivered = True                     # False only mid stork-delivery
        self.costume = state.get("costume", "none")
        if self.costume not in COSTUMES:
            self.costume = "none"
        self.sdx = self.sdy = 0.0      # screen-shake offset (read by all props)
        self.shake = 0.0
        self._shaking_prev = False

        self.title("vCat")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.config(bg=KEY)
        try:
            self.attributes("-transparentcolor", KEY)
        except tk.TclError:
            pass

        self.canvas = tk.Canvas(self, bg=KEY, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.sprite_item = None
        self.images = {}
        self.icon_images = {}
        self._build_images()

        wa = work_area()
        self.wa = wa
        self.x = (wa[0] + wa[2]) / 2
        self.y = float(wa[3])          # feet line (screen coords)
        self.facing = 1                # 1 = right, -1 = left
        self.surface_hwnd = None       # window we're standing on, if any
        self.surface_last = None       # its last rect

        self.state = "idle"
        self.state_t = 0.0
        self.plan_dur = 2.0
        self.anim = "idle"
        self.walk_target = None
        self.vy = 0.0
        self.jump = None               # (x0, y0, x1, y1, dur) while leaping
        self.after_jump = None
        self.chase_cd = 20.0           # first chase possible soon after launch
        self.behavior_cd = {"scratch": 40.0, "climb": 18.0, "icon": 100.0,
                            "sleep": 180.0, "tailchase": 90.0}
        self.critter = None            # the mouse, when one is visiting
        self.next_mouse = time.monotonic() + random.uniform(90, 240)
        self.carrying = False          # bringing the caught mouse as a gift
        self.carry_target = 0.0
        self.mouth_item = None
        self._snd_cd = 0.0
        self.kitten = None             # retired in favour of the animal flock
        self.animals = []              # the ecosystem companions
        self.animal_cap = 14
        self.laser = None              # the red dot, while the laser is out
        self.laser_until = 0.0
        self.toy = None                # the yarn ball, while it's out
        self.bat_count = 0
        self.bat_limit = 5
        self.zoom_flip = False         # finish the zoomies with a backflip?
        self.climb_info = None         # (hwnd, side, col) while climbing a window edge
        self.behavior_cd["toy"] = 0.0
        self.behavior_cd["decor"] = 8.0
        self.decor = []                # placed furniture (Decor objects)
        self.decor_target = None       # Decor we're walking to / interacting with
        self.perch = None              # Decor we're sitting on top of (the box)
        self.surface_move = 0.0        # accumulated jostle of the window we're on
        self.messes = []               # Mess objects on the floor
        self.bird = None               # Bird, when one is flying by
        self.next_bird = time.monotonic() + random.uniform(45, 150)
        self.litter_target = None      # litter Decor we're heading to
        self.beg_cd = 15.0
        self.gone_far_t = 0.0
        self.windows_cache = []
        self.windows_cache_t = 0.0
        self.cursor_hist = []          # (t, x, y)
        self.cur = cursor_pos()
        self.effects = []              # floating canvas items: dicts
        self.bubble = None             # (item ids, expire time)
        self.drag = None               # dict while dragging
        self.press = None
        self.menu_open = False
        self._menu_widget = None
        self.last_save = time.monotonic()
        self.last_top = 0.0
        self.err_streak = 0
        self._quitting = False

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<ButtonPress-3>", self.on_menu)
        self.protocol("WM_DELETE_WINDOW", self.quit_app)

        self._place()
        for d in state.get("decor", []):
            try:
                self.decor.append(Decor(self, d["kind"], d["x"], d.get("uses", 0),
                                        d.get("variant"), d.get("grow")))
            except Exception as e:
                log_error(f"decor load: {e!r}")
        for m in state.get("messes", []):
            try:
                self.messes.append(Mess(self, m["kind"], m["x"]))
            except Exception as e:
                log_error(f"mess load: {e!r}")
        for a in state.get("animals", []):
            try:
                self.animals.append(Animal(
                    self, a["species"], a.get("gender"), a.get("genes"),
                    a.get("name", ""), a.get("birth"), a.get("hunger"),
                    lifespan=a.get("lifespan")))
            except Exception as e:
                log_error(f"animal load: {e!r}")
        if state.get("kitten") and not state.get("animals"):
            # migrate the old single kitten into the new companion flock
            kc = state.get("kitten_color") or (
                "ginger" if state["color"] == "black" else "black")
            try:
                self.animals.append(Animal(self, "cat", genes={
                    "pal": dict(variant_pal(kc)), "shiny": False,
                    "ability": None, "size": 1.0, "ultra": False},
                    name=state.get("kitten_name", "")))
            except Exception as e:
                log_error(f"kitten migrate: {e!r}")
        self.last_tick = time.monotonic()
        self.after(TICK_MS, self.tick)

    # ---- images / layout ----------------------------------------------

    def _build_images(self):
        s = self.scale
        cos = COSTUMES.get(self.costume, COSTUMES["none"])
        spec = SPECIES.get(self.species, SPECIES["cat"])
        if self.species == "cat":
            pal = variant_pal(self.persist.get("color", "black"))
        else:
            pal = dict(PAL, **spec["pal"])      # species fur colors
        pal = dict(pal, **cos["pal"])           # costume eye-tint on top
        frames = dict(FRAMES)
        frames.update(species_frame_overrides(self.species))
        self.cw, self.ch = int(42 * s), int(36 * s)
        self.canvas.config(width=self.cw, height=self.ch)
        self.images = {}
        for name, rows in frames.items():
            self.images[(name, 1)] = frame_to_photo(rows, s, pal=pal)
            self.images[(name, -1)] = frame_to_photo(rows, s, flip=True, pal=pal)
        ms = max(2, int(s) - 1)
        self.icon_images = {k: frame_to_photo(v, ms) for k, v in ICONS.items()}
        self.mouse_small = {1: frame_to_photo(CRITTER_FRAMES["flat"], ms),
                            -1: frame_to_photo(CRITTER_FRAMES["flat"], ms, flip=True)}
        # accessory overlays: species feature (e.g. dragon wings) + costume,
        # composited so a costumed dragon still shows both
        self.acc_img = {}
        overlays = {"behind": _compose_arts([spec.get("behind"), cos["behind"]]),
                    "front": _compose_arts([spec.get("front"), cos["front"]])}
        for slot, art in overlays.items():
            if art is not None:
                self.acc_img[(slot, 1)] = frame_to_photo(art, s)
                self.acc_img[(slot, -1)] = frame_to_photo(art, s, flip=True)
        self.canvas.delete("all")
        self.acc_behind = (self.canvas.create_image(0, 0, anchor="c")
                           if ("behind", 1) in self.acc_img else None)
        self.sprite_item = self.canvas.create_image(self.cw // 2, self.ch,
                                                    anchor="s", image=None)
        self.acc_front = (self.canvas.create_image(0, 0, anchor="c")
                          if ("front", 1) in self.acc_img else None)
        self.bubble = None
        self.effects = []
        self.mouth_item = None
        if getattr(self, "carrying", False):
            self.mouth_item = self.canvas.create_image(0, 0, image=self.mouse_small[1])

    def _place(self):
        self.geometry(f"+{int(self.x - self.cw / 2 + self.sdx)}"
                      f"+{int(self.y - self.ch + getattr(self, '_gait_dy', 0) + self.sdy)}")

    def feet_to_canvas(self, sx, sy):
        """Convert screen coords to canvas coords."""
        return sx - (self.x - self.cw / 2), sy - (self.y - self.ch)

    # ---- needs ----------------------------------------------------------

    def need_low(self):
        worst = min(self.needs, key=self.needs.get)
        return worst if self.needs[worst] < 35 else None

    def is_sad(self):
        return min(self.needs.values()) < 12

    def update_needs(self, dt):
        for k, rate in DECAY.items():
            self.needs[k] = max(0.0, self.needs[k] - rate * dt)
        if self.can("litter"):
            self.potty = max(0.0, self.potty - (100 / (5 * 3600)) * dt)
        else:
            self.potty = 100.0          # only litter-using species track a bladder
        # a dirty home slowly bums her out (motivates cleaning, but bounded)
        if self.messes:
            self.needs["love"] = max(0.0, self.needs["love"]
                                     - min(len(self.messes), 6) * 0.05 * dt)

    # ---- lifecycle ------------------------------------------------------

    def life_stage(self):
        age = time.time() - self.created_ts
        egg = SPECIES[self.species]["spawn"] == "egg"
        if egg and age < EGG_DUR:
            return "egg"
        a = age - (EGG_DUR if egg else 0)
        for name, bound in STAGE_BOUNDS:
            if a < bound:
                return name
        return "elder" if self.immortal else "passing"

    def _age_scale(self, stage):
        return round(max(1.4, self.base_scale * STAGE_FACTOR.get(stage, 1.0)), 2)

    def _young(self):
        return self.stage in ("egg", "baby")

    def _old(self):
        return self.stage in ("elder", "passing")

    def age_text(self):
        age = max(0, int(time.time() - self.created_ts))
        d, rem = divmod(age, 86400)
        h, rem = divmod(rem, 3600)
        m = rem // 60
        if d:
            return f"{d}d {h}h"
        return f"{h}h {m}m" if h else f"{m}m"

    def _on_stage_change(self, old, new):
        self.stage = new
        self.scale = self._age_scale(new)
        self._build_images()
        self._rescale_props()          # keep kitten/furniture sized to the pet
        if new == "passing":
            self._start_passing()
            return
        if old == "egg" and new == "baby":
            self.set_state("hatch", "hatch", 1.5)   # crack out of the shell!
            return
        if STAGE_ORDER.index(new) > STAGE_ORDER.index(old):
            self._birthday(new)

    def _birthday(self, new):
        self._say("🎂", dur=2.2)
        for _ in range(10):
            self._confetti()
        self.needs["love"] = min(100.0, self.needs["love"] + 8)
        self.play_snd(self.voice(), force=True)
        self._stash_save()

    def voice(self):
        return SPECIES[self.species]["voice"]

    def voice_word(self):
        return random.choice(VOICE_WORDS.get(self.voice(), ("mrrp",)))

    def _start_passing(self):
        # a long, full life — a gentle goodbye, then a new little one arrives
        self.surface_hwnd = self.surface_last = self.perch = None
        self.carrying = False
        nm = self.name or SPECIES[self.species]["name"]
        self._say(f"bye {nm} 🌈", dur=3.0)
        for _ in range(8):
            self._float_icon("heart", dx=random.uniform(-12, 12) * self.scale / 3)
        self.set_state("passing", "sleep", 4.0)

    def st_passing(self, dt):
        if random.random() < 0.25:
            f = self.canvas.create_text(
                self.cw / 2 + random.uniform(-14, 14), self.ch - 24 * self.scale,
                text=random.choice(("🌸", "✦", "♥")), fill="#ffd966",
                font=("Segoe UI", 3 + int(2 * self.scale)))
            self.effects.append({"id": f, "t": 1.5, "vy": -22})
        if self.state_t >= self.plan_dur:
            self.begin_new_pet(random.choice(list(SPECIES)), reborn=True)

    def begin_new_pet(self, species, reborn=False):
        if species not in SPECIES:
            species = "cat"
        # clear any in-flight companions/props of the previous pet
        for attr in ("critter", "bird", "toy", "laser"):
            obj = getattr(self, attr, None)
            if obj is not None:
                obj.despawn() if hasattr(obj, "despawn") else obj.destroy()
                setattr(self, attr, None)
        self.carrying = False
        if self.mouth_item is not None:
            try:
                self.canvas.delete(self.mouth_item)
            except tk.TclError:
                pass
            self.mouth_item = None
        self.species = species
        self.created_ts = time.time()
        self.name = ""
        self.costume = "none"
        self.needs = {"hunger": 85.0, "thirst": 85.0, "love": 80.0}
        self.potty = 85.0
        self.perch = None
        self.surface_hwnd = self.surface_last = None
        self.x = (self.wa[0] + self.wa[2]) / 2
        self.y = self.ground()
        self.stage = self.life_stage()
        self.scale = self._age_scale(self.stage)
        self._build_images()
        if SPECIES[species]["spawn"] == "stork":
            # hide the baby off-screen; the stork carries it in and drops it
            self._delivered = False
            self.y = self.wa[1] - 300
            self.set_state("delivering", "land", 30)
            self._start_stork()
        else:
            self.set_state("egg", "egg", 9999)
            self.play_snd("chirp", force=True)
        self._float_icon("heart")
        self._stash_save()

    def st_delivering(self, dt):
        pass            # wait off-screen until the stork drops us (or a fallback)

    def _stork_drop(self, x, y):
        if getattr(self, "_delivered", True):
            return
        self._delivered = True
        self.x = min(max(float(x), self.wa[0] + 20), self.wa[2] - 20)
        self.y = float(y)
        self.vy = 0.0
        self._float_icon("heart")
        self.play_snd(self.voice(), force=True)
        self.set_state("fall", "fall")    # the bundle drops and the baby lands

    def _start_stork(self):
        if self.stork is not None:
            self.stork.despawn()
        try:
            self.stork = Stork(self, self.x)
        except Exception as e:
            log_error(f"stork: {e!r}")
            self.stork = None

    def st_egg(self, dt):
        # the egg sits and incubates; wobble more as it gets close to hatching
        if random.random() < 0.04:
            self.shake = max(self.shake, 4 * self.scale)
            self.play_snd(self.voice())

    def st_hatch(self, dt):
        self.shake = max(self.shake, 6 * self.scale)
        if self.state_t >= self.plan_dur:
            for _ in range(10):
                self._confetti()
            self._say("hi! 🐣", dur=2.0)
            self.play_snd(self.voice(), force=True)
            self.needs["love"] = min(100.0, self.needs["love"] + 5)
            self.set_state("idle", "idle", 2)

    # ---- state machine --------------------------------------------------

    def set_state(self, state, anim=None, dur=None):
        self.state = state
        self.state_t = 0.0
        self.anim = anim or state
        if dur is not None:
            self.plan_dur = dur

    def report_callback_exception(self, exc, val, tb):
        log_error(f"callback: {val!r}")

    def tick(self):
        if self._quitting:
            return
        if self.menu_open:
            # cat state is frozen under the menu, but the props keep living
            now = time.monotonic()
            dt = min(0.25, now - self.last_tick)
            self.last_tick = now
            try:
                self.cur = cursor_pos()
                if self.laser is not None:
                    self.laser.tick(dt)
                if self.toy is not None:
                    self.toy.tick(dt)
            except Exception as e:
                log_error(f"tick(menu): {e!r}")
            self.after(TICK_MS, self.tick)
            return
        try:
            now = time.monotonic()
            dt = min(0.25, now - self.last_tick)
            self.last_tick = now
            self.update_needs(dt)
            self.state_t += dt
            self.chase_cd = max(0.0, self.chase_cd - dt)
            self.beg_cd = max(0.0, self.beg_cd - dt)
            for k in self.behavior_cd:
                self.behavior_cd[k] = max(0.0, self.behavior_cd[k] - dt)

            # aging: detect a stage change (hatch / birthday / passing)
            ns = self.life_stage()
            if ns != self.stage:
                self._on_stage_change(self.stage, ns)
            elif self.stage == "passing" and self.state != "passing":
                self._start_passing()          # crossed the threshold while closed
            elif (self.stage == "egg" and self.state not in ("egg", "dangle")
                    and self.y >= self.ground()):
                self.set_state("egg", "egg", 9999)   # but let a dropped egg fall first

            if self.stork is not None:           # the delivery flyover
                self.stork.tick(dt)
                if not self.stork.alive:
                    self.stork = None
            # safety: if the delivery never happened, drop the baby anyway
            if self.state == "delivering" and not self._delivered and self.stork is None:
                self._stork_drop((self.wa[0] + self.wa[2]) / 2,
                                 self.wa[1] + 0.2 * (self.wa[3] - self.wa[1]))

            # screen-shake (read by the cat and every prop's _place)
            self.shake = max(0.0, self.shake - dt * 55)
            if self.shake > 0.6:
                self.sdx = random.uniform(-1, 1) * self.shake
                self.sdy = random.uniform(-1, 1) * self.shake
            else:
                self.sdx = self.sdy = 0.0
            # floor props are only re-placed every ~4s, so nudge them while a
            # shake is live (and one frame after, to snap them back to rest)
            if self.shake > 0 or self._shaking_prev:
                for d in self.decor + self.messes:
                    d._place()
            self._shaking_prev = self.shake > 0

            self._track_cursor(now)
            self._maintain_surface(dt)
            self._maintain_perch(dt)

            # the mouse comes and goes on its own schedule
            if self.critter is not None:
                self.critter.tick(dt)
                if not self.critter.alive:
                    self.critter = None
                    self.next_mouse = now + random.uniform(360, 900)
            elif now > self.next_mouse:
                self.critter = Critter(self)

            if self.laser is not None:
                self.laser.tick(dt)
                if now > self.laser_until:   # the red dot mysteriously vanishes
                    self.laser.destroy()
                    self.laser = None
                    if self.state == "laser":
                        self.needs["love"] = min(100.0, self.needs["love"] + 10)
                        if random.random() < 0.25:
                            self.do_flip()
                        else:  # it's gone?? ...anyway, bath time
                            self.set_state("groom", "groom", 4)

            if self.toy is not None:
                self.toy.tick(dt)
                # cat kicks don't keep it alive — only the user does
                if now - self.toy.user_touch > 150 and not self.toy.held:
                    self.toy.despawn()
                    self.toy = None
                    if self.state in ("toy_chase", "toy_bat"):
                        self.set_state("idle", "idle", 2)

            # birds visit on their own schedule
            if self.bird is not None:
                self.bird.tick(dt)
                if not self.bird.alive:
                    self.bird = None
                    self.next_bird = now + random.uniform(120, 320)
            elif now > self.next_bird:
                self.bird = Bird(self)

            handler = getattr(self, "st_" + self.state, None)
            if handler:
                handler(dt)

            self._tick_ecosystem(dt)      # the companion flock lives its life

            self._draw()
            self._tick_effects(dt)

            if now - self.last_top > 4.0:
                self.last_top = now
                for d in self.decor + self.messes:   # furniture/messes behind cat
                    try:
                        d.win.attributes("-topmost", True)
                        d.win.lift()
                    except tk.TclError:
                        pass
                self.attributes("-topmost", True)
                self.lift()
                for pet in ([self.critter, self.toy, self.laser, self.bird]
                            + list(self.animals)):
                    if pet is not None:
                        try:
                            pet.win.attributes("-topmost", True)
                            pet.win.lift()
                        except tk.TclError:
                            pass
                self.wa = work_area()
                for d in self.decor + self.messes:   # floor-anchored
                    d._place()
                # re-pin to the floor if the work area changed under us
                if (self.surface_hwnd is None and self.perch is None
                        and self.jump is None and self.state not in AIR_STATES):
                    if self.y > self.ground():
                        self.y = self.ground()
                    elif self.y < self.ground():
                        self.start_fall()
                c = self.critter
                if (c is not None and c.alive
                        and not (c.caught and c.dropped_t is None)
                        and c.y != self.ground()):
                    c.y = self.ground()
                    c._place()
            if now - self.last_save > 60:
                self._stash_save()
            self.err_streak = 0
        except Exception as e:
            self.err_streak += 1
            log_error(f"tick: {e!r}")
            if self.err_streak > 60:
                self.quit_app()
                return
        self.after(TICK_MS, self.tick)

    def _stash_save(self):
        self.last_save = time.monotonic()
        self.persist.update(
            self.needs, scale=self.base_scale,    # the user's Size tier, not age scale
            potty=self.potty, name=self.name, costume=self.costume,
            species=self.species, created_ts=self.created_ts, immortal=self.immortal,
            kitten=False,
            decor=[{"kind": d.kind, "x": d.x, "uses": d.uses,
                    "variant": d.variant, "grow": round(d.grow, 3)}
                   for d in self.decor],
            messes=[{"kind": m.kind, "x": m.x} for m in self.messes],
            animals=[a.to_save() for a in self.animals if a.alive and not a.dying])
        save_state(self.persist)

    def play_snd(self, kind, force=False):
        if not self.persist.get("sounds", True):
            return
        now = time.monotonic()
        if not force and now < self._snd_cd:
            return
        self._snd_cd = now + 4.0
        play_sound(kind)

    def _track_cursor(self, now):
        cx, cy = cursor_pos()
        self.cursor_hist.append((now, cx, cy))
        while self.cursor_hist and now - self.cursor_hist[0][0] > 1.2:
            self.cursor_hist.pop(0)
        self.cur = (cx, cy)

    def cursor_activity(self):
        h = self.cursor_hist
        return sum(math.dist(h[i][1:], h[i - 1][1:]) for i in range(1, len(h)))

    def ground(self):
        return float(self.wa[3])

    def can(self, trait):
        """Does this pet's species naturally do this behaviour? (see SPECIES_TRAITS)"""
        return trait in SPECIES_TRAITS.get(self.species, set())

    # ---- ecosystem ------------------------------------------------------

    def has_food_for(self, diet, exclude=None):
        """Is there anything this diet could eat in the world right now?"""
        if diet == "herb":
            return any(d.edible() for d in self.decor)
        return any(o is not exclude and o.alive and not o.dying and o.diet == "herb"
                   and o.state != "dangle" for o in self.animals)

    def nearest_food(self, x):
        best, bd = None, 1e9
        for d in self.decor:
            if d.edible():
                dd = abs(d.x - x)
                if dd < bd:
                    best, bd = d, dd
        return best

    def nearest_prey(self, animal):
        best, bd = None, 700
        for o in self.animals:
            if (o is not animal and o.alive and not o.dying and o.diet == "herb"
                    and o.state != "dangle"):     # not while the user is holding it
                dd = abs(o.x - animal.x)
                if dd < bd:
                    best, bd = o, dd
        return best

    def nearest_threat(self, animal):
        best, bd = None, 240
        for o in self.animals:
            if (o is not animal and o.alive and not o.dying and o.diet == "carn"
                    and o.hunger < 60 and o.state != "dangle"):
                dd = abs(o.x - animal.x)
                if dd < bd:
                    best, bd = o, dd
        return best

    def nearest_mate(self, animal):
        # prefer a same-species mate; fall back to another species (-> hybrids)
        best, bd, alt, ad = None, 520, None, 520
        for o in self.animals:
            if (o is not animal and o.alive and not o.dying and o.gender != animal.gender
                    and o.is_adult() and o.hunger > 55 and o.breed_cd <= 0
                    and o.state != "dangle"):
                dd = abs(o.x - animal.x)
                if o.species == animal.species:
                    if dd < bd:
                        best, bd = o, dd
                elif dd < ad:
                    alt, ad = o, dd
        return best or alt

    def spawn_animal(self, species, gender=None, genes=None, x=None, name=""):
        if len(self.animals) >= self.animal_cap:
            return None
        try:
            an = Animal(self, species, gender=gender, genes=genes, x=x, name=name)
            self.animals.append(an)
            return an
        except Exception as e:
            log_error(f"spawn_animal: {e!r}")
            return None

    def _tick_ecosystem(self, dt):
        # nothing to simulate only if there are no animals AND no plants to grow/regrow
        if not self.animals and not self.decor:
            return
        for d in self.decor:
            d.regrow(dt)
        births = []
        for an in self.animals:
            an.tick(dt)
            if an.want_baby is not None and len(self.animals) + len(births) < self.animal_cap:
                mate = an.want_baby
                an.want_baby = None
                genes = breed_genes(an.genes, mate.genes)
                # hybrids: rare chance the baby takes the other parent's species
                sp = an.species
                if an.species != mate.species and random.random() < 0.5:
                    sp = mate.species
                births.append((sp, genes, (an.x + mate.x) / 2))
            else:
                an.want_baby = None
        for sp, genes, bx in births:
            baby = self.spawn_animal(sp, genes=genes, x=bx)
            if baby is not None:
                baby.birth = time.time()          # born a baby
                baby.hunger = 70.0
                self._float_icon("heart")
                if genes.get("ultra"):
                    self._say("✨ ULTRA RARE! ✨", dur=3.0)
                elif genes.get("shiny"):
                    self._say("✨ a shiny! ✨", dur=2.5)
        # bury the dead
        dead = [a for a in self.animals if not a.alive]
        for a in dead:
            a.destroy()
        if dead:
            self.animals = [a for a in self.animals if a.alive]

    def _maintain_surface(self, dt):
        """If standing on a window, follow gentle drifts; rage-quit if jostled."""
        if self.surface_hwnd is None:
            return
        if self.state in ("dangle", "fall", "jump", "madfall", "mad"):
            return
        rect = window_rect(self.surface_hwnd)
        if rect is None:                      # window closed/minimized under her
            self.start_angry_fall()
            return
        l, t, r, b = rect
        if self.surface_last:
            dl = l - self.surface_last[0]
            dtop = t - self.surface_last[1]
            self.surface_move = self.surface_move * 0.5 + max(abs(dl), abs(dtop))
            self.x += dl                      # ride small drifts along
            if self.surface_move > 26:        # someone is yanking the window around
                self.surface_last = rect
                self.start_angry_fall()
                return
        self.surface_last = rect
        if abs(self.y - t) > 240 or not (l - 10 <= self.x <= r + 10):
            self.start_fall()
        else:
            self.y = float(t)

    def _maintain_perch(self, dt):
        """Keep the cat sitting on top of the box she perched on."""
        if self.perch is None:
            return
        if self.state in ("dangle", "fall", "jump", "madfall"):
            return
        if self.perch not in self.decor:      # box was removed under her
            self.perch = None
            self.start_fall()
            return
        box = self.perch
        self.x = min(max(self.x, box.x - box.cw / 2 + 4 * self.scale),
                     box.x + box.cw / 2 - 4 * self.scale)
        if self.state in ("perchsit", "perchsleep"):
            self.y = box.top_y()

    def windows(self):
        now = time.monotonic()
        if now - self.windows_cache_t > 2.5:
            self.windows_cache_t = now
            try:
                self.windows_cache = list_app_windows(self.winfo_id())
            except Exception:
                self.windows_cache = []
        return self.windows_cache

    # ---- idle decision making -------------------------------------------

    def st_idle(self, dt):
        self.anim = "sad" if self.is_sad() else "idle"
        self._face_cursor_sometimes()
        if self._maybe_potty():
            return
        if self._maybe_laser():
            return
        if self._maybe_bird():
            return
        if self._maybe_hunt():
            return
        if self._maybe_toy():
            return
        if self._maybe_chase():
            return
        if self._maybe_beg():
            return
        if self.state_t >= self.plan_dur:
            self.choose_behavior()

    def st_lie(self, dt):
        if self._maybe_potty():
            return
        if self._maybe_laser():
            return
        if self._maybe_bird():
            return
        if self._maybe_hunt():
            return
        if self._maybe_toy():
            return
        if self._maybe_chase():
            return
        if self.state_t >= self.plan_dur:
            self.choose_behavior()

    def st_groom(self, dt):
        if self.state_t >= self.plan_dur:
            self.set_state("idle", "idle", random.uniform(2, 5))

    def _face_cursor_sometimes(self):
        if random.random() < 0.01:
            self.facing = 1 if self.cur[0] >= self.x else -1

    def choose_behavior(self):
        on_window = self.surface_hwnd is not None
        hour = time.localtime().tm_hour
        night = hour >= 22 or hour < 7
        young, old = self._young(), self._old()
        # babies and elders nap far more
        sleepw = (3.5 if (young or old) else 0.9) * (2.2 if night else 1.0)
        options = [("idle", 3.0), ("wander", 3.0)]
        if not on_window:
            options += [("lie", 2.0 if old else 1.2), ("groom", 1.6)]
            if self.behavior_cd["sleep"] <= 0:
                options.append(("sleep", sleepw))
            # the spry middle stages do the athletic stuff (species-appropriate only)
            if not young and not old:
                if self.can("scratch") and self.behavior_cd["scratch"] <= 0:
                    options.append(("go_scratch", 1.1))
                if self.can("climb") and self.behavior_cd["climb"] <= 0 and self.windows():
                    options.append(("go_climb", 2.6))
                if self.can("scratch") and self.behavior_cd["icon"] <= 0:
                    options.append(("go_icon", 0.8))
                if self.can("tailchase") and self.behavior_cd["tailchase"] <= 0:
                    options.append(("tailchase", 0.6))
                if self.can("zoomies"):
                    options.append(("zoomies_auto", 0.7 if night else 0.22))
            elif young and self.can("tailchase") and self.behavior_cd["tailchase"] <= 0:
                options.append(("tailchase", 1.0))     # young ones chase their tail
            if self.decor and self.behavior_cd["decor"] <= 0:
                options.append(("go_decor", 2.4))
        else:
            options += [("hop_down", 2.0)]
            if self.behavior_cd["sleep"] <= 0:
                options.append(("sleep", 0.7))
        total = sum(w for _, w in options)
        pick = random.uniform(0, total)
        for name, w in options:
            pick -= w
            if pick <= 0:
                break
        getattr(self, "do_" + name)()

    def do_idle(self):
        self.set_state("idle", "idle", random.uniform(2.5, 7))

    def do_lie(self):
        self.set_state("lie", "lie", random.uniform(5, 12))

    def do_groom(self):
        self.set_state("groom", "groom", random.uniform(2.5, 5))

    def do_sleep(self):
        hour = time.localtime().tm_hour
        night = hour >= 22 or hour < 7
        self.behavior_cd["sleep"] = random.uniform(240, 480)
        self.set_state("sleep", "sleep",
                       random.uniform(45, 120) * (2.0 if night else 1.0))

    def do_tailchase(self):
        self.behavior_cd["tailchase"] = random.uniform(180, 420)
        self.set_state("tailchase", "tailchase", random.uniform(2.2, 4.0))

    def do_zoomies_auto(self):
        # sudden cat madness, especially at 3 a.m.
        self.after_walk = None
        self.zoom_passes = 2
        self.zoom_flip = random.random() < 0.4
        target = (self.wa[0] + 60 if self.x > (self.wa[0] + self.wa[2]) / 2
                  else self.wa[2] - 60)
        self.walk_target = target
        self.set_state("zoomies", "run", 25)

    def st_tailchase(self, dt):
        # quick facing flips read as spinning after the tail
        self.facing = 1 if int(self.state_t * 3) % 2 == 0 else -1
        if self.state_t >= self.plan_dur:
            self.set_state("idle", "idle", 3)  # dizzy little pause

    def st_stretch(self, dt):
        if self.state_t >= self.plan_dur:
            self.set_state("idle", "idle", random.uniform(2, 4))

    def do_wander(self):
        self.after_walk = None
        if self.surface_hwnd and self.surface_last:
            l, t, r, b = self.surface_last
            if random.random() < 0.35:   # perch right on a corner
                target = random.choice((l + 16, r - 16))
            else:
                target = random.uniform(l + 30, r - 30)
        else:
            target = random.uniform(self.wa[0] + 40, self.wa[2] - 40)
        self.walk_target = target
        self.facing = 1 if target > self.x else -1
        self.set_state("walk", "walk", 30)

    def do_go_scratch(self):
        self.behavior_cd["scratch"] = random.uniform(90, 240)
        spots = []
        for hwnd, (l, t, r, b) in self.windows():
            if b < self.ground() - 60:
                continue  # edge doesn't reach the floor
            for edge_x, face in ((l, 1), (r, -1)):
                # stand beside the edge, facing it
                stand = edge_x - face * (10 * self.scale)
                if self.wa[0] + 30 < stand < self.wa[2] - 30 and t < self.ground() - 80:
                    spots.append((stand, face))
        if not spots:
            self.do_wander()
            return
        stand, face = random.choice(spots)
        self.walk_target = stand
        self.after_walk = ("scratch", face)
        self.facing = 1 if stand > self.x else -1
        self.set_state("walk", "walk", 30)

    def do_go_icon(self):
        self.behavior_cd["icon"] = random.uniform(120, 300)
        icons = desktop_icon_rects()
        reach = self.ground() - 26 * self.scale
        good = [ic for ic in icons
                if ic[3] > reach - 60 and self.wa[0] + 20 < (ic[0] + ic[2]) / 2 < self.wa[2] - 20]
        if not good:
            self.do_wander()
            return
        ic = random.choice(good)
        cx = (ic[0] + ic[2]) / 2
        stand = cx + random.choice((-1, 1)) * 8 * self.scale
        stand = min(max(stand, self.wa[0] + 22), self.wa[2] - 22)
        self.walk_target = stand
        self.after_walk = ("scratch", 1 if cx >= stand else -1)
        self.facing = 1 if stand > self.x else -1
        self.set_state("walk", "walk", 30)

    def climb_targets(self):
        """Windows the cat could scale: a side that runs from near the floor
        up to a visible title bar (so she never climbs empty air)."""
        cands = []
        for hwnd, (l, t, r, b) in self.windows():
            if (r - l > 220 and self.wa[1] - 6 <= t <= self.ground() - 80
                    and b >= self.ground() - 90
                    and self.wa[0] + 4 < (l + r) / 2 < self.wa[2] - 4):
                cands.append((hwnd, (l, t, r, b)))
        return cands

    def do_go_climb(self):
        self.behavior_cd["climb"] = random.uniform(45, 110)
        cands = self.climb_targets()
        if not cands:
            self.do_wander()
            return
        # prefer a window the cat is already under, else the topmost one
        def key(c):
            l, t, r, b = c[1]
            return 0 if l <= self.x <= r else min(abs(self.x - l), abs(self.x - r))
        hwnd, (l, t, r, b) = min(cands, key=key)
        # climb the nearest vertical edge, kept on-screen (maximized windows
        # climb the screen edge; floating windows climb their own side)
        if abs(self.x - l) <= abs(self.x - r):
            side, edge = 1, l        # left edge: cat faces right, window to its right
        else:
            side, edge = -1, r       # right edge: cat faces left
        col = min(max(edge, self.wa[0] + 6 * self.scale),
                  self.wa[2] - 6 * self.scale)
        self.walk_target = col
        self.after_walk = ("wallclimb", (hwnd, side, col))
        self.facing = 1 if col > self.x else -1
        self.set_state("walk", "walk", 30)

    def do_hop_down(self):
        self.surface_hwnd = None
        self.surface_last = None
        x1 = min(max(self.x + self.facing * 90, self.wa[0] + 40), self.wa[2] - 40)
        self.start_jump(x1, self.ground(), anim="fall")
        self.after_jump = ("idle", None)

    # ---- furniture interaction ---------------------------------------------

    def do_go_decor(self):
        self.behavior_cd["decor"] = random.uniform(12, 35)
        # the litter box is driven by the potty urge, not idle curiosity
        blocked = {"litter", "grass", "tree", "pond", "bush", "flower"}
        if not self.can("scratch"):          # only clawing species use the post/plant
            blocked |= {"post", "plant"}
        if not self.can("box"):              # only box-dwellers hop in the box
            blocked.add("box")
        usable = [d for d in self.decor if d.kind not in blocked]
        if not usable:
            self.do_wander()
            return
        # head for a bowl that matches a low need, else any item
        pick = None
        low = self.need_low()
        want = {"hunger": "food", "thirst": "water"}.get(low)
        if want:
            bowls = [d for d in usable if d.kind == want]
            if bowls:
                pick = min(bowls, key=lambda d: abs(d.x - self.x))
        if pick is None:
            pick = random.choice(usable)
        self.decor_target = pick
        if pick.kind in ("post", "plant"):
            target = pick.x - 12 * self.scale
        else:
            target = pick.x
        target = min(max(target, self.wa[0] + 16), self.wa[2] - 16)
        self.walk_target = target
        self.after_walk = ("decor", pick)
        self.facing = 1 if target > self.x else -1
        self.set_state("walk", "walk", 30)

    def _begin_decor(self, decor):
        if decor not in self.decor:
            self.set_state("idle", "idle", 2)
            return
        self.decor_target = decor
        k = decor.kind
        if k == "bed":
            self.x = min(max(decor.x, self.wa[0] + 16), self.wa[2] - 16)
            self.set_state("sleep", "sleep", random.uniform(30, 80))
        elif k in ("food", "water"):
            self.x = min(max(decor.x, self.wa[0] + 16), self.wa[2] - 16)
            self.facing = 1
            self._decor_need = "hunger" if k == "food" else "thirst"
            self.set_state("munch", "munch", 4.0)
        elif k == "post":
            self.facing = 1 if decor.x >= self.x else -1
            self.set_state("scratch", "scratch", random.uniform(3, 6.5))
        elif k == "plant":
            self.facing = 1 if decor.x >= self.x else -1
            self.set_state("plantbat", "bat", random.uniform(2, 4))
        elif k == "box":
            self.start_jump(decor.x, decor.top_y(), anim="pounce", dur=0.45)
            self.after_jump = ("box_land", decor)

    def st_munch(self, dt):
        if self.state_t >= self.plan_dur:
            need = getattr(self, "_decor_need", "hunger")
            self.needs[need] = 100.0
            self.needs["love"] = min(100.0, self.needs["love"] + 2)
            self._float_icon("heart")
            self._say("nom nom~" if need == "hunger" else "*lap lap*")
            self.set_state("groom", "groom", 2.5)

    def st_plantbat(self, dt):
        self.anim = "bat"
        if random.random() < 0.06:
            self._spark()
        if self.state_t >= self.plan_dur:
            self.needs["love"] = min(100.0, self.needs["love"] + 2)
            if random.random() < 0.4:
                self._say("mrrp")
            self.set_state("idle", "idle", random.uniform(2, 4))

    # ---- nature calls ------------------------------------------------------

    def _maybe_potty(self):
        if not self.can("litter"):
            return False
        if (self.potty > 22 or self.surface_hwnd is not None
                or self.perch is not None):
            return False
        self.after_walk = None
        boxes = [d for d in self.decor if d.kind == "litter" and d.uses < 6]
        if boxes:
            box = min(boxes, key=lambda d: abs(d.x - self.x))
            self.walk_target = min(max(box.x, self.wa[0] + 16), self.wa[2] - 16)
            self.after_walk = ("usebox", box)
        else:
            # no clean box — gotta go right here (well, a couple steps over)
            tx = self.x + random.choice((-1, 1)) * random.uniform(30, 150)
            self.walk_target = min(max(tx, self.wa[0] + 30), self.wa[2] - 30)
            self.after_walk = ("gofloor", None)
            self.show_bubble("drop")
        self.facing = 1 if self.walk_target > self.x else -1
        self.set_state("walk", "walk", 30)
        return True

    def st_potty_box(self, dt):
        if self.state_t >= self.plan_dur:
            self.potty = 100.0
            box = self.after_walk_box()
            if box is not None and box in self.decor:
                box.uses += 1
            self.needs["love"] = min(100.0, self.needs["love"] + 1)
            self._stash_save()
            self.set_state("groom", "groom", 2.5)

    def after_walk_box(self):
        # the litter box we just used is the nearest litter decor
        boxes = [d for d in self.decor if d.kind == "litter"]
        return min(boxes, key=lambda d: abs(d.x - self.x)) if boxes else None

    def st_potty_floor(self, dt):
        if self.state_t >= self.plan_dur:
            self.potty = 100.0
            kind = random.choice(("poop", "pee", "pee"))
            if len(self.messes) < 20:
                try:
                    mx = self.x + self.facing * 8 * self.scale
                    self.messes.append(Mess(self, kind, mx))
                except Exception as e:
                    log_error(f"mess spawn: {e!r}")
            self._say("...")
            self._stash_save()
            self.set_state("idle", "idle", random.uniform(2, 4))

    def clean_mess(self, mess):
        if mess in self.messes:
            self.messes.remove(mess)
        mess.destroy()
        self.needs["love"] = min(100.0, self.needs["love"] + 1)
        self._stash_save()

    def clean_all_messes(self):
        for m in self.messes:
            m.destroy()
        self.messes = []
        self._stash_save()

    # ---- bird watching / catching ------------------------------------------

    def _maybe_bird(self):
        if not self.can("birds"):
            return False
        b = self.bird
        if (b is not None and b.alive and not b.caught
                and self.surface_hwnd is None and self.perch is None):
            self.after_walk = None
            self.set_state("birdwatch", "birdwatch", 14)
            return True
        return False

    def st_birdwatch(self, dt):
        b = self.bird
        if b is None or not b.alive or b.caught:
            self.set_state("idle", "idle", 2)
            return
        dx = b.x - self.x
        self.facing = 1 if dx > 0 else -1
        if abs(dx) > 30:
            self.anim = "run"
            self.x += (1 if dx > 0 else -1) * min(abs(dx), 240 * self.scale / 3 * dt)
            self._clamp_x()
        else:
            self.anim = "birdwatch"
            if random.random() < 0.04:        # the famous bird chatter
                self._say("ekekek!")
                self.play_snd("chirp")
        if b.low_enough() and abs(dx) < 55:
            tx = min(max(b.x, self.wa[0] + 16), self.wa[2] - 16)
            self.start_jump(tx, self.ground() - 150 * self.scale, anim="pounce", dur=0.4)
            self.after_jump = ("birdcatch", None)
            return
        if self.state_t > self.plan_dur:
            self.set_state("groom", "groom", 2.5)  # gave up; act unbothered

    def _feather(self):
        x = self.cw / 2 + random.uniform(-16, 16)
        y = self.ch - random.uniform(14, 26) * self.scale
        f = self.canvas.create_text(x, y, text="❜", fill="#f4f4f8",
                                     font=("Segoe UI", 4 + int(2 * self.scale)))
        self.effects.append({"id": f, "t": 0.8, "vy": -16})

    # ---- box perch ----------------------------------------------------------

    def st_perchsit(self, dt):
        self.anim = "sad" if self.is_sad() else "idle"
        if self.state_t >= self.plan_dur:
            r = random.random()
            if r < 0.4:
                self.set_state("perchsleep", "sleep", random.uniform(20, 50))
            elif r < 0.7:
                self.set_state("perchsit", "idle", random.uniform(3, 7))
            else:
                self._hop_off_perch()

    def st_perchsleep(self, dt):
        if random.random() < 0.02:
            self._float_icon("zzz", dx=10 * self.scale, rise=18)
        if self.state_t >= self.plan_dur:
            self.set_state("perchsit", "idle", random.uniform(3, 6))

    def _hop_off_perch(self):
        box = self.perch
        self.perch = None
        if box is not None:
            side = random.choice((-1, 1))
            x1 = box.x + side * (box.cw / 2 + 30 * self.scale)
            x1 = min(max(x1, self.wa[0] + 40), self.wa[2] - 40)
        else:
            x1 = self.x
        self.start_jump(x1, self.ground(), anim="fall")
        self.after_jump = ("idle", None)

    # ---- walking ---------------------------------------------------------

    after_walk = None

    def st_walk(self, dt):
        if self._maybe_laser():
            return
        if self._maybe_hunt():
            return
        if self._maybe_toy():
            return
        if self._maybe_chase():
            self.after_walk = None
            return
        speed = (28 if self.is_sad() else 46) * self.scale * dt
        if self._young() or self._old():        # toddlers and elders amble
            speed *= 0.6
        if self.walk_target is None:
            self.set_state("idle", "idle", 2)
            return
        delta = self.walk_target - self.x
        self.facing = 1 if delta > 0 else -1
        step = min(abs(delta), speed)
        self.x += self.facing * step
        self._clamp_x()
        if abs(delta) < 4 or self.state_t > self.plan_dur:
            self.walk_target = None
            todo, self.after_walk = self.after_walk, None
            if todo is None:
                self.set_state("idle", "idle", random.uniform(2, 6))
            elif todo[0] == "scratch":
                self.facing = todo[1]
                self.set_state("scratch", "scratch", random.uniform(3, 6.5))
            elif todo[0] == "wallclimb":
                hwnd, side, col = todo[1]
                rect = window_rect(hwnd)
                if rect is None:
                    self.set_state("idle", "idle", 2)
                else:
                    l, t, r, b = rect
                    edge = l if side == 1 else r
                    live_col = min(max(edge, self.wa[0] + 6 * self.scale),
                                   self.wa[2] - 6 * self.scale)
                    if abs(live_col - self.x) > 36 * self.scale:
                        self.set_state("idle", "idle", 2)  # window moved off; no teleport
                    else:
                        self.climb_info = (hwnd, side, live_col)
                        speed = 110 * self.scale / 3
                        dur = (self.y - (t + 2)) / speed + 3.0
                        self.set_state("wallclimb", "climb",
                                       max(3.0, min(dur, 32.0)))
            elif todo[0] == "decor":
                self._begin_decor(todo[1])
            elif todo[0] == "usebox":
                box = todo[1]
                if box in self.decor:
                    self.x = min(max(box.x, self.wa[0] + 16), self.wa[2] - 16)
                    self.set_state("potty_box", "potty", random.uniform(3.5, 5))
                else:
                    self.set_state("idle", "idle", 2)   # box vanished; hold it, kid
            elif todo[0] == "gofloor":
                self.set_state("potty_floor", "potty", random.uniform(2.5, 4))

    def _clamp_x(self):
        if self.surface_hwnd and self.surface_last:
            l, t, r, b = self.surface_last
            self.x = min(max(self.x, l + 12), r - 12)
        else:
            self.x = min(max(self.x, self.wa[0] + 16), self.wa[2] - 16)

    # ---- scratching -------------------------------------------------------

    def st_wallclimb(self, dt):
        hwnd, side, col = self.climb_info
        rect = window_rect(hwnd)
        if rect is None:
            self.start_fall()
            return
        l, t, r, b = rect
        edge = l if side == 1 else r
        # keep glued to the (possibly moved) edge, always on-screen
        col = min(max(edge, self.wa[0] + 6 * self.scale), self.wa[2] - 6 * self.scale)
        self.climb_info = (hwnd, side, col)
        self.x = col
        self.facing = 1 if side == 1 else -1
        self.y -= 110 * self.scale / 3 * dt
        if self.y <= t + 2:
            # made it! step inward onto the title bar
            self.surface_hwnd = hwnd
            self.surface_last = rect
            self.surface_move = 0.0
            self.y = float(t)
            self.x = min(max(col + side * 16 * self.scale, l + 12), r - 12)
            self.needs["love"] = min(100.0, self.needs["love"] + 1)
            self.play_snd("chirp")
            self.set_state("idle", "idle", random.uniform(4, 9))
        elif self.state_t > self.plan_dur:
            self.start_fall()  # tired halfway up. happens.

    def st_scratch(self, dt):
        # spawn little scratch marks in front of the paws
        if random.random() < 0.18:
            px = self.cw / 2 + self.facing * 11 * self.scale
            py = self.ch - random.uniform(6, 13) * self.scale
            ln = self.canvas.create_line(
                px, py, px + self.facing * 4 * self.scale, py + 2 * self.scale,
                fill="#e8e8f0", width=max(1, self.scale - 1))
            self.effects.append({"id": ln, "t": 0.5, "vy": 0})
        if self.state_t >= self.plan_dur:
            self.needs["love"] = min(100.0, self.needs["love"] + 2)
            self.set_state("idle", "idle", random.uniform(2, 5))

    # ---- sleeping ----------------------------------------------------------

    def st_sleep(self, dt):
        if random.random() < 0.02:
            self._float_icon("zzz", dx=10 * self.scale, rise=18)
        if self.state_t >= self.plan_dur:
            self.set_state("stretch", "stretch", 1.3)

    # ---- begging (needs attention) -----------------------------------------

    def _maybe_beg(self):
        worst = self.need_low()
        if worst and self.beg_cd <= 0:
            self.beg_cd = random.uniform(35, 70)
            food = "veg" if SPECIES_DIET.get(self.species) == "herb" else "fish"
            icon = {"hunger": food, "thirst": "drop", "love": "heart"}[worst]
            self.show_bubble(icon)
            self._say(self.voice_word())
            self.play_snd(self.voice())
            # hold the idle pose while asking
            self.state_t = 0.0
            self.plan_dur = max(self.plan_dur, 2.5)
            return True
        return False

    # ---- laser pointer -----------------------------------------------------------

    def _maybe_laser(self):
        if not self.can("laser"):
            return False
        if self.laser is not None and self.surface_hwnd is None:
            self.after_walk = None
            self.set_state("laser", "run", 9999)
            return True
        return False

    def st_laser(self, dt):
        lz = self.laser
        if lz is None:
            self.set_state("groom", "groom", 3.5)
            return
        dx = lz.x - self.x
        self.facing = 1 if dx > 0 else -1
        if abs(dx) < 16 * self.scale:
            if lz.y < self.ground() - 30 * self.scale:
                self.anim = "scratch"      # dot is up the wall: paw at it
            elif random.random() < dt * 2.2:
                tx = min(max(lz.x, self.wa[0] + 16), self.wa[2] - 16)
                self.start_jump(tx, self.ground(), anim="pounce", dur=0.28)
                self.after_jump = ("laser_land", None)
            else:
                self.anim = "bat"          # swatting at the uncatchable
        else:
            self.anim = "run"
            self.x += self.facing * 300 * self.scale / 3 * dt
            self._clamp_x()

    # ---- yarn ball ------------------------------------------------------------------

    def _maybe_toy(self):
        if not self.can("toy"):
            return False
        t = self.toy
        if t is None or t.held or self.surface_hwnd is not None:
            return False
        # "fast" means the USER just flung it — the cat's own kicks are
        # inside kick_grace, otherwise she'd re-trigger herself forever
        fast = ((abs(t.vx) > 140 or abs(t.vy) > 140)
                and time.monotonic() > t.kick_grace)
        urge = self.behavior_cd["toy"] <= 0 and (t.moving()
                                                 or abs(t.x - self.x) < 420)
        if fast or urge:
            self.after_walk = None
            self.bat_limit = random.randint(4, 8)
            self.bat_count = 0
            self.set_state("toy_chase", "run", 14)
            return True
        return False

    def st_toy_chase(self, dt):
        t = self.toy
        if t is None:
            self.set_state("idle", "idle", 2)
            return
        dx = t.x - self.x
        self.facing = 1 if dx > 0 else -1
        if t.held:
            self.anim = "stalk"            # staring intently at your hand
            return
        if abs(dx) < 13 * self.scale:
            if t.y > self.ground() - 25 * self.scale:
                self.set_state("toy_bat", "bat", 0.4)
            else:
                self.anim = "stalk"        # track the airborne ball until it lands
            return
        self.anim = "run"
        self.x += self.facing * 280 * self.scale / 3 * dt
        self._clamp_x()
        if self.state_t > self.plan_dur:
            self.behavior_cd["toy"] = random.uniform(40, 140)
            self.set_state("lie", "lie", 6)

    def st_toy_bat(self, dt):
        if self.state_t < self.plan_dur:
            return
        t = self.toy
        if (t is not None and not t.held
                and abs(t.x - self.x) < 20 * self.scale
                and t.y > self.ground() - 25 * self.scale):
            t.kick(self.facing * random.uniform(240, 460),
                   -random.uniform(120, 280))
            self.bat_count += 1
            if random.random() < 0.3:
                self._spark()
            self.needs["love"] = min(100.0, self.needs["love"] + 1)
        if self.bat_count >= self.bat_limit:
            # enough. flop down next to it like she never cared.
            self.behavior_cd["toy"] = random.uniform(60, 180)
            self.set_state("lie", "lie", random.uniform(5, 9))
        else:
            self.set_state("toy_chase", "run", 14)

    # ---- backflip ----------------------------------------------------------------------

    def do_flip(self):
        if not self.can("flip"):
            # not a backflipping species — but if we were caught mid-air (e.g. a
            # bear/frog pouncing an elevated cursor), come back down, don't float
            if self.surface_hwnd is None and self.perch is None and self.y < self.ground():
                self.start_fall()
            else:
                self.set_state("idle", "idle", 2)
            return
        self.start_jump(self.x, self.ground(), anim="flip", dur=0.7)
        self.after_jump = ("tada", None)

    # ---- mouse hunting ---------------------------------------------------------

    def _maybe_hunt(self):
        if not self.can("hunt"):
            return False
        c = self.critter
        if (c is not None and c.alive and not c.caught
                and self.surface_hwnd is None and abs(c.x - self.x) < 750):
            self.after_walk = None
            self.facing = 1 if c.x > self.x else -1
            self.set_state("hunt_stalk", "stalk", random.uniform(0.6, 1.2))
            return True
        return False

    def st_hunt_stalk(self, dt):
        c = self.critter
        if c is None or not c.alive or c.caught:
            self.set_state("idle", "idle", 2)
            return
        self.facing = 1 if c.x > self.x else -1
        if self.state_t >= self.plan_dur:
            self.set_state("hunt", "run", 10.0)

    def st_hunt(self, dt):
        c = self.critter
        if c is None or not c.alive or c.caught:
            self.set_state("groom", "groom", 2.5)  # it got away, act casual
            return
        dx = c.x - self.x
        self.facing = 1 if dx > 0 else -1
        if abs(dx) < 60:
            # pounce, leading the running mouse a little
            tx = min(max(c.x + c.dir * 30, self.wa[0] + 16), self.wa[2] - 16)
            self.start_jump(tx, self.ground(), anim="pounce", dur=0.3)
            self.after_jump = ("snag", None)
            return
        self.x += self.facing * 330 * self.scale / 3 * dt
        self._clamp_x()
        if self.state_t > self.plan_dur:
            self.set_state("groom", "groom", 3)

    def st_gotcha(self, dt):
        self.anim = "bat"
        if random.random() < 0.12:
            self._spark()
        if self.state_t >= self.plan_dur:
            self.carrying = True
            self.carry_target = min(max(self.cur[0], self.wa[0] + 30), self.wa[2] - 30)
            if self.mouth_item is None:
                self.mouth_item = self.canvas.create_image(0, 0, image=self.mouse_small[1])
            self.set_state("carry", "walk", 25)

    def st_carry(self, dt):
        delta = self.carry_target - self.x
        self.facing = 1 if delta > 0 else -1
        self.x += self.facing * min(abs(delta), 46 * self.scale * dt)
        self._clamp_x()
        if abs(delta) < 8 or self.state_t > self.plan_dur:
            self._drop_gift(proud=True)

    def _drop_gift(self, proud=False):
        self.carrying = False
        if self.mouth_item is not None:
            self.canvas.delete(self.mouth_item)
            self.mouth_item = None
        if self.critter is not None and self.critter.alive:
            dx = min(max(self.x + self.facing * 14 * self.scale,
                         self.wa[0] + 16), self.wa[2] - 16)
            self.critter.drop_at(dx, self.ground())
        if proud:
            self.needs["love"] = min(100.0, self.needs["love"] + 8)
            self._say("for you!")
            self._float_icon("heart")
            self.play_snd(self.voice(), force=True)
            self.set_state("idle", "idle", 5)

    # ---- cursor chase --------------------------------------------------------

    def _maybe_chase(self):
        if not self.can("hunt"):
            return False
        if self.chase_cd > 0 or self.surface_hwnd is not None:
            return False
        cx, cy = self.cur
        near = math.dist((cx, cy), (self.x, self.y - 20 * self.scale)) < 260
        if near and self.cursor_activity() > 380:
            self.set_state("stalk", "stalk", random.uniform(0.9, 1.7))
            self.facing = 1 if cx > self.x else -1
            return True
        return False

    def st_stalk(self, dt):
        cx, cy = self.cur
        self.facing = 1 if cx > self.x else -1
        if self.state_t >= self.plan_dur:
            self.set_state("chase", "run", 6.0)

    def st_chase(self, dt):
        cx, cy = self.cur
        dist = math.dist((cx, cy), (self.x, self.y - 14 * self.scale))
        self.facing = 1 if cx > self.x else -1
        if dist < 46 * self.scale / 3 + 30:
            self.start_jump(cx, cy + 8 * self.scale, anim="pounce", dur=0.36)
            self.after_jump = ("catch", None)
            return
        if dist > 460:
            self.gone_far_t += dt
        else:
            self.gone_far_t = 0
        self.x += (1 if cx > self.x else -1) * 120 * self.scale / 3 * dt * 2.2
        self._clamp_x()
        if self.state_t > self.plan_dur or self.gone_far_t > 1.6:
            # gave up; restore dignity by grooming
            self.gone_far_t = 0
            self.chase_cd = random.uniform(45, 120)
            self.set_state("groom", "groom", 3.5)

    def st_catch(self, dt):
        self.anim = "bat"
        if random.random() < 0.1:
            self._spark()
        if self.state_t > 0.9:
            self.needs["love"] = min(100.0, self.needs["love"] + 6)
            self.chase_cd = random.uniform(60, 150)
            self._float_icon("heart")
            if random.random() < 0.35:
                self.do_flip()   # victory backflip off the cursor!
            else:
                self.start_fall()

    # ---- jumping / falling ------------------------------------------------------

    def start_jump(self, x1, y1, anim="pounce", dur=0.42):
        self.jump = (self.x, self.y, float(x1), float(y1), dur, 0.0)
        self.set_state("jump", anim)

    def st_jump(self, dt):
        x0, y0, x1, y1, dur, t = self.jump
        t += dt
        f = min(1.0, t / dur)
        self.x = x0 + (x1 - x0) * f
        self.y = y0 + (y1 - y0) * f - math.sin(math.pi * f) * 90
        if x1 != x0:   # vertical flips keep their facing
            self.facing = 1 if x1 > x0 else -1
        self.jump = (x0, y0, x1, y1, dur, t)
        if f >= 1.0:
            self.jump = None
            todo, self.after_jump = self.after_jump, None
            if todo and todo[0] == "catch":
                self.play_snd("chirp")
                self.set_state("catch", "bat", 2)
            elif todo and todo[0] == "laser_land":
                if self.laser is None:
                    # the dot vanished while we were mid-pounce
                    self.needs["love"] = min(100.0, self.needs["love"] + 10)
                    if random.random() < 0.25:
                        self.do_flip()
                    else:
                        self.set_state("groom", "groom", 4)
                else:
                    self.set_state("laser", "bat", 9999)
            elif todo and todo[0] == "tada":
                self.y = self.ground()
                for _ in range(3):
                    self._spark()
                self._say("ta-da!")
                self.play_snd("chirp")
                self.needs["love"] = min(100.0, self.needs["love"] + 2)
                self.set_state("idle", "idle", 3)
            elif todo and todo[0] == "snag":
                c = self.critter
                self.y = self.ground()
                if c is not None and c.alive and not c.caught and abs(c.x - self.x) < 60:
                    c.catch()
                    self.play_snd("chirp")
                    self.set_state("gotcha", "bat", 0.9)
                elif c is not None and c.alive and not c.caught:
                    self.set_state("hunt", "run", 8)  # missed! try again
                else:
                    self.set_state("idle", "idle", 3)
            elif todo and todo[0] == "box_land":
                box = todo[1]
                if box in self.decor:
                    self.perch = box
                    self.surface_hwnd = None
                    self.surface_last = None
                    self.y = box.top_y()
                    self.x = min(max(self.x, box.x - box.cw / 2 + 4 * self.scale),
                                 box.x + box.cw / 2 - 4 * self.scale)
                    self.needs["love"] = min(100.0, self.needs["love"] + 1)
                    self.play_snd("chirp")
                    self.set_state("perchsit", "idle", random.uniform(4, 9))
                else:
                    self.start_fall()
            elif todo and todo[0] == "birdcatch":
                b = self.bird
                if (b is not None and b.alive and not b.caught
                        and abs(b.x - self.x) < 75 and b.low_enough()):
                    b.despawn()
                    self.needs["love"] = min(100.0, self.needs["love"] + 8)
                    for _ in range(6):
                        self._feather()
                    self._say("got it!")
                    self.play_snd("chirp")
                else:
                    self._say("aw...")
                self.start_fall()    # descend from the apex instead of snapping down
            else:
                self.y = self.ground() if self.surface_hwnd is None else self.y
                self.set_state("idle", "idle", random.uniform(2, 5))

    def start_fall(self):
        if self.carrying or self.state == "gotcha":
            self._drop_gift()
        self.surface_hwnd = None
        self.surface_last = None
        self.perch = None
        self.vy = 0.0
        self.set_state("fall", "fall")

    def start_angry_fall(self):
        """Bucked off a window the user dragged — and she is NOT happy."""
        if self.carrying or self.state == "gotcha":
            self._drop_gift()
        self.surface_hwnd = None
        self.surface_last = None
        self.perch = None
        self.vy = 0.0
        self._say(random.choice(ANGRY_WORDS), dur=2.4)
        self.play_snd("hiss")
        self.set_state("madfall", "flipoff")

    def st_madfall(self, dt):
        self.vy += 2600 * dt
        self.y += self.vy * dt
        if self.y >= self.ground():
            self.y = self.ground()
            self.shake = 16 * self.scale     # SLAM — the whole screen jolts
            for _ in range(4):
                self._spark()
            self.play_snd("hiss")
            self.set_state("mad", "flipoff", random.uniform(1.8, 2.8))
            if random.random() < 0.6:
                self._say(random.choice(ANGRY_WORDS), dur=1.8)

    def st_mad(self, dt):
        self.anim = "flipoff"
        if random.random() < 0.05:
            self._spark()
        if self.state_t >= self.plan_dur:
            self.set_state("idle", "idle", random.uniform(2, 4))

    def st_fall(self, dt):
        self.vy += 2600 * dt
        self.y += self.vy * dt
        if self.y >= self.ground():
            self.y = self.ground()
            self.set_state("landing", "land", 0.35)

    def st_landing(self, dt):
        if self.state_t >= self.plan_dur:
            self.set_state("idle", "idle", random.uniform(1.5, 4))

    # ---- dragging / petting -------------------------------------------------------

    def on_press(self, ev):
        self.press = (ev.x_root, ev.y_root, time.monotonic())

    def on_drag(self, ev):
        if self.press is None:
            return
        if self.drag is None:
            if math.dist((ev.x_root, ev.y_root), self.press[:2]) > 9:
                self.drag = True
                self.surface_hwnd = None
                self.surface_last = None
                self.perch = None
                self.after_walk = None
                self.jump = None
                self.after_jump = None
                if self.carrying or self.state == "gotcha":
                    self._drop_gift()  # she drops the mouse when grabbed
                self.set_state("dangle", "dangle")
        if self.drag:
            self.x = float(ev.x_root)
            self.y = float(ev.y_root) + 26 * self.scale  # hang from the scruff
            self._place()

    def on_release(self, ev):
        was_drag = self.drag
        self.drag = None
        self.press = None
        if was_drag:
            self.start_fall()
            return
        # a click without movement = petting
        if self.state == "sleep":
            self.set_state("stretch", "stretch", 1.2)
            self._say("mrrp?")
            return
        self.needs["love"] = min(100.0, self.needs["love"] + 3)
        for _ in range(random.randint(2, 3)):
            self._float_icon("heart", dx=random.uniform(-8, 8) * self.scale / 3)
        if random.random() < 0.45:
            self._say(self.voice_word())
            self.play_snd(self.voice())

    # ---- context menu ----------------------------------------------------------------

    def on_menu(self, ev):
        if self._menu_widget is not None:
            try:
                self._menu_widget.destroy()
            except tk.TclError:
                pass
        menu = tk.Menu(self, tearoff=0, font=("Segoe UI", 10))
        self._menu_widget = menu

        def bar(v):
            full = int(round(v / 10))
            return "█" * full + "░" * (10 - full)

        spname = SPECIES[self.species]["name"]
        who = self.name or spname
        menu.add_command(label=f"{SPECIES_EMOJI.get(self.species, '🐈')}  {who}  ·  {spname}",
                         state="disabled")
        menu.add_command(
            label=f"     {STAGE_LABEL.get(self.stage, self.stage)}  ·  {self.age_text()}",
            state="disabled")
        menu.add_command(label=f"  food   {bar(self.needs['hunger'])}", state="disabled")
        menu.add_command(label=f"  water  {bar(self.needs['thirst'])}", state="disabled")
        menu.add_command(label=f"  love   {bar(self.needs['love'])}", state="disabled")
        if self.can("litter"):
            menu.add_command(label=f"  potty  {bar(self.potty)}", state="disabled")
        menu.add_separator()
        feed_icon = "🥬" if SPECIES_DIET.get(self.species) == "herb" else "🐟"
        menu.add_command(label=f"{feed_icon}  Feed", command=self.act_feed)
        menu.add_command(label="💧  Water", command=self.act_water)
        menu.add_command(label="🍬  Give a treat", command=self.act_treat)

        play = tk.Menu(menu, tearoff=0)
        if self.can("zoomies"):
            play.add_command(label="🏃  Zoomies", command=self.act_play)
        if self.can("laser"):
            play.add_command(label="🔴  Laser: stop" if self.laser else "🔴  Laser pointer",
                             command=self.act_laser)
        if self.can("toy"):
            play.add_command(label="🧶  Put yarn away" if self.toy else "🧶  Toss the yarn",
                             command=self.act_toy)
        if self.can("flip"):
            play.add_command(label="🤸  Do a trick", command=self.act_trick)
        play.add_command(label="👋  Come here", command=self.act_come)      # universal
        play.add_command(label="💤  Nap time", command=self.act_nap)        # universal
        menu.add_cascade(label="🎾  Play", menu=play)

        look = tk.Menu(menu, tearoff=0)
        cos = tk.Menu(look, tearoff=0)
        labels = {"none": "no costume", "bat": "🦇 batcat", "spider": "🕷 spidercat",
                  "wizard": "🧙 wizard", "king": "👑 king", "devil": "😈 devil"}
        for key in ("none", "bat", "spider", "wizard", "king", "devil"):
            cos.add_command(label=("●  " if self.costume == key else "    ") + labels[key],
                            command=lambda k=key: self.act_costume(k))
        look.add_cascade(label="🎭  Costume", menu=cos)
        fur = tk.Menu(look, tearoff=0)
        cur = self.persist.get("color", "black")
        for key in ("black", "ginger", "gray", "snow", "choco"):
            fur.add_command(label=("●  " if cur == key else "    ") + key,
                            command=lambda k=key: self.act_color(k))
        look.add_cascade(label="🎨  Fur", menu=fur)
        size = tk.Menu(look, tearoff=0)
        for label, s in (("smol", 2), ("normal", 3), ("big", 4),
                         ("huge", 6), ("giant", 8)):
            size.add_command(label=("●  " if self.base_scale == s else "    ") + label,
                             command=lambda s=s: self.act_resize(s))
        look.add_cascade(label="📏  Size", menu=size)
        menu.add_cascade(label="🎀  Look", menu=look)

        deco = tk.Menu(menu, tearoff=0)
        for kind in ("bed", "food", "water", "litter", "post", "plant", "box"):
            deco.add_command(label="add  " + DECOR_META[kind]["label"],
                             command=lambda k=kind: self.act_add_decor(k))
        deco.add_separator()
        for kind in ("grass", "flower", "bush", "tree", "pond"):   # plant & scenery
            deco.add_command(label="plant  " + DECOR_META[kind]["label"],
                             command=lambda k=kind: self.act_add_decor(k))
        if self.decor:
            deco.add_separator()
            deco.add_command(label=f"🧹  Clear furniture ({len(self.decor)})",
                             command=self.clear_decor)
        if self.messes:
            deco.add_command(label=f"🧽  Clean up mess ({len(self.messes)})",
                             command=self.clean_all_messes)
        menu.add_cascade(label="🏠  Decorate", menu=deco)

        zoo = tk.Menu(menu, tearoff=0)
        herb = sum(1 for a in self.animals if a.diet == "herb")
        carn = sum(1 for a in self.animals if a.diet == "carn")
        zoo.add_command(label=f"🌍  flock: {len(self.animals)}/{self.animal_cap}"
                              f"   🌿{herb} 🥩{carn}", state="disabled")
        full = len(self.animals) >= self.animal_cap
        zoo.add_command(label="🎲  Surprise me!", state="disabled" if full else "normal",
                        command=self.act_add_random)
        zoo.add_separator()
        # group the 14 species under two tidy diet submenus instead of a long flat list
        for diet_key, diet_label in (("herb", "🌿  Herbivores"), ("carn", "🥩  Carnivores")):
            grp = tk.Menu(zoo, tearoff=0)
            for key, sp in SPECIES.items():
                if SPECIES_DIET.get(key, "carn") != diet_key:
                    continue
                pair = tk.Menu(grp, tearoff=0)
                pair.add_command(label="♂  male",
                                 command=lambda k=key: self.act_add_animal(k, "m"))
                pair.add_command(label="♀  female",
                                 command=lambda k=key: self.act_add_animal(k, "f"))
                pair.add_command(label="♂♀  breeding pair",
                                 command=lambda k=key: self.act_add_pair(k))
                grp.add_cascade(label=f"{SPECIES_EMOJI.get(key, '🐾')}  {sp['name']}",
                                menu=pair)
            zoo.add_cascade(label=diet_label, menu=grp)
        if self.animals:
            zoo.add_separator()
            zoo.add_command(label="🧹  Release all animals", command=self.clear_animals)
        menu.add_cascade(label="🐾  Animals", menu=zoo)

        menu.add_command(label="✏  Rename…", command=self.act_rename)

        newpet = tk.Menu(menu, tearoff=0)
        for key, sp in SPECIES.items():
            born = "🥚 hatch" if sp["spawn"] == "egg" else "🪶 stork"
            newpet.add_command(label=f"{SPECIES_EMOJI.get(key, '🐾')}  {sp['name']}  ({born})",
                               command=lambda k=key: self.act_new_pet(k))
        menu.add_cascade(label="🍼  New pet…", menu=newpet)

        menu.add_command(
            label=f"♾  Immortal: {'on' if self.immortal else 'off'}",
            command=self.act_immortal)
        menu.add_command(
            label=f"🔊  Sounds: {'on' if self.persist.get('sounds', True) else 'off'}",
            command=self.act_sounds)
        menu.add_separator()
        menu.add_command(label="❌  Bye bye (quit)", command=self.quit_app)
        self.menu_open = True
        try:
            menu.tk_popup(ev.x_root, ev.y_root)
        finally:
            menu.grab_release()
            self.menu_open = False

    def _ensure_ground_state(self):
        if self.state in ("jump", "fall", "dangle", "catch", "wallclimb", "madfall"):
            return False
        self.after_walk = None
        if self.carrying or self.state == "gotcha":
            self._drop_gift()
        if self.perch is not None:
            self._hop_off_perch()
            return False
        if self.surface_hwnd is not None:
            self.do_hop_down()
            return False
        return True

    def act_feed(self):
        if self.needs["hunger"] > 92:
            self._say("(full!)")
            return
        if not self._ensure_ground_state():
            return
        self.set_state("eat", "eat", 5.0)

    def act_water(self):
        if self.needs["thirst"] > 92:
            self._say("(no thx)")
            return
        if not self._ensure_ground_state():
            return
        self.set_state("drink", "drink", 4.0)

    def act_play(self):
        if not self.can("zoomies"):
            return
        if not self._ensure_ground_state():
            return
        self.zoom_passes = 3
        self.zoom_flip = random.random() < 0.5
        target = self.wa[0] + 60 if self.x > (self.wa[0] + self.wa[2]) / 2 else self.wa[2] - 60
        self.walk_target = target
        self.set_state("zoomies", "run", 25)

    def act_nap(self):
        if not self._ensure_ground_state():
            return
        self.set_state("sleep", "sleep", random.uniform(60, 120))

    def act_treat(self):
        if not self._ensure_ground_state():
            return
        self.needs["hunger"] = min(100.0, self.needs["hunger"] + 25)
        self.needs["love"] = min(100.0, self.needs["love"] + 4)
        self._float_icon("heart")
        self._say(random.choice(("treat!", "nom!", "yum~")))
        self.play_snd(self.voice())
        self.set_state("treat", "munch", 1.6)   # NOT "munch" — that slams a need

    def st_treat(self, dt):
        if self.state_t >= self.plan_dur:
            self.set_state("groom", "groom", 1.5)

    def act_come(self):
        if not self._ensure_ground_state():
            return
        tx = min(max(float(self.cur[0]), self.wa[0] + 16), self.wa[2] - 16)
        self.walk_target = tx
        self.after_walk = None
        self.facing = 1 if tx > self.x else -1
        self.set_state("walk", "run", 30)

    def act_costume(self, key):
        if key not in COSTUMES or key == self.costume:
            return
        self.costume = key
        self._build_images()
        self._float_icon("heart")
        self._stash_save()

    def act_rename(self):
        self._open_name_dialog()

    def act_immortal(self):
        self.immortal = not self.immortal
        self._say("♾" if self.immortal else "⏳", dur=1.6)
        if self.stage == "passing":     # toggling on mid-goodbye revives to elder
            self.stage = "elder"
            self.scale = self._age_scale("elder")
            self._build_images()
            self.set_state("idle", "idle", 2)
        self._stash_save()

    def act_new_pet(self, species):
        if species not in SPECIES:
            return
        from tkinter import messagebox
        sp = SPECIES[species]["name"]
        try:
            ok = messagebox.askyesno(
                "New pet",
                f"Welcome a new baby {sp}?\n\n"
                f"Your current pet will move out to a lovely farm. 🌻",
                parent=self)
        except tk.TclError:
            ok = True
        if ok:
            self.begin_new_pet(species)

    def _open_name_dialog(self):
        if getattr(self, "_name_dlg", None) is not None:
            try:
                self._name_dlg.destroy()
            except tk.TclError:
                pass
            self._name_dlg = None
        dlg = tk.Toplevel(self)
        self._name_dlg = dlg
        dlg.title("Name your cat 🐈")
        dlg.transient(self)            # stay above the periodically re-lifted cat
        dlg.attributes("-topmost", True)
        dlg.resizable(False, False)
        dlg.configure(bg="#1c1c28")
        entries = {}

        def row(label, initial):
            f = tk.Frame(dlg, bg="#1c1c28")
            f.pack(fill="x", padx=14, pady=6)
            tk.Label(f, text=label, fg="#f4f4f8", bg="#1c1c28",
                     width=7, anchor="w", font=("Segoe UI", 10)).pack(side="left")
            e = tk.Entry(f, font=("Segoe UI", 11), width=16)
            e.pack(side="right")
            e.insert(0, initial)
            return e

        entries["cat"] = row("Cat:", self.name)
        if self.kitten is not None:
            entries["kitten"] = row("Kitten:", self.kitten.name)

        def close(*_):
            try:
                dlg.grab_release()
            except tk.TclError:
                pass
            dlg.destroy()
            self._name_dlg = None

        def ok(*_):
            self.name = entries["cat"].get().strip()[:16]
            if "kitten" in entries and self.kitten is not None:
                self.kitten.name = entries["kitten"].get().strip()[:16]
            self._stash_save()
            shown = self.name
            close()
            if shown:
                self._say(f"I'm {shown}!", dur=2.0)

        btns = tk.Frame(dlg, bg="#1c1c28")
        btns.pack(fill="x", padx=14, pady=(4, 12))
        tk.Button(btns, text="OK", command=ok, width=8).pack(side="right", padx=4)
        tk.Button(btns, text="Cancel", command=close, width=8).pack(side="right")
        dlg.bind("<Return>", ok)
        dlg.bind("<Escape>", close)
        dlg.protocol("WM_DELETE_WINDOW", close)
        entries["cat"].focus_set()
        entries["cat"].selection_range(0, "end")
        dlg.update_idletasks()
        dlg.geometry(f"+{int(min(self.cur[0], self.wa[2] - 240))}"
                     f"+{max(int(self.wa[1]) + 20, int(self.cur[1]) - 90)}")
        try:
            dlg.grab_set()
        except tk.TclError:
            pass

    def _rouse_for_play(self):
        """Wake her / get her off a perch so she notices the new toy."""
        if self.drag or self.state in ("jump", "fall", "dangle", "catch",
                                       "gotcha", "wallclimb", "madfall"):
            return
        if self.state in ("sleep", "perchsleep"):
            self.set_state("stretch", "stretch", 1.2)
        self.after_walk = None
        if self.perch is not None:
            self._hop_off_perch()
        elif self.surface_hwnd is not None:
            self.do_hop_down()

    def act_laser(self):
        if self.laser is not None:
            self.laser.destroy()
            self.laser = None
            if self.state == "laser":
                self.set_state("groom", "groom", 3)
            return
        if not self.can("laser"):
            return
        self.laser = Laser(self)
        self.laser_until = time.monotonic() + random.uniform(50, 90)
        self.play_snd("chirp")
        self._rouse_for_play()

    def act_toy(self):
        if self.toy is not None:
            self.toy.despawn()
            self.toy = None
            if self.state in ("toy_chase", "toy_bat"):
                self.set_state("idle", "idle", 2)
            return
        if not self.can("toy"):
            return
        cx, cy = self.cur
        x = min(max(cx, self.wa[0] + 30), self.wa[2] - 30)
        y = min(cy, self.ground() - 40)
        self.toy = Toy(self, x, y,
                       random.choice((-1, 1)) * random.uniform(180, 380),
                       -random.uniform(60, 200))
        self.behavior_cd["toy"] = 0.0
        self.play_snd("chirp")
        self._rouse_for_play()

    def act_trick(self):
        if self.state in ("jump", "fall", "dangle", "catch", "gotcha",
                          "wallclimb", "madfall") or self.drag:
            return
        if self.carrying:
            self._drop_gift()
        self.surface_hwnd = None   # flips dismount from window tops / boxes too
        self.surface_last = None
        self.perch = None
        self.after_walk = None
        self.do_flip()

    def _rescale_props(self):
        """Resize companions/furniture to match the cat's current scale."""
        if self.critter is not None and self.critter.alive:
            self.critter.rescale()
        if self.toy is not None:
            self.toy.rescale()
        if self.bird is not None and self.bird.alive:
            self.bird.rescale()
        for an in self.animals:
            if an.alive:
                an.rescale()
        for d in self.decor + self.messes:
            d.rescale()

    def act_resize(self, s):
        if s == self.base_scale:
            return
        self.base_scale = s                # user's Size tier
        self.scale = self._age_scale(self.stage)   # effective scale (age-adjusted)
        self._build_images()
        self._place()
        self._rescale_props()
        self._stash_save()

    def act_color(self, key):
        if key == self.persist.get("color"):
            return
        self.persist["color"] = key
        self._build_images()
        self._stash_save()

    def act_sounds(self):
        self.persist["sounds"] = not self.persist.get("sounds", True)
        if self.persist["sounds"]:
            play_sound("chirp")
        self._stash_save()

    def act_kitten(self):
        if self.kitten:
            self.kitten.destroy()
            self.kitten = None
            self._say("bye bye...")
        else:
            kc = self.persist.get("kitten_color") or (
                "ginger" if self.persist.get("color", "black") == "black" else "black")
            self.persist["kitten_color"] = kc
            self.kitten = Kitten(self, kc)
            self._float_icon("heart")
            self.play_snd("mew")
        self._stash_save()

    def act_add_decor(self, kind):
        if len(self.decor) >= 30:
            self._say("(no room!)")
            return
        x = min(max(float(self.cur[0]), self.wa[0] + 40), self.wa[2] - 40)
        try:
            self.decor.append(Decor(self, kind, x))
            self.behavior_cd["decor"] = min(self.behavior_cd["decor"], 4.0)
            self.play_snd("chirp")
            self._stash_save()
        except Exception as e:
            log_error(f"add_decor: {e!r}")

    def act_add_animal(self, species, gender=None):
        if len(self.animals) >= self.animal_cap:
            self._say("(flock is full!)")
            return
        cx = min(max(float(self.cur[0]), self.wa[0] + 40), self.wa[2] - 40)
        if self.spawn_animal(species, gender=gender, x=cx):
            self._float_icon("heart")
            self.play_snd("chirp")
            self._stash_save()

    def act_add_pair(self, species):
        cx = float(self.cur[0])
        a = self.spawn_animal(species, gender="m", x=cx - 40 * self.base_scale)
        b = self.spawn_animal(species, gender="f", x=cx + 40 * self.base_scale)
        if a or b:
            self._float_icon("heart")
            self.play_snd("chirp")
            self._stash_save()

    def act_add_random(self):
        self.act_add_animal(random.choice(list(SPECIES)))

    def clear_animals(self):
        for a in self.animals:
            a.destroy()
        self.animals = []
        self._stash_save()

    def animal_menu(self, animal, ev):
        m = tk.Menu(self, tearoff=0, font=("Segoe UI", 10))
        spn = SPECIES[animal.species]["name"]
        sex = "♀" if animal.gender == "f" else "♂"
        diet_icon = "🌿" if animal.diet == "herb" else "🥩"
        # ---- header: who is this? ----
        tags = []
        if animal.genes.get("ultra"):
            tags.append("✨ULTRA")
        elif animal.genes.get("shiny"):
            tags.append("✨shiny")
        if animal.genes.get("ability"):
            tags.append(animal.genes["ability"])
        if animal.genes.get("hybrid"):
            tags.append("hybrid")
        m.add_command(label=f"{sex}  {animal.name or spn}", state="disabled")
        sub = f"{diet_icon} {spn} · {animal.stage()}"
        if tags:
            sub += " · " + ", ".join(tags)
        m.add_command(label="   " + sub, state="disabled")
        hb = max(0, min(100, int(animal.hunger)))
        bar = "█" * (hb // 10) + "░" * (10 - hb // 10)
        m.add_command(label=f"   hunger {bar} {hb}%", state="disabled")
        m.add_separator()

        # ---- always-available care ----
        m.add_command(label="🫶  Pet", command=lambda: self._pet_animal(animal))
        m.add_command(label="🍖  Feed", command=lambda: self._feed_animal(animal))

        # ---- one diet-specific command (the headline per-breed action) ----
        if animal.diet == "herb":
            if self.has_food_for("herb"):
                m.add_command(label="🌿  Go graze",
                              command=lambda: self._urge_animal(animal, "graze"))
            else:
                m.add_command(label="🌿  Go graze  (grow some grass first)",
                              state="disabled")
        else:
            if self.has_food_for("carn", animal):
                m.add_command(label="🥩  Go hunt",
                              command=lambda: self._urge_animal(animal, "hunt"))
            else:
                m.add_command(label="🥩  Go hunt  (no prey around)",
                              state="disabled")

        # ---- breeding, only when this animal can actually do it ----
        if animal.gender == "f" and animal.is_adult():
            if animal.breed_cd > 0:
                m.add_command(label=f"💕  Find a mate  (resting {int(animal.breed_cd)}s)",
                              state="disabled")
            elif animal.hunger <= 60:
                m.add_command(label="💕  Find a mate  (too hungry — feed her first)",
                              state="disabled")
            elif len(self.animals) < self.animal_cap:
                m.add_command(label="💕  Find a mate",
                              command=lambda: self._urge_animal(animal, "mate"))

        # ---- generic "tell it to…" submenu keeps the top level tidy ----
        act = tk.Menu(m, tearoff=0)
        act.add_command(label="❗  Come here",
                        command=lambda: self._urge_animal(animal, "come"))
        act.add_command(label="🎾  Play",
                        command=lambda: self._urge_animal(animal, "play"))
        act.add_command(label="💤  Rest",
                        command=lambda: self._urge_animal(animal, "rest"))
        m.add_cascade(label="🐾  Tell it to…", menu=act)

        m.add_separator()
        m.add_command(label="✏  Rename…", command=lambda: self._rename_animal(animal))
        m.add_command(label="🗑  Release", command=lambda: self._release_animal(animal))
        try:
            m.tk_popup(ev.x_root, ev.y_root)
        finally:
            m.grab_release()

    def _pet_animal(self, animal):
        if animal in self.animals and animal.alive and not animal.dying:
            animal._heart()
            if animal.state not in ("dangle", "fall"):
                animal.set("look", "blink", 1.2)
            self.play_snd(animal.voice())

    def _feed_animal(self, animal):
        if animal in self.animals and animal.alive:
            animal.hunger = 100.0
            animal._heart()

    def _urge_animal(self, animal, urge, secs=14.0):
        if animal not in self.animals or not animal.alive or animal.dying:
            return
        if animal.state in ("dangle", "fall"):
            return
        animal.urge = urge
        animal.urge_t = secs
        icon = {"graze": "🌿", "hunt": "🥩", "mate": "💕",
                "come": "❗", "play": "🎾", "rest": "💤"}.get(urge, "✦")
        animal._fx(icon, -22, 1.0)
        animal.set("walk", "walk", secs)   # ensure the brain runs so the urge fires

    def _rename_animal(self, animal):
        if animal not in self.animals:
            return
        dlg = tk.Toplevel(self)
        dlg.title("Name this animal")
        dlg.transient(self)
        dlg.attributes("-topmost", True)
        dlg.resizable(False, False)
        dlg.configure(bg="#1c1c28")
        f = tk.Frame(dlg, bg="#1c1c28")
        f.pack(fill="x", padx=14, pady=10)
        tk.Label(f, text=SPECIES[animal.species]["name"] + ":", fg="#f4f4f8",
                 bg="#1c1c28", font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))
        e = tk.Entry(f, font=("Segoe UI", 11), width=16)
        e.pack(side="right")
        e.insert(0, animal.name)

        def close(*_):
            try:
                dlg.grab_release()
            except tk.TclError:
                pass
            dlg.destroy()

        def ok(*_):
            if animal in self.animals:
                animal.name = e.get().strip()[:16]
                self._stash_save()
            close()

        btns = tk.Frame(dlg, bg="#1c1c28")
        btns.pack(fill="x", padx=14, pady=(0, 12))
        tk.Button(btns, text="OK", command=ok, width=8).pack(side="right", padx=4)
        tk.Button(btns, text="Cancel", command=close, width=8).pack(side="right")
        dlg.bind("<Return>", ok)
        dlg.bind("<Escape>", close)
        dlg.protocol("WM_DELETE_WINDOW", close)
        e.focus_set()
        e.selection_range(0, "end")
        dlg.update_idletasks()
        dlg.geometry(f"+{int(min(self.cur[0], self.wa[2] - 240))}"
                     f"+{max(int(self.wa[1]) + 20, int(self.cur[1]) - 60)}")
        try:
            dlg.grab_set()
        except tk.TclError:
            pass

    def _release_animal(self, animal):
        if animal in self.animals:
            self.animals.remove(animal)
        animal.destroy()
        self._stash_save()

    def decor_menu(self, decor, ev):
        m = tk.Menu(self, tearoff=0, font=("Segoe UI", 10))
        m.add_command(label=DECOR_META[decor.kind]["label"]
                      + "   (drag to move)", state="disabled")
        m.add_separator()
        if decor.kind == "litter":
            dirty = "  (dirty!)" if decor.uses >= 6 else f"  ({decor.uses} used)"
            m.add_command(label="🧹  Scoop the litter" + dirty,
                          command=lambda: self.scoop_litter(decor))
        m.add_command(label="🗑  Remove this",
                      command=lambda: self.remove_decor(decor))
        m.add_command(label="🧹  Clear all furniture", command=self.clear_decor)
        try:
            m.tk_popup(ev.x_root, ev.y_root)
        finally:
            m.grab_release()

    def scoop_litter(self, decor):
        decor.uses = 0
        self._float_icon("heart")
        self._stash_save()

    def remove_decor(self, decor):
        if self.perch is decor:
            self.perch = None
            self.start_fall()
        if self.decor_target is decor:
            self.decor_target = None
        if decor in self.decor:
            self.decor.remove(decor)
        decor.destroy()
        self._stash_save()

    def clear_decor(self):
        if self.perch is not None:
            self.perch = None
            self.start_fall()
        self.decor_target = None
        for d in self.decor:
            d.destroy()
        self.decor = []
        self._stash_save()

    def st_eat(self, dt):
        if self.state_t >= self.plan_dur:
            self.needs["hunger"] = 100.0
            self.needs["love"] = min(100.0, self.needs["love"] + 2)
            self._float_icon("heart")
            self._say("nom nom~")
            self.set_state("groom", "groom", 3)

    def st_drink(self, dt):
        if self.state_t >= self.plan_dur:
            self.needs["thirst"] = 100.0
            self._float_icon("heart")
            self.set_state("idle", "idle", 3)

    def st_zoomies(self, dt):
        if self.walk_target is None:
            self.set_state("idle", "idle", 2)
            return
        delta = self.walk_target - self.x
        self.facing = 1 if delta > 0 else -1
        self.x += self.facing * min(abs(delta), 300 * self.scale / 3 * dt * 2.4)
        self._clamp_x()
        if abs(delta) < 8:
            self.zoom_passes -= 1
            if self.zoom_passes <= 0:
                self.needs["love"] = min(100.0, self.needs["love"] + 10)
                self._float_icon("heart")
                self._say("!!!")
                if self.zoom_flip:
                    self.zoom_flip = False
                    self.do_flip()
                else:
                    self.set_state("idle", "idle", 4)
            else:
                self.walk_target = (self.wa[0] + 60 if self.walk_target > (self.wa[0] + self.wa[2]) / 2
                                    else self.wa[2] - 60)
        if self.state_t > self.plan_dur:
            self.set_state("idle", "idle", 3)

    def st_dangle(self, dt):
        pass

    # ---- drawing -----------------------------------------------------------------------

    def _draw(self):
        # gait: a frog/bunny hops, a penguin waddles — but only on flat ground,
        # never while perched/climbing/airborne (would detach from the surface)
        anim = self.anim
        self._gait_dy = 0.0
        if (self.surface_hwnd is None and self.perch is None
                and self.anim in ("walk", "run")):
            gdy, anim2 = gait_render(self.species, self.anim, self.state_t,
                                     self.scale, True)
            self._gait_dy = gdy
            anim = anim2 or anim
        frames, fps, loop = ANIMS.get(anim, ANIMS["idle"])
        idx = int(self.state_t * fps)
        idx = idx % len(frames) if loop else min(idx, len(frames) - 1)
        img = self.images[(frames[idx], self.facing)]
        self.canvas.itemconfig(self.sprite_item, image=img)
        if self.carrying and self.mouth_item is not None:
            self.canvas.coords(self.mouth_item,
                               self.cw / 2 + self.facing * 9 * self.scale,
                               self.ch - 12 * self.scale)
            self.canvas.itemconfig(self.mouth_item, image=self.mouse_small[self.facing])
        # accessories track a standing head/body; hide them in poses where
        # that anchor would float (prone, head-down, spinning, rotated)
        hide = self.anim in _ACC_HIDE_ANIMS
        if self.acc_behind is not None:        # wings / spider legs behind body
            if hide:
                self.canvas.itemconfig(self.acc_behind, state="hidden")
            else:
                self.canvas.coords(self.acc_behind,
                                   self.cw / 2, self.ch - 12 * self.scale)
                self.canvas.itemconfig(self.acc_behind, state="normal",
                                       image=self.acc_img[("behind", self.facing)])
        if self.acc_front is not None:         # hat / horns on the head
            if hide:
                self.canvas.itemconfig(self.acc_front, state="hidden")
            else:
                self.canvas.coords(self.acc_front,
                                   self.cw / 2 + self.facing * 4 * self.scale,
                                   self.ch - 19 * self.scale)
                self.canvas.itemconfig(self.acc_front, state="normal",
                                       image=self.acc_img[("front", self.facing)])
        self._place()

    def show_bubble(self, icon, dur=2.2):
        self.clear_bubble()
        cx = self.cw / 2 + 13 * self.scale
        cy = self.ch - 26 * self.scale
        r = 7 * self.scale
        ids = [
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                    fill="#ffffff", outline="#16161e", width=2),
            self.canvas.create_oval(cx - r * 0.9, cy + r * 0.75, cx - r * 0.5, cy + r * 1.05,
                                    fill="#ffffff", outline="#16161e", width=1),
            self.canvas.create_image(cx, cy, image=self.icon_images[icon]),
        ]
        self.bubble = (ids, time.monotonic() + dur)

    def clear_bubble(self):
        if self.bubble:
            for i in self.bubble[0]:
                self.canvas.delete(i)
            self.bubble = None

    def _say(self, text, dur=1.8):
        # text over an opaque pill, so antialiased edges never blend
        # into the transparency key color (magenta fringing)
        tid = self.canvas.create_text(self.cw / 2 + 6 * self.scale, self.ch - 24 * self.scale,
                                      text=text, fill="#f4f4f8",
                                      font=("Segoe UI", 4 + int(2 * self.scale), "bold"))
        x0, y0, x1, y1 = self.canvas.bbox(tid)
        bg = self.canvas.create_rectangle(x0 - 3, y0 - 2, x1 + 3, y1 + 2,
                                          fill="#16161e", outline="#f4f4f8")
        self.canvas.tag_lower(bg, tid)
        self.effects.append({"id": bg, "t": dur, "vy": -6})
        self.effects.append({"id": tid, "t": dur, "vy": -6})

    def _float_icon(self, icon, dx=0.0, rise=26):
        iid = self.canvas.create_image(self.cw / 2 + dx, self.ch - 22 * self.scale,
                                       image=self.icon_images[icon])
        self.effects.append({"id": iid, "t": 1.4, "vy": -rise})

    def _spark(self):
        x = self.cw / 2 + random.uniform(-12, 12)
        y = self.ch - random.uniform(10, 20) * self.scale
        s = self.canvas.create_text(x, y, text="✦", fill="#ffd966",
                                    font=("Segoe UI", 3 + int(2 * self.scale)))
        self.effects.append({"id": s, "t": 0.5, "vy": -10})

    def _confetti(self):
        x = self.cw / 2 + random.uniform(-18, 18)
        y = self.ch - random.uniform(16, 30) * self.scale
        col = random.choice(("#ff5d76", "#ffd24a", "#62b8ff", "#5cc05a", "#f0a6c0"))
        c = self.canvas.create_text(x, y, text=random.choice(("✦", "•", "❜", "♥")),
                                    fill=col, font=("Segoe UI", 3 + int(2 * self.scale)))
        self.effects.append({"id": c, "t": random.uniform(0.8, 1.4),
                             "vy": -random.uniform(14, 34)})

    def _tick_effects(self, dt):
        if self.bubble and time.monotonic() > self.bubble[1]:
            self.clear_bubble()
        for fx in self.effects[:]:
            fx["t"] -= dt
            if fx["vy"]:
                self.canvas.move(fx["id"], 0, fx["vy"] * dt)
            if fx["t"] <= 0:
                self.canvas.delete(fx["id"])
                self.effects.remove(fx)

    # ---- shutdown -------------------------------------------------------------------------

    def quit_app(self):
        self._quitting = True
        try:
            self._stash_save()
        finally:
            self.destroy()


# ---------------------------------------------------------------------------
# Sprite sheet preview (dev helper, requires Pillow)
# ---------------------------------------------------------------------------

def render_sheet(path="sprite_sheet.png", px=5):
    from PIL import Image, ImageDraw

    sheet = {**FRAMES, **{"m_" + k: v for k, v in CRITTER_FRAMES.items()},
             **{"d_" + k: v for k, v in DECOR_ART.items()}}
    names = list(sheet)
    cols = 6
    rows_n = math.ceil(len(names) / cols)
    cell_w = max(len(f[0]) for f in sheet.values()) * px + 8
    cell_h = max(len(f) for f in sheet.values()) * px + 22
    img = Image.new("RGB", (cols * cell_w, rows_n * cell_h), "#6a8aa8")
    d = ImageDraw.Draw(img)
    for i, name in enumerate(names):
        ox = (i % cols) * cell_w + 4
        oy = (i // cols) * cell_h + 18
        d.text((ox, oy - 15), name, fill="white")
        for r, row in enumerate(sheet[name]):
            for c, ch in enumerate(row):
                if ch != ".":
                    d.rectangle([ox + c * px, oy + r * px,
                                 ox + c * px + px - 1, oy + r * px + px - 1],
                                fill=PAL[ch])
    img.save(path)
    print(f"wrote {path}")


# ---------------------------------------------------------------------------

def main():
    if "--sheet" in sys.argv:
        render_sheet()
        return
    if acquire_single_instance() is None:
        ctypes.windll.user32.MessageBoxW(0, "vCat is already running! 🐈‍⬛",
                                         "vCat", 0x40)
        return
    set_dpi_aware()
    state = load_state()
    try:
        app = VCat(state)
        app.mainloop()
    except Exception as e:
        log_error(f"fatal: {e!r}")
        ctypes.windll.user32.MessageBoxW(
            0, f"vCat had to go home early :(\n\n{e!r}\n\nDetails: {LOG_PATH}",
            "vCat", 0x10)


if __name__ == "__main__":
    main()
