#!/usr/bin/env python3
"""AON Style gallery images for Devpost: gradient band with chip + headline + one-liner, screenshot card below.

Adapted from the global note "AON Style 商店截圖" for landscape web screenshots: output is 3:2 (Devpost gallery),
the card shows the part of the screenshot that starts at `offset` (source pixels).
Usage: python3 scripts/aon_style_shots.py   ->  docs/screenshots/gallery/*.png
"""
import glob
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.join(os.path.dirname(__file__), '..', 'docs', 'screenshots')
OUT = os.path.join(ROOT, 'gallery')
W, H = 1620, 1080  # 3:2
BAND = 0.30

_PF = glob.glob('/System/Library/AssetsV2/com_apple_MobileAsset_Font*/*/AssetData/PingFang.ttc')
_FALLBACK = '/Library/Fonts/Arial Unicode.ttf'


def font(size, weight='semibold'):
    if _PF:
        return ImageFont.truetype(_PF[0], size, index={'regular': 2, 'medium': 6, 'semibold': 10}[weight])
    return ImageFont.truetype(_FALLBACK, size)


# output name: (source, colors, chip, headline, one-liner, source y offset)
SHOTS = {
    '1-agent': ('04_agent_compare.png', ('#0FB39A', '#22C7D6'), 'Qloo-grounded agent',
                'Same agent, with and without Qloo.\nWith Qloo it wins 17 of 20 runs.',
                'Every product decision cites Qloo films, audience age and taste tags', 820),
    '2-culture': ('01_culture_comparison.png', ('#6C4CF5', '#9B6BFF'), 'Culture comparison',
                  'Same crowd size, same budget.\nDifferent culture, different stock.',
                  "Live Qloo recommendations for each event's audience", 0),
    '3-plans': ('02_plans_what_if.png', ('#2F6BFF', '#4FA3FF'), 'Plans & what-if',
                'Three risk plans.\nWhat-if scenarios in one click.',
                'Rain, attendance, cost, rival stalls, supplier MOQ', 0),
    '4-ops': ('03_live_ops.png', ('#F59E0B', '#FF6B3D'), 'Live ops',
              'Restock mid-event\nfrom sales so far.',
              'Simulated sales, calibration and multi-day restock', 0),
}


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def gradient(w, h, c1, c2):
    a, b = hex_rgb(c1), hex_rgb(c2)
    g = Image.new('RGB', (w, h))
    px = ImageDraw.Draw(g)
    for y in range(h):
        t = y / max(h - 1, 1)
        px.line([(0, y), (w, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)))
    return g


def decorate(img, w, h, base):
    ov = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    r = int(base * 0.42)
    d.ellipse([w - r * 1.3, -r * 0.7, w + r * 0.7, r * 1.3], fill=(255, 255, 255, 34))
    r2 = int(base * 0.18)
    d.ellipse([-r2 * 0.6, h * BAND * 0.62, r2 * 1.4, h * BAND * 0.62 + r2 * 2], fill=(255, 255, 255, 26))
    img.alpha_composite(ov)


def compose(key):
    src, (c1, c2), chip, title, sub, offset = SHOTS[key]
    shot = Image.open(os.path.join(ROOT, src)).convert('RGBA')
    base = min(W, int(H * 0.6))
    img = gradient(W, H, c1, c2).convert('RGBA')
    decorate(img, W, H, base)

    d = ImageDraw.Draw(img)
    x, y = int(W * 0.07), int(H * BAND * 0.14)
    f_chip = font(int(base * 0.036))
    ph, pv = int(base * 0.028), int(base * 0.014)
    ch = int(base * 0.036) + pv * 2
    d.rounded_rectangle([x, y, x + d.textlength(chip, font=f_chip) + ph * 2, y + ch], radius=ch // 2, fill='white')
    d.text((x + ph, y + ch // 2), chip, font=f_chip, fill=c1, anchor='lm')
    y += ch + int(base * 0.03)
    f_title = font(int(base * 0.074))
    d.multiline_text((x, y), title, font=f_title, fill='white', spacing=int(base * 0.014))
    y = d.multiline_textbbox((x, y), title, font=f_title, spacing=int(base * 0.014))[3] + int(base * 0.024)
    d.text((x, y), sub, font=font(int(base * 0.038), 'medium'), fill=(255, 255, 255, 235))

    # card: 86% wide, starts below the band, runs off the bottom edge
    cw = int(W * 0.86)
    scale = cw / shot.width
    s = shot.resize((cw, int(shot.height * scale)), Image.LANCZOS)
    top = int(H * BAND) + int(base * 0.02)
    s = s.crop((0, int(offset * scale), cw, min(s.height, int(offset * scale) + H - top)))
    left, rad = (W - cw) // 2, int(base * 0.04)
    mask = Image.new('L', s.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s.width, s.height + rad], radius=rad, fill=255)
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([left, top + rad // 3, left + cw, H + rad], radius=rad, fill=(0, 0, 0, 70))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(base * 0.025)))
    border = int(base * 0.012)
    ImageDraw.Draw(img).rounded_rectangle([left - border, top - border, left + cw + border, H + rad],
                                          radius=rad + border, fill=(255, 255, 255, 110))
    img.paste(s, (left, top), mask)

    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, key + '.png')
    img.convert('RGB').save(out, optimize=True)
    return out


if __name__ == '__main__':
    for k in SHOTS:
        print(compose(k))
