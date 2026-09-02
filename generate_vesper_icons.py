import math
from PIL import Image, ImageDraw, ImageFilter

def create_vesper_icon(size=512):
    # Render at 4x for extreme antialiasing quality
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Base Squircle (Dark Obsidian Slate)
    pad = int(s * 0.05)
    r = int(s * 0.22)
    # Background rounded rect
    draw.rounded_rectangle(
        [pad, pad, s - pad, s - pad],
        radius=r,
        fill=(15, 17, 23, 255),
        outline=(35, 39, 50, 255),
        width=int(s * 0.015)
    )

    # Subtle inner border for tactile feel
    draw.rounded_rectangle(
        [pad + int(s*0.012), pad + int(s*0.012), s - pad - int(s*0.012), s - pad - int(s*0.012)],
        radius=r - int(s*0.01),
        outline=(25, 28, 38, 255),
        width=int(s * 0.008)
    )

    # 2. RF Antenna Wave Arcs (Burnt Ember)
    cx, cy = s // 2, int(s * 0.44)
    # Outer arc
    arc1_r = int(s * 0.16)
    draw.arc(
        [cx - arc1_r, cy - arc1_r, cx + arc1_r, cy + arc1_r],
        start=215, end=325,
        fill=(230, 111, 39, 230),
        width=int(s * 0.02)
    )
    # Inner arc
    arc2_r = int(s * 0.11)
    draw.arc(
        [cx - arc2_r, cy - arc2_r, cx + arc2_r, cy + arc2_r],
        start=210, end=330,
        fill=(230, 111, 39, 255),
        width=int(s * 0.02)
    )

    # 3. Outer Chevron V (Crisp White/Platinum)
    v_top_y = int(s * 0.32)
    v_bot_y = int(s * 0.78)
    v_left_x = int(s * 0.22)
    v_right_x = int(s * 0.78)
    v_thick = int(s * 0.038)

    # Left leg outer
    draw.line([(v_left_x, v_top_y), (cx, v_bot_y)], fill=(255, 255, 255, 255), width=v_thick)
    # Right leg outer
    draw.line([(v_right_x, v_top_y), (cx, v_bot_y)], fill=(255, 255, 255, 255), width=v_thick)

    # 4. Inner Chevron V (Brushed Titanium / Slate)
    in_top_y = int(s * 0.40)
    in_bot_y = int(s * 0.67)
    in_left_x = int(s * 0.33)
    in_right_x = int(s * 0.67)
    in_thick = int(s * 0.025)

    draw.line([(in_left_x, in_top_y), (cx, in_bot_y)], fill=(161, 166, 180, 255), width=in_thick)
    draw.line([(in_right_x, in_top_y), (cx, in_bot_y)], fill=(161, 166, 180, 255), width=in_thick)

    # 5. Glowing Amber Core Diode
    diode_y = int(s * 0.52)
    diode_r = int(s * 0.038)

    # Glow layer
    glow_r = int(s * 0.08)
    glow_img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_img)
    glow_draw.ellipse([cx - glow_r, diode_y - glow_r, cx + glow_r, diode_y + glow_r], fill=(230, 111, 39, 140))
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(int(s * 0.03)))
    img = Image.alpha_composite(img, glow_img)

    draw = ImageDraw.Draw(img)
    draw.ellipse([cx - diode_r, diode_y - diode_r, cx + diode_r, diode_y + diode_r], fill=(245, 130, 50, 255))
    inner_core = int(diode_r * 0.5)
    draw.ellipse([cx - inner_core, diode_y - inner_core, cx + inner_core, diode_y + inner_core], fill=(255, 210, 150, 255))

    # Downsample with LANCZOS to target size
    final_img = img.resize((size, size), Image.Resampling.LANCZOS)
    return final_img

# Generate all icon assets
icon_512 = create_vesper_icon(512)
icon_512.save("static/pwa/icons/icon-512.png", "PNG")
icon_512.save("static/pwa/icons/icon-maskable.png", "PNG")

icon_192 = create_vesper_icon(192)
icon_192.save("static/pwa/icons/icon-192.png", "PNG")
icon_192.save("static/pwa/icons/favicon.png", "PNG")

print("Vesper PWA icons generated successfully!")
