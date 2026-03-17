"""
quote_card.py — Pillow-based quote card generator.
Handles multi-line text wrapping and uses beautiful themes.
"""

import io
import textwrap
from PIL import Image, ImageDraw, ImageFont
from rank_card import THEMES, _load_font, FONT_DIR

# Dimensions
WIDTH, HEIGHT = 1000, 500  # Default size, can be adjusted if text is very long
PADDING = 60

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int):
    """
    Wraps text into multiple lines without splitting words.
    """
    words = text.split(' ')
    lines = []
    current_line = []

    for word in words:
        # Try adding the word to the current line
        temp_line = ' '.join(current_line + [word])
        # Get width of the line with the new word
        w = font.getlength(temp_line)
        
        if w <= max_width:
            current_line.append(word)
        else:
            # Line is full, start a new one
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def generate_quote_card(quote_text: str, theme_name: str = "obsidian") -> io.BytesIO:
    """
    Generates a beautiful image for a quote.
    """
    theme = THEMES.get(theme_name, THEMES["obsidian"])
    
    # 1. Background setup
    img = Image.new("RGB", (WIDTH, HEIGHT), theme["bg_bot"])
    draw = ImageDraw.Draw(img)

    # Background Gradient
    t, b = theme["bg_top"], theme["bg_bot"]
    for y in range(HEIGHT):
        r = t[0] + (b[0] - t[0]) * y // HEIGHT
        g = t[1] + (b[1] - t[1]) * y // HEIGHT
        bl = t[2] + (b[2] - t[2]) * y // HEIGHT
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, bl))

    acc = theme["accent"]
    pri = theme["text_pri"]
    sec = theme["text_sec"]

    # 2. Add some accent glow / scanlines
    for y in range(0, HEIGHT, 8):
        draw.line([(0, y), (WIDTH, y)], fill=(acc[0]//30, acc[1]//30, acc[2]//30))

    # 3. Draw Header
    header_text = "BLESSINGS TO APEIRON"
    header_font = _load_font("Chalice", 28)
    h_w = header_font.getlength(header_text)
    draw.text(((WIDTH - h_w) // 2, 40), header_text, font=header_font, fill=acc)
    # Underline
    draw.line([((WIDTH - h_w) // 2, 75), ((WIDTH + h_w) // 2, 75)], fill=acc, width=2)

    # 4. Wrap the text
    font_size = 46
    font = _load_font("Chalice", font_size)
    max_text_width = WIDTH - (2 * PADDING)
    lines = wrap_text(quote_text, font, max_text_width)
    
    # Vertical available space (from header underline to bottom padding)
    available_h = HEIGHT - 75 - (2 * PADDING)
    line_height = int(font_size * 1.3)
    
    # Shrink font until it fits
    while (len(lines) * line_height > available_h or any(font.getlength(l) > max_text_width for l in lines)) and font_size > 20:
        font_size -= 2
        font = _load_font("Chalice", font_size)
        line_height = int(font_size * 1.3)
        lines = wrap_text(quote_text, font, max_text_width)

    # 5. Draw Text (Centered)
    total_text_height = len(lines) * line_height
    # Center text in the area below the header
    current_y = 75 + (available_h - total_text_height) // 2
    
    for line in lines:
        line_w = font.getlength(line)
        x = (WIDTH - line_w) // 2
        # Shadow
        draw.text((x + 2, current_y + 2), line, font=font, fill=(0, 0, 0, 150))
        # Main text
        draw.text((x, current_y), line, font=font, fill=pri)
        current_y += line_height

    # 6. Border
    draw.rectangle([5, 5, WIDTH - 6, HEIGHT - 6], outline=acc, width=3)

    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf

if __name__ == "__main__":
    # Test generation
    test_quote = "To reflect that each one who enters imagines himself to be the first to enter whereas he is always the last term of a preceding series even if the first term of a succeeding one, each imagining himself to be first, last, only and alone whereas he is neither first nor last nor only nor alone."
    buf = generate_quote_card(test_quote, "cyberpunk")
    with open("test_quote.png", "wb") as f:
        f.write(buf.getbuffer())
    print("Test quote card generated as test_quote.png")
