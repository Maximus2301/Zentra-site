#!/usr/bin/env python3
"""
Generate HYT MONEY app launcher icons.
Dark navy background with metallic gold 'H' in Cinzel Bold.
Writes all Android mipmap densities + adaptive icon layers.
"""
import os
import sys
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont

RENDER_SIZE = 4096
FONT_PATH   = "/tmp/Cinzel.ttf"
FONT_URL    = "https://github.com/google/fonts/raw/main/ofl/cinzel/Cinzel[wght].ttf"

MIPMAP_SIZES = {
    "mipmap-mdpi":    48,
    "mipmap-hdpi":    72,
    "mipmap-xhdpi":   96,
    "mipmap-xxhdpi":  144,
    "mipmap-xxxhdpi": 192,
}

RES_DIR = os.path.join(
    os.path.dirname(__file__),
    "sms_finance_tracker/android/app/src/main/res",
)

# Metallic gold gradient (same palette as Zantra Z)
GRADIENT_STOPS = [
    (0.00, (90,  65,  8)),
    (0.18, (180, 138, 30)),
    (0.38, (212, 175, 55)),
    (0.50, (241, 215, 122)),
    (0.62, (212, 175, 55)),
    (0.82, (180, 138, 30)),
    (1.00, (90,  65,  8)),
]

BG_COLOR = [13, 13, 31]   # #0D0D1F — same dark navy as Zantra icon


def download_font():
    if os.path.exists(FONT_PATH):
        return
    print("Downloading Cinzel font …")
    r = requests.get(FONT_URL, timeout=30)
    r.raise_for_status()
    with open(FONT_PATH, "wb") as f:
        f.write(r.content)
    print("Font downloaded.")


def make_gradient(width, height):
    arr = np.zeros((height, width, 3), dtype=np.float32)
    xs  = np.linspace(0.0, 1.0, width)
    for xi, t in enumerate(xs):
        for i in range(len(GRADIENT_STOPS) - 1):
            t0, c0 = GRADIENT_STOPS[i]
            t1, c1 = GRADIENT_STOPS[i + 1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0)
                color = tuple(c0[k] + (c1[k] - c0[k]) * f for k in range(3))
                arr[:, xi, :] = color
                break
    return arr.clip(0, 255).astype(np.uint8)


def render_master():
    """Render 1024×1024 master icon (4× supersampled)."""
    font_size = int(RENDER_SIZE * 0.68)
    font      = ImageFont.truetype(FONT_PATH, font_size)

    mask_pil  = Image.new("L", (RENDER_SIZE, RENDER_SIZE), 0)
    mask_draw = ImageDraw.Draw(mask_pil)
    bbox      = mask_draw.textbbox((0, 0), "H", font=font)
    tw, th    = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (RENDER_SIZE - tw) // 2 - bbox[0]
    y = (RENDER_SIZE - th) // 2 - bbox[1]
    mask_draw.text((x, y), "H", font=font, fill=255)

    final = 1024
    mask_small = mask_pil.resize((final, final), Image.LANCZOS)
    mask       = np.array(mask_small, dtype=np.float32) / 255.0

    gradient = make_gradient(final, final)
    bg       = np.full((final, final, 3), BG_COLOR, dtype=np.uint8)
    alpha    = mask[:, :, np.newaxis]
    result   = (alpha * gradient + (1 - alpha) * bg).clip(0, 255).astype(np.uint8)

    return Image.fromarray(result, "RGB")


def write_adaptive_xml():
    """Write ic_launcher.xml and ic_launcher_round.xml for API 26+."""
    anydpi_dir = os.path.join(RES_DIR, "mipmap-anydpi-v26")
    os.makedirs(anydpi_dir, exist_ok=True)

    xml = """\
<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background"/>
    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>
</adaptive-icon>
"""
    for name in ("ic_launcher.xml", "ic_launcher_round.xml"):
        path = os.path.join(anydpi_dir, name)
        with open(path, "w") as f:
            f.write(xml)
        print(f"  wrote {path}")

    # Color resource for background
    values_dir = os.path.join(RES_DIR, "values")
    os.makedirs(values_dir, exist_ok=True)
    colors_path = os.path.join(values_dir, "ic_launcher_background.xml")
    with open(colors_path, "w") as f:
        f.write("""\
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#0D0D1F</color>
</resources>
""")
    print(f"  wrote {colors_path}")


def main():
    download_font()
    master = render_master()
    print(f"Master icon rendered: {master.size[0]}×{master.size[1]}")

    # Legacy PNG icons at each density
    for subdir, size in MIPMAP_SIZES.items():
        d = os.path.join(RES_DIR, subdir)
        os.makedirs(d, exist_ok=True)
        resized = master.resize((size, size), Image.LANCZOS)
        # ic_launcher.png
        out = os.path.join(d, "ic_launcher.png")
        resized.save(out, "PNG")
        # ic_launcher_round.png — same image; Android crops to circle
        out_r = os.path.join(d, "ic_launcher_round.png")
        resized.save(out_r, "PNG")
        print(f"  {subdir}: {size}×{size}  →  ic_launcher.png + ic_launcher_round.png")

    # Foreground layer for adaptive icon (same master, slightly smaller safe zone)
    fg_size = 108  # dp — Android adaptive icon foreground canvas
    fg_safe = int(fg_size * 0.667)   # 72dp — safe zone
    for subdir, base_px in MIPMAP_SIZES.items():
        # Scale: the adaptive foreground is 108dp; same density ratio applies
        density_scale = base_px / 48  # mdpi=1×, hdpi=1.5×, etc.
        fg_px  = int(fg_size * density_scale)
        safe_px = int(fg_safe * density_scale)
        # Render H centred in the 108dp canvas (letterform in safe zone)
        canvas = Image.new("RGBA", (fg_px, fg_px), (0, 0, 0, 0))
        # Place master (resized to safe zone) centred
        inner = master.resize((safe_px, safe_px), Image.LANCZOS)
        inner_rgba = inner.convert("RGBA")
        # Make the BG transparent for the foreground layer
        arr = np.array(inner_rgba, dtype=np.float32)
        # Background pixels (close to BG_COLOR) → transparent
        bg = np.array(BG_COLOR, dtype=np.float32)
        dist = np.linalg.norm(arr[:, :, :3] - bg, axis=2)
        arr[:, :, 3] = np.where(dist < 40, 0, 255).astype(np.float32)
        inner_t = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")
        offset = (fg_px - safe_px) // 2
        canvas.paste(inner_t, (offset, offset), inner_t)
        d = os.path.join(RES_DIR, subdir)
        fg_out = os.path.join(d, "ic_launcher_foreground.png")
        canvas.save(fg_out, "PNG")

    write_adaptive_xml()
    print("\n✅  All icon files written to:", RES_DIR)


if __name__ == "__main__":
    main()
