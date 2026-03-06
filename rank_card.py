"""
rank_card.py — Pillow-based rank card image generator.

Downloads TTF fonts on first use from Google Fonts (cached locally).
Falls back to PIL default font if download fails.
"""

import io
import logging
import urllib.request
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ── Font paths ────────────────────────────────────────────────────────────────
FONT_DIR = Path(__file__).parent / "assets" / "fonts"
FONT_DIR.mkdir(parents=True, exist_ok=True)

FONT_URLS: dict[str, str] = {
    # User-selectable display fonts
    "Avenger":  "https://github.com/google/fonts/raw/main/ofl/bebasneue/BebasNeue-Regular.ttf",
    "Disney":   "https://github.com/google/fonts/raw/main/ofl/pacifico/Pacifico-Regular.ttf",
    "Chalice":  "https://github.com/google/fonts/raw/main/ofl/cinzeldecorative/CinzelDecorative-Regular.ttf",
    "Truckin":  "https://github.com/google/fonts/raw/main/ofl/blackopsone/BlackOpsOne-Regular.ttf",
    "StarWars": "https://github.com/google/fonts/raw/main/ofl/audiowide/Audiowide-Regular.ttf",
    "Pokemon":  "https://github.com/google/fonts/raw/main/ofl/titanone/TitanOne-Regular.ttf",
    # Mono for numbers / bar %
    "_Mono":    "https://github.com/google/fonts/raw/main/apache/robotomono/static/RobotoMono-Bold.ttf",
    "_MonoReg": "https://github.com/google/fonts/raw/main/apache/robotomono/static/RobotoMono-Regular.ttf",
}

FONT_DISPLAY_NAMES = ["Avenger", "Disney", "Chalice", "Truckin", "StarWars", "Pokemon"]


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
    return _load_font("_Mono" if bold else "_MonoReg", size)


def prefetch_fonts():
    """Pre-download all fonts in background at startup."""
    for name in list(FONT_URLS.keys()):
        _try_download_font(name)


# ── Colour themes ─────────────────────────────────────────────────────────────
THEMES: dict[str, dict] = {
    "matrix": {
        "bg_top":   (0,  20,  0), "bg_bot":   (0,   0,  0),
        "accent":   (0, 255, 100), "bar_fill": (0, 255, 70),
        "bar_bg":   (0,  50, 20), "text_pri": (200, 255, 200),
        "text_sec": (100, 255, 150), "ring":   (0, 255, 100),
        "label":    "☠ MATRIX",
    },
    "cyberpunk": {
        "bg_top":   (20, 0, 40), "bg_bot":   (0,   0,  0),
        "accent":   (0, 255, 255), "bar_fill": (255, 0, 255),
        "bar_bg":   (60, 0, 80), "text_pri": (255, 255, 255),
        "text_sec": (200, 100, 255), "ring":   (0, 255, 255),
        "label":    "⚡ CYBERPUNK",
    },
    "vampire": {
        "bg_top":   (40,  0,  0), "bg_bot":   (0,   0,  0),
        "accent":   (255, 0, 50), "bar_fill": (220, 0, 30),
        "bar_bg":   (80,  0,  0), "text_pri": (255, 255, 255),
        "text_sec": (255, 100, 100), "ring":   (255, 0, 50),
        "label":    "🩸 VAMPIRE",
    },
    "ghost": {
        "bg_top":   (30, 30, 50), "bg_bot":   (0,   0,  0),
        "accent":   (0, 200, 255), "bar_fill": (150, 150, 255),
        "bar_bg":   (40, 40, 80), "text_pri": (255, 255, 255),
        "text_sec": (200, 200, 255), "ring":   (0, 200, 255),
        "label":    "👻 GHOST",
    },
    "obsidian": {
        "bg_top":   (30, 25,  0), "bg_bot":   (0,   0,  0),
        "accent":   (255, 180, 0), "bar_fill": (255, 215, 0),
        "bar_bg":   (60, 45,  0), "text_pri": (255, 255, 255),
        "text_sec": (255, 200, 50), "ring":   (255, 180, 0),
        "label":    "⚫ OBSIDIAN",
    },
    "aurora": {
        "bg_top":   (0, 40, 60), "bg_bot":   (0,   0,  0),
        "accent":   (0, 255, 150), "bar_fill": (0, 255, 200),
        "bar_bg":   (0, 60, 80), "text_pri": (255, 255, 255),
        "text_sec": (150, 255, 200), "ring":   (0, 255, 150),
        "label":    "🌌 AURORA",
    },
    "crimson": {
        "bg_top":   (50, 0, 20), "bg_bot":   (0,   0,  0),
        "accent":   (255, 0, 100), "bar_fill": (255, 50, 150),
        "bar_bg":   (100, 0, 50), "text_pri": (255, 255, 255),
        "text_sec": (255, 150, 200), "ring":   (255, 0, 100),
        "label":    "💀 CRIMSON",
    },
    "void": {
        "bg_top":   (10, 0, 30), "bg_bot":   (0,   0,  0),
        "accent":   (180, 0, 255), "bar_fill": (150, 0, 255),
        "bar_bg":   (50, 0, 100), "text_pri": (255, 255, 255),
        "text_sec": (200, 150, 255), "ring":   (180, 0, 255),
        "label":    "🕳 VOID",
    },
}

THEME_NAMES = list(THEMES.keys())

# ── Card dimensions ───────────────────────────────────────────────────────────
W, H         = 900, 300
AVATAR_SIZE  = 200
AVATAR_X     = 25
AVATAR_Y     = (H - AVATAR_SIZE) // 2   # vertically centered
STATS_X      = AVATAR_X + AVATAR_SIZE + 28   # left edge of text area
COL2_X       = STATS_X + 330                 # second column of 2x2 grid — slightly widened from 300


# ── Helpers ───────────────────────────────────────────────────────────────────
def _circle_crop(img: Image.Image, size: int) -> Image.Image:
    img = img.resize((size, size), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img


def _draw_bg(draw: ImageDraw.ImageDraw, theme: dict):
    # Base Gradient
    t, b = theme["bg_top"], theme["bg_bot"]
    for y in range(H):
        r  = t[0] + (b[0] - t[0]) * y // H
        g  = t[1] + (b[1] - t[1]) * y // H
        bl = t[2] + (b[2] - t[2]) * y // H
        draw.line([(0, y), (W, y)], fill=(r, g, bl))

    acc = theme["accent"]
    
    # ── SUBTLE NOISE / GRIT ──
    import random
    for _ in range(2500):
        nx, ny = random.randint(0, W-1), random.randint(0, H-1)
        val = random.randint(5, 15)
        draw.point((nx, ny), fill=(acc[0]//val, acc[1]//val, acc[2]//val, 100))

    # ── SCANLINES ──
    for y in range(0, H, 6):
        draw.line([(0, y), (W, y)], fill=(acc[0]//25, acc[1]//25, acc[2]//25))

    # ── CYBER CIRCUIT LINES ──
    # Random tech lines for "esoteric/cyber" look
    for i in range(3):
        lx = random.randint(200, W-100)
        draw.line([(lx, 0), (lx + 40, 40)], fill=(acc[0]//10, acc[1]//10, acc[2]//10), width=1)
        draw.line([(lx + 40, 40), (W, 40)], fill=(acc[0]//10, acc[1]//10, acc[2]//10), width=1)

    # ── CORNER GLOW / FLARE (Top Right) ──
    # Multi-layered polygon for "glow" effect
    for i in range(10, 1, -1):
        alpha_div = i * 2
        draw.polygon([(W - (80*i), 0), (W, 0), (W, 80*i)],
                     fill=(acc[0]//alpha_div, acc[1]//alpha_div, acc[2]//alpha_div))

    # ── NEON BORDER ──
    draw.rectangle([2, 2, W - 3, H - 3], outline=acc, width=2)


def _draw_avatar(card: Image.Image, avatar_bytes: bytes | None, ring_color: tuple, size: int):
    ring_img = Image.new("RGBA", (size + 8, size + 8), (0, 0, 0, 0))
    ImageDraw.Draw(ring_img).ellipse((0, 0, size + 7, size + 7),
                                     outline=ring_color + (255,), width=4)
    card.paste(ring_img, (AVATAR_X - 4, AVATAR_Y - 4), ring_img)

    if avatar_bytes:
        try:
            av = Image.open(__import__("io").BytesIO(avatar_bytes)).convert("RGBA")
            av = _circle_crop(av, size)
            card.paste(av, (AVATAR_X, AVATAR_Y), av)
            return
        except Exception:
            pass

    fb = Image.new("RGBA", (size, size), (60, 60, 60, 255))
    card.paste(_circle_crop(fb, size), (AVATAR_X, AVATAR_Y), _circle_crop(fb, size))


# ── Main renderer ─────────────────────────────────────────────────────────────
def build_rank_card(
    username:     str,
    level:        int,
    server_rank:  int,
    balance:      int,
    total_xp:     int,
    progress_xp:  int,
    needed_xp:    int,
    bar_pct:      float,        # 0-100
    avatar_bytes: bytes | None,
    font_name:    str = "Avenger",
    theme_name:   str = "vampire",
    member_days:  int = 0,
    avg_xp:       int = 20,
) -> io.BytesIO:
    theme = THEMES.get(theme_name, THEMES["matrix"])
    card  = Image.new("RGB", (W, H), theme["bg_bot"])
    draw  = ImageDraw.Draw(card)

    _draw_bg(draw, theme)
    _draw_avatar(card, avatar_bytes, theme["ring"], AVATAR_SIZE)

    acc = theme["accent"]
    pri = theme["text_pri"]
    sec = theme["text_sec"]

    # ── Load fonts ────────────────────────────────────────────────────────────
    # Custom font: username + all stat labels + all stat values
    f_user  = _load_font(font_name, 46)   # username
    f_label = _load_font(font_name, 13)   # stat labels (down 8px from 21)
    f_val   = _load_font(font_name, 25)   # stat values (down 8px from 33)
    f_level = _load_font(font_name, 46)   # level
    
    # Mono for persistent UI elements (star is being replaced)
    f_pct   = _load_font("Avenger", 26)   # increased to 26px for better visibility
    f_mono  = _load_mono(21)             # for lower-case suffix/emoji fallback
    f_wmark = _load_mono(13)             # theme watermark

    # ── LEVEL CIRCLE ── top-right
    lvl_str = str(level)
    circ_size = 95   # Enlarge slightly (was 80)
    cx, cy = W - circ_size - 25, 20
    # draw circle
    draw.ellipse([cx, cy, cx+circ_size, cy+circ_size], outline=acc, width=3)
    # text centering
    l_w = draw.textlength(lvl_str, font=f_level)
    tx = cx + (circ_size - l_w) // 2
    ty = cy + (circ_size - 46) // 2 - 4
    draw.text((tx, ty), lvl_str, font=f_level, fill=pri)
    # Small "LVL" tag
    f_tiny = _load_mono(10)
    draw.text((cx + (circ_size - 20)//2, cy + 12), "LVL", font=f_tiny, fill=sec)

    # ── USERNAME ──────────────────────────────────────────────────────────────
    uy = 20
    # Truncate to 17 characters
    display_name = username
    if len(display_name) > 17:
        display_name = display_name[:14] + "..."
    
    # shadow
    draw.text((STATS_X + 2, uy + 2), display_name.upper(), font=f_user,
              fill=(acc[0]//5, acc[1]//5, acc[2]//5))
    draw.text((STATS_X, uy), display_name.upper(), font=f_user, fill=pri)

    # ── 2 × 2 STAT GRID ──────────────────────────────────────────────────────
    LABEL_Y1, LABEL_Y2 = 105, 165  # Tighter row gap

    cells = [
        # (col_x, label_y,  label_text,              value_text)
        (STATS_X, LABEL_Y1, "RANK",    f"#{server_rank:,}"),
        (COL2_X,  LABEL_Y1, "BALANCE", f"{balance:,}"),
        (STATS_X, LABEL_Y2, "EXP",     f"{int(progress_xp)}/{int(needed_xp)}"),
        (COL2_X,  LABEL_Y2, "MEMBER",  f"{member_days:,}d"),
    ]

    for col_x, lbl_y, label, value in cells:
        draw.text((col_x, lbl_y), label, font=f_label, fill=sec)
        lbl_w = draw.textlength(label, font=f_label)
        
        # Stat value placement (smaller fonts need less offset)
        val_x = col_x + lbl_w + 12
        val_y = lbl_y - 8
        draw.text((val_x, val_y), value, font=f_val, fill=pri)

    # ── XP PROGRESS BAR ───────────────────────────────────────────────────────
    bar_h  = 52   # thickened by 50% from 35
    bar_y  = H - 70
    bar_x0, bar_x1 = STATS_X, W - 20
    bar_r  = 16

    draw.rounded_rectangle([bar_x0, bar_y, bar_x1, bar_y + bar_h],
                            radius=bar_r, fill=theme["bar_bg"], outline=acc, width=1)
    
    bar_width = bar_x1 - bar_x0
    fill_w = int((bar_pct / 100) * bar_width)
    if fill_w > bar_r * 2:
        draw.rounded_rectangle([bar_x0, bar_y, bar_x0 + fill_w, bar_y + bar_h],
                                radius=bar_r, fill=theme["bar_fill"])

    # Calculate messages left
    xp_left = max(0, needed_xp - progress_xp)
    msgs_left = math.ceil(xp_left / avg_xp) if avg_xp > 0 else 0
    pct_str = f"{bar_pct:.1f}%  ~{msgs_left:,} MSGS LEFT"
    
    p_w = draw.textlength(pct_str, font=f_pct)
    empty_w = bar_width - fill_w
    
    # Position logic: center in empty space if possible, else center in filled
    if p_w + 30 <= empty_w:
        # Center in unfilled part (right)
        px = bar_x0 + fill_w + (empty_w - p_w) // 2
        text_fill = (255, 255, 255) # Pure white in the dark part
    else:
        # Center in filled part (left)
        px = bar_x0 + (fill_w - p_w) // 2
        # Contrast logic for filled part
        luma = 0.299*theme["bar_fill"][0] + 0.587*theme["bar_fill"][1] + 0.114*theme["bar_fill"][2]
        text_fill = (10, 10, 10) if luma > 150 else (255, 255, 255)

    # Vertical centering for a 52px bar (26px font)
    # Using textbbox for more precise vertical centering
    _bb = draw.textbbox((0, 0), pct_str, font=f_pct)
    th = _bb[3] - _bb[1]
    py = bar_y + (bar_h - th) // 2 - 2  # slight offset for visual balance
    # Shadow for extra readability
    draw.text((px+1, py+1), pct_str, font=f_pct, fill=(0,0,0,160))
    draw.text((px, py), pct_str, font=f_pct, fill=text_fill)

    # ── Watermark ─────────────────────────────────────────────────────────────
    draw.text((AVATAR_X, H - 16), theme.get("label", ""), font=f_wmark,
              fill=(acc[0]//4, acc[1]//4, acc[2]//4))

    buf = io.BytesIO()
    card.save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf
