#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""元サイト(asahiroumu-sr.jp 当社制作)の写真をWeb最適化して assets/img/ に配置。
   JPEG(品質82・幅上限)＋WebP(品質80)を生成。"""
from PIL import Image
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src/assets/img/source"
OUT = ROOT / "src/assets/img"

# (元ファイル, 出力名, 最大幅)
JOBS = [
    ("img_mv01-pc.jpg", "hero-building", 1920),
    ("img_mv02-pc.jpg", "handshake", 1280),
    ("img_mv03-pc.jpg", "meeting", 1280),
    ("img_profile.jpg", "rep-yasuda", 900),
]

def save(im, out_base):
    # JPEG
    jp = OUT / (out_base + ".jpg")
    im.convert("RGB").save(jp, "JPEG", quality=82, optimize=True, progressive=True)
    # WebP
    wp = OUT / (out_base + ".webp")
    im.convert("RGB").save(wp, "WEBP", quality=80, method=6)
    return jp.stat().st_size, wp.stat().st_size

for src, base, maxw in JOBS:
    p = SRC / src
    im = Image.open(p)
    w, h = im.size
    if w > maxw:
        im = im.resize((maxw, round(h * maxw / w)), Image.LANCZOS)
    js, ws = save(im, base)
    print("%-14s %dx%d -> jpg %dKB / webp %dKB" % (base, im.size[0], im.size[1], js // 1024, ws // 1024))
print("done")
