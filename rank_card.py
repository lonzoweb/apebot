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
        "bg_top":   (5,  12,  5), "bg_bot":   (0,   0,  0),
        "accent":   (0, 255, 70), "bar_fill": (0, 220, 60),
        "bar_bg":   (15, 40, 15), "text_pri": (200, 255, 200),
        "text_sec": (100, 200, 100), "ring":   (0, 255, 70),
        "label":    "☠ MATRIX",
    },
    "cyberpunk": {
        "bg_top":   (10,  5, 25), "bg_bot":   (0,   0,  0),
        "accent":   (255, 0, 200), "bar_fill": (190, 0, 255),
        "bar_bg":   (40,  5, 60), "text_pri": (255, 200, 255),
        "text_sec": (200, 100, 255), "ring":   (255, 0, 200),
        "label":    "⚡ CYBERPUNK",
    },
    "vampire": {
        "bg_top":   (20,  0,  0), "bg_bot":   (5,   0,  0),
        "accent":   (200, 0, 30), "bar_fill": (180, 0, 20),
        "bar_bg":   (50, 10, 10), "text_pri": (255, 200, 200),
        "text_sec": (200, 100, 100), "ring":   (200, 0, 30),
        "label":    "🩸 VAMPIRE",
    },
    "ghost": {
        "bg_top":   (15, 15, 20), "bg_bot":   (5,   5, 10),
        "accent":   (180, 180, 255), "bar_fill": (140, 140, 255),
        "bar_bg":   (30,  30, 60), "text_pri": (220, 220, 255),
        "text_sec": (150, 150, 200), "ring":   (160, 160, 255),
        "label":    "👻 GHOST",
    },
    "obsidian": {
        "bg_top":   (10, 10, 10), "bg_bot":   (0,   0,  0),
        "accent":   (255, 215, 0), "bar_fill": (220, 180, 0),
        "bar_bg":   (40,  35,  5), "text_pri": (255, 230, 150),
        "text_sec": (200, 170, 80), "ring":   (255, 215, 0),
        "label":    "⚫ OBSIDIAN",
    },
    "aurora": {
        "bg_top":   (0,  15, 25), "bg_bot":   (0,   5, 10),
        "accent":   (0, 235, 200), "bar_fill": (0, 200, 170),
        "bar_bg":   (0,  40, 40), "text_pri": (180, 255, 240),
        "text_sec": (80, 200, 180), "ring":   (0, 220, 190),
        "label":    "🌌 AURORA",
    },
    "crimson": {
        "bg_top":   (20,  0, 10), "bg_bot":   (5,   0,  5),
        "accent":   (255, 50, 100), "bar_fill": (220, 30, 80),
        "bar_bg":   (60, 10, 30), "text_pri": (255, 180, 200),
        "text_sec": (200, 100, 140), "ring":   (255, 50, 100),
        "label":    "💀 CRIMSON",
    },
    "void": {
        "bg_top":   (5,   0, 15), "bg_bot":   (0,   0,  5),
        "accent":   (130, 0, 255), "bar_fill": (110, 0, 220),
        "bar_bg":   (25,  0, 50), "text_pri": (210, 180, 255),
        "text_sec": (150, 100, 220), "ring":   (130, 0, 255),
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
    t, b = theme["bg_top"], theme["bg_bot"]
    for y in range(H):
        r  = t[0] + (b[0] - t[0]) * y // H
        g  = t[1] + (b[1] - t[1]) * y // H
        bl = t[2] + (b[2] - t[2]) * y // H
        draw.line([(0, y), (W, y)], fill=(r, g, bl))

    acc = theme["accent"]
    for y in range(0, H, 6):   # scanlines
        draw.line([(0, y), (W, y)], fill=(acc[0]//20, acc[1]//20, acc[2]//20))

    # diagonal accent corner top-right
    draw.polygon([(W - 240, 0), (W, 0), (W, 240)],
                 fill=(acc[0]//8, acc[1]//8, acc[2]//8))

    # neon border frame
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
    theme_name:   str = "matrix",
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
    f_user  = _load_font(font_name, 46)   # username — down 6px from 52
    f_label = _load_font(font_name, 21)   # stat labels
    f_val   = _load_font(font_name, 33)   # stat values
    f_level = _load_font(font_name, 46)   # level — now same as username
    
    # Mono for persistent UI elements (star is being replaced)
    f_pct   = _load_font("Avenger", 18)   # Always use Avenger for bar text
    f_wmark = _load_mono(13)              # theme watermark

    # ── LEVEL CIRCLE ── top-right
    lvl_str = str(level)
    circ_size = 80
    cx, cy = W - circ_size - 25, 20
    # draw circle
    draw.ellipse([cx, cy, cx+circ_size, cy+circ_size], outline=acc, width=3)
    # text centering
    l_w = draw.textlength(lvl_str, font=f_level)
    tx = cx + (circ_size - l_w) // 2
    ty = cy + (circ_size - 46) // 2 - 4
    draw.text((tx, ty), lvl_str, font=f_level, fill=pri)
    # Small "LVL" tag above or inside? Let's put it tiny inside
    f_tiny = _load_mono(10)
    draw.text((cx + (circ_size - 20)//2, cy + 10), "LVL", font=f_tiny, fill=sec)

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
        (COL2_X,  LABEL_Y1, "BALANCE", f"{balance:,} 💎"),
        (STATS_X, LABEL_Y2, "EXP",     f"{int(progress_xp)}/{int(needed_xp)}"),
        (COL2_X,  LABEL_Y2, "MEMBER",  f"{member_days:,}d"),
    ]

    for col_x, lbl_y, label, value in cells:
        draw.text((col_x, lbl_y), label, font=f_label, fill=sec)
        # Calculate width of label to place value right after it
        lbl_w = draw.textlength(label, font=f_label)
        # Vertical offset -12 to align visual baselines of different sizes
        draw.text((col_x + lbl_w + 15, lbl_y - 12), value, font=f_val, fill=pri)

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

    # Vertical centering for a 52px bar (18px font)
    py = bar_y + (bar_h - 18) // 2 - 4
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
