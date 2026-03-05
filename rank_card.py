"""
rank_card.py — Pillow-based rank card image generator.

Downloads TTF fonts on first use from Google Fonts (cached locally).
Falls back to PIL default font if download fails.
"""

import io
import os
import math
import logging
import asyncio
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger(__name__)

# ── Font paths ────────────────────────────────────────────────────────────────
FONT_DIR = Path(__file__).parent / "assets" / "fonts"
FONT_DIR.mkdir(parents=True, exist_ok=True)

FONT_URLS: dict[str, str] = {
    "Avenger":  "https://github.com/google/fonts/raw/main/ofl/bebasneue/BebasNeue-Regular.ttf",
    "Disney":   "https://github.com/google/fonts/raw/main/ofl/pacifico/Pacifico-Regular.ttf",
    "Chalice":  "https://github.com/google/fonts/raw/main/ofl/cinzeldecorative/CinzelDecorative-Regular.ttf",
    "Vampire":  "https://github.com/google/fonts/raw/main/ofl/unifrakturmaguntia/UnifrakturMaguntia-Book.ttf",
    "Vogue":    "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay-Bold.ttf",
    "Halo":     "https://github.com/google/fonts/raw/main/ofl/orbitron/Orbitron-Bold.ttf",
    "OldLondon":"https://github.com/google/fonts/raw/main/ofl/imfellenglish/IMFellEnglish-Regular.ttf",
    # mono for stats body text
    "_Mono":    "https://github.com/google/fonts/raw/main/apache/robotomono/RobotoMono-Bold.ttf",
    "_MonoReg": "https://github.com/google/fonts/raw/main/apache/robotomono/RobotoMono-Regular.ttf",
}

# map display name → internal key (for lookup)
FONT_DISPLAY_NAMES = ["Avenger", "Disney", "Chalice", "Vampire", "Vogue", "Halo", "OldLondon"]


def _try_download_font(name: str) -> Path | None:
    url = FONT_URLS.get(name)
    if not url:
        return None
    dest = FONT_DIR / f"{name}.ttf"
    if dest.exists():
        return dest
    try:
        logger.info(f"Downloading font {name}...")
        urllib.request.urlretrieve(url, dest)
        return dest
    except Exception as e:
        logger.warning(f"Could not download font {name}: {e}")
        return None


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = _try_download_font(name)
    if path and path.exists():
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            pass
    return ImageFont.load_default()


def _load_mono(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    key = "_Mono" if bold else "_MonoReg"
    return _load_font(key, size)


# pre-download fonts in background at startup
def prefetch_fonts():
    for name in list(FONT_URLS.keys()):
        _try_download_font(name)


# ── Colour themes ─────────────────────────────────────────────────────────────
# Each theme: bg_top, bg_bot, accent, bar_fill, bar_bg, text_primary, text_secondary, ring_color
THEMES: dict[str, dict] = {
    "matrix": {
        "bg_top":    (5,  12,  5),
        "bg_bot":    (0,   0,  0),
        "accent":    (0, 255, 70),
        "bar_fill":  (0, 220, 60),
        "bar_bg":    (15, 40, 15),
        "text_pri":  (200, 255, 200),
        "text_sec":  (100, 200, 100),
        "ring":      (0, 255, 70),
        "label":     "☠ MATRIX",
    },
    "cyberpunk": {
        "bg_top":    (10,  5, 25),
        "bg_bot":    (0,   0,  0),
        "accent":    (255, 0, 200),
        "bar_fill":  (190, 0, 255),
        "bar_bg":    (40,  5, 60),
        "text_pri":  (255, 200, 255),
        "text_sec":  (200, 100, 255),
        "ring":      (255, 0, 200),
        "label":     "⚡ CYBERPUNK",
    },
    "vampire": {
        "bg_top":    (20,  0,  0),
        "bg_bot":    (5,   0,  0),
        "accent":    (200, 0, 30),
        "bar_fill":  (180, 0, 20),
        "bar_bg":    (50, 10, 10),
        "text_pri":  (255, 200, 200),
        "text_sec":  (200, 100, 100),
        "ring":      (200, 0, 30),
        "label":     "🩸 VAMPIRE",
    },
    "ghost": {
        "bg_top":    (15, 15, 20),
        "bg_bot":    (5,   5, 10),
        "accent":    (180, 180, 255),
        "bar_fill":  (140, 140, 255),
        "bar_bg":    (30,  30, 60),
        "text_pri":  (220, 220, 255),
        "text_sec":  (150, 150, 200),
        "ring":      (160, 160, 255),
        "label":     "👻 GHOST",
    },
    "obsidian": {
        "bg_top":    (10, 10, 10),
        "bg_bot":    (0,   0,  0),
        "accent":    (255, 215, 0),
        "bar_fill":  (220, 180, 0),
        "bar_bg":    (40,  35,  5),
        "text_pri":  (255, 230, 150),
        "text_sec":  (200, 170, 80),
        "ring":      (255, 215, 0),
        "label":     "⚫ OBSIDIAN",
    },
    "aurora": {
        "bg_top":    (0,  15, 25),
        "bg_bot":    (0,   5, 10),
        "accent":    (0, 235, 200),
        "bar_fill":  (0, 200, 170),
        "bar_bg":    (0,  40, 40),
        "text_pri":  (180, 255, 240),
        "text_sec":  (80, 200, 180),
        "ring":      (0, 220, 190),
        "label":     "🌌 AURORA",
    },
    "crimson": {
        "bg_top":    (20,  0, 10),
        "bg_bot":    (5,   0,  5),
        "accent":    (255, 50, 100),
        "bar_fill":  (220, 30, 80),
        "bar_bg":    (60, 10, 30),
        "text_pri":  (255, 180, 200),
        "text_sec":  (200, 100, 140),
        "ring":      (255, 50, 100),
        "label":     "💀 CRIMSON",
    },
    "void": {
        "bg_top":    (5,   0, 15),
        "bg_bot":    (0,   0,  5),
        "accent":    (130, 0, 255),
        "bar_fill":  (110, 0, 220),
        "bar_bg":    (25,  0, 50),
        "text_pri":  (210, 180, 255),
        "text_sec":  (150, 100, 220),
        "ring":      (130, 0, 255),
        "label":     "🕳 VOID",
    },
}

THEME_NAMES = list(THEMES.keys())

# ── Card renderer ─────────────────────────────────────────────────────────────
W, H = 900, 280
AVATAR_SIZE = 180
AVATAR_X, AVATAR_Y = 30, (H - AVATAR_SIZE) // 2    # left-center
STATS_X = AVATAR_X + AVATAR_SIZE + 30              # right of avatar


def _circle_crop(img: Image.Image, size: int) -> Image.Image:
    img = img.resize((size, size), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img


def _draw_bg(draw: ImageDraw.ImageDraw, theme: dict):
    """Vertical gradient + subtle scanlines."""
    t, b = theme["bg_top"], theme["bg_bot"]
    for y in range(H):
        r = t[0] + (b[0] - t[0]) * y // H
        g = t[1] + (b[1] - t[1]) * y // H
        bl = t[2] + (b[2] - t[2]) * y // H
        draw.line([(0, y), (W, y)], fill=(r, g, bl))

    # Scanlines
    acc = theme["accent"]
    for y in range(0, H, 6):
        draw.line([(0, y), (W, y)], fill=(acc[0]//20, acc[1]//20, acc[2]//20))

    # Diagonal accent band (top-right corner)
    pts = [(W - 220, 0), (W, 0), (W, 220)]
    draw.polygon(pts, fill=(acc[0]//8, acc[1]//8, acc[2]//8))

    # Corner neon frame
    lw = 2
    draw.rectangle([lw, lw, W - lw - 1, H - lw - 1], outline=theme["accent"], width=lw)


def _draw_avatar(card: Image.Image, avatar_bytes: bytes | None, ring_color: tuple, size: int):
    # Ring
    ring_img = Image.new("RGBA", (size + 8, size + 8), (0, 0, 0, 0))
    ImageDraw.Draw(ring_img).ellipse((0, 0, size + 7, size + 7), outline=ring_color + (255,), width=4)
    card.paste(ring_img, (AVATAR_X - 4, AVATAR_Y - 4), ring_img)

    if avatar_bytes:
        try:
            av = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            av = _circle_crop(av, size)
            card.paste(av, (AVATAR_X, AVATAR_Y), av)
            return
        except Exception:
            pass

    # Fallback gray circle
    fb = Image.new("RGBA", (size, size), (60, 60, 60, 255))
    fb = _circle_crop(fb, size)
    card.paste(fb, (AVATAR_X, AVATAR_Y), fb)


def build_rank_card(
    username:      str,
    level:         int,
    server_rank:   int,
    balance:       int,
    total_xp:      int,
    progress_xp:   int,
    needed_xp:     int,
    bar_pct:       float,       # 0-100
    avatar_bytes:  bytes | None,
    font_name:     str = "Halo",
    theme_name:    str = "matrix",
) -> io.BytesIO:
    theme = THEMES.get(theme_name, THEMES["matrix"])
    card  = Image.new("RGB", (W, H), theme["bg_bot"])
    draw  = ImageDraw.Draw(card)

    _draw_bg(draw, theme)
    _draw_avatar(card, avatar_bytes, theme["ring"], AVATAR_SIZE)

    # ── fonts ─────────────────────────────────────────────────────────────────
    f_name   = _load_font(font_name, 36)   # username
    f_stat   = _load_mono(22)              # stat labels
    f_stat_v = _load_mono(22, bold=False)  # stat values (slightly lighter)
    f_level  = _load_mono(52)             # big level number
    f_star   = _load_mono(40)             # ★ glyph
    f_label  = _load_mono(13)             # theme label watermark

    acc = theme["accent"]
    pri = theme["text_pri"]
    sec = theme["text_sec"]

    # ── ★ LEVEL (top-right) ───────────────────────────────────────────────────
    level_str = str(level)
    star_str  = "★"
    star_w    = draw.textlength(star_str, font=f_star)
    lvl_w     = draw.textlength(level_str, font=f_level)
    total_w   = int(star_w + 8 + lvl_w)
    sx = W - total_w - 18
    sy = 12
    draw.text((sx, sy),            star_str,  font=f_star,  fill=acc)
    draw.text((sx + star_w + 8, sy + 4), level_str, font=f_level, fill=acc)

    # ── USERNAME ──────────────────────────────────────────────────────────────
    uy = 22
    # Glow: draw slightly blurred version behind (simulate)
    draw.text((STATS_X, uy), username.upper(), font=f_name, fill=(acc[0]//3, acc[1]//3, acc[2]//3))
    draw.text((STATS_X - 1, uy - 1), username.upper(), font=f_name, fill=pri)

    # ── STAT ROWS ─────────────────────────────────────────────────────────────
    row1_y = uy + 56
    row2_y = row1_y + 36
    row3_y = row2_y + 36

    # Row 1: RANK #N
    draw.text((STATS_X, row1_y), "RANK", font=f_stat, fill=sec)
    draw.text((STATS_X + 80, row1_y), f"#{server_rank:,}", font=f_stat_v, fill=acc)

    # Row 2: BALANCE  N 💎
    bal_str = f"{balance:,} 💎"
    draw.text((STATS_X, row2_y), "BALANCE", font=f_stat, fill=sec)
    draw.text((STATS_X + 120, row2_y), bal_str, font=f_stat_v, fill=pri)

    # Row 3: EXP  progress/needed  (total TOTAL)
    exp_str = f"{int(progress_xp):,} / {int(needed_xp):,}   ({total_xp:,} TOTAL)"
    draw.text((STATS_X, row3_y), "EXP", font=f_stat, fill=sec)
    draw.text((STATS_X + 60, row3_y), exp_str, font=f_stat_v, fill=pri)

    # ── XP PROGRESS BAR ───────────────────────────────────────────────────────
    bar_y = H - 50
    bar_x0, bar_x1 = STATS_X, W - 20
    bar_h = 18
    bar_r = bar_h // 2   # corner radius

    # trough
    draw.rounded_rectangle([bar_x0, bar_y, bar_x1, bar_y + bar_h],
                            radius=bar_r, fill=theme["bar_bg"], outline=acc, width=1)
    # fill
    fill_w = int((bar_pct / 100) * (bar_x1 - bar_x0))
    if fill_w > bar_r * 2:
        draw.rounded_rectangle([bar_x0, bar_y, bar_x0 + fill_w, bar_y + bar_h],
                                radius=bar_r, fill=theme["bar_fill"])

    # percentage label inside bar
    pct_str = f"{bar_pct:.1f}%"
    f_pct = _load_mono(13)
    pw = draw.textlength(pct_str, font=f_pct)
    px = bar_x0 + (bar_x1 - bar_x0) // 2 - int(pw) // 2
    luma_fill = 0.299*theme["bar_fill"][0] + 0.587*theme["bar_fill"][1] + 0.114*theme["bar_fill"][2]
    pct_color = (10, 10, 10) if luma_fill > 140 else (220, 220, 220)
    draw.text((px, bar_y + 2), pct_str, font=f_pct, fill=pct_color)

    # ── theme watermark (bottom-left, faint) ─────────────────────────────────
    draw.text((AVATAR_X, H - 18), theme.get("label", ""), font=f_label,
              fill=(acc[0]//4, acc[1]//4, acc[2]//4))

    buf = io.BytesIO()
    card.save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf
