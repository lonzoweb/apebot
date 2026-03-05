"""
rank_card.py — Pillow-based rank card image generator.

Downloads TTF fonts on first use from Google Fonts (cached locally).
Falls back to PIL default font if download fails.
"""

import io
import logging
import urllib.request
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
    "_Mono":    "https://github.com/google/fonts/raw/main/apache/robotomono/RobotoMono-Bold.ttf",
    "_MonoReg": "https://github.com/google/fonts/raw/main/apache/robotomono/RobotoMono-Regular.ttf",
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
COL2_X       = STATS_X + 330                 # second column of 2x2 grid


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
    font_name:    str = "Halo",
    theme_name:   str = "matrix",
    member_days:  int = 0,
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
    # Custom font: username + all stat labels
    f_user  = _load_font(font_name, 52)   # username
    f_label = _load_font(font_name, 44)   # stat labels (RANK, BALANCE, etc.) — was 42
    # Mono for pure numbers / progress bar %
    f_val   = _load_mono(34)              # stat values
    f_level = _load_mono(70)              # big level number top-right
    f_star  = _load_mono(56)              # ★
    f_pct   = _load_mono(14)             # % inside bar
    f_wmark = _load_mono(13)             # theme watermark

    # ── ★ LEVEL — top-right ───────────────────────────────────────────────────
    star_str  = "★"
    level_str = str(level)
    star_w = draw.textlength(star_str, font=f_star)
    lvl_w  = draw.textlength(level_str, font=f_level)
    sx = W - int(star_w + 10 + lvl_w) - 16
    sy = 8
    draw.text((sx, sy),                  star_str,  font=f_star,  fill=acc)
    draw.text((sx + star_w + 10, sy + 6), level_str, font=f_level, fill=acc)

    # ── USERNAME ──────────────────────────────────────────────────────────────
    uy = 20
    # shadow
    draw.text((STATS_X + 2, uy + 2), username.upper(), font=f_user,
              fill=(acc[0]//5, acc[1]//5, acc[2]//5))
    draw.text((STATS_X, uy), username.upper(), font=f_user, fill=pri)

    # ── 2 × 2 STAT GRID ──────────────────────────────────────────────────────
    # Row 1 y=92 (label), row 2 y=182 (label)  — value 50px below each label
    LABEL_Y1, LABEL_Y2 = 95, 185
    VAL_OFFSET = 48   # px below label to place value

    cells = [
        # (col_x, label_y,  label_text,              value_text,                  val_color)
        (STATS_X, LABEL_Y1, "RANK",    f"#{server_rank:,}",             acc),
        (COL2_X,  LABEL_Y1, "BALANCE", f"{balance:,} \U0001f48e",       pri),
        (STATS_X, LABEL_Y2, "EXP",     f"{int(progress_xp):,} / {int(needed_xp):,}", pri),
        (COL2_X,  LABEL_Y2, "MEMBER",  f"{member_days:,} days",         sec),
    ]

    for col_x, lbl_y, label, value, val_col in cells:
        draw.text((col_x, lbl_y), label, font=f_label, fill=sec)
        draw.text((col_x, lbl_y + VAL_OFFSET), value, font=f_val, fill=val_col)

    # ── XP PROGRESS BAR ───────────────────────────────────────────────────────
    bar_h  = 12
    bar_y  = H - 30
    bar_x0, bar_x1 = STATS_X, W - 20
    bar_r  = bar_h // 2

    draw.rounded_rectangle([bar_x0, bar_y, bar_x1, bar_y + bar_h],
                            radius=bar_r, fill=theme["bar_bg"], outline=acc, width=1)
    fill_w = int((bar_pct / 100) * (bar_x1 - bar_x0))
    if fill_w > bar_r * 2:
        draw.rounded_rectangle([bar_x0, bar_y, bar_x0 + fill_w, bar_y + bar_h],
                                radius=bar_r, fill=theme["bar_fill"])

    pct_str = f"{bar_pct:.1f}%"
    px = bar_x0 + (bar_x1 - bar_x0) // 2 - int(draw.textlength(pct_str, font=f_pct)) // 2
    luma = 0.299*theme["bar_fill"][0] + 0.587*theme["bar_fill"][1] + 0.114*theme["bar_fill"][2]
    draw.text((px, bar_y - 1), pct_str, font=f_pct,
              fill=(10, 10, 10) if luma > 140 else (230, 230, 230))

    # ── Watermark ─────────────────────────────────────────────────────────────
    draw.text((AVATAR_X, H - 16), theme.get("label", ""), font=f_wmark,
              fill=(acc[0]//4, acc[1]//4, acc[2]//4))

    buf = io.BytesIO()
    card.save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf
