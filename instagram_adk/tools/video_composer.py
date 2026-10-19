"""In-Dashboard Native Vertical Video Compositor Engine.

Compiles multi-scene ReelScreenplays (scenes, durations, visual prompts,
voiceovers, and on-screen text) into playable vertical 1080x1920 H.264 MP4 files.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw, ImageFont

from ..models.state import AccountContext, CoreNarrative, ReelDraft

logger = logging.getLogger("instagram_adk.video_composer")


def _get_ffmpeg_path() -> str:
    """Locates the FFmpeg binary via imageio_ffmpeg or system PATH."""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(exe):
            return exe
    except Exception:
        pass

    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg

    raise RuntimeError("FFmpeg executable not found. Please install imageio-ffmpeg.")


def _hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    h = hex_code.lstrip("#")
    if len(h) == 6:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    return (15, 23, 42)


def render_scene_frame(
    output_png: Path,
    scene_idx: int,
    total_scenes: int,
    account: AccountContext,
    start_sec: float,
    end_sec: float,
    on_screen_text: str,
    visual_broll: str,
    voiceover: str,
) -> Path:
    """Renders a cinematic vertical 1080x1920 scene slide with branding & kinetic text."""
    width, height = 1080, 1920
    palette = account.color_palette or ["#0D0D11", "#E63946", "#38BDF8"]
    bg_rgb = _hex_to_rgb(palette[0])
    accent_rgb = _hex_to_rgb(palette[1]) if len(palette) > 1 else (201, 162, 42)
    cyan_rgb = _hex_to_rgb(palette[2]) if len(palette) > 2 else (110, 207, 219)

    img = Image.new("RGB", (width, height), bg_rgb)
    draw = ImageDraw.Draw(img)

    # 1. Atmospheric radial glow
    for r in range(450, 0, -10):
        alpha = int(25 * (1 - r / 450))
        glow_color = (
            min(255, bg_rgb[0] + int((accent_rgb[0] - bg_rgb[0]) * (alpha / 100))),
            min(255, bg_rgb[1] + int((accent_rgb[1] - bg_rgb[1]) * (alpha / 100))),
            min(255, bg_rgb[2] + int((accent_rgb[2] - bg_rgb[2]) * (alpha / 100))),
        )
        draw.ellipse([(-100 - r, -100 - r), (500 + r, 500 + r)], fill=glow_color)

    # 2. Modern grid / letterbox aesthetic border
    draw.rectangle([(50, 50), (width - 50, height - 50)], outline=(45, 45, 55), width=2)
    draw.rectangle([(56, 56), (width - 56, height - 56)], outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2]), width=1)

    # 3. Top Header: Channel branding & Scene progress
    font_small = ImageFont.load_default()
    brand_header = f"{account.name.upper()}  •  {account.handle}"
    draw.text((90, 95), brand_header, fill=(200, 200, 210), font=font_small)

    scene_progress = f"SCENE {scene_idx}/{total_scenes}  [{start_sec:.1f}s - {end_sec:.1f}s]"
    draw.text((width - 320, 95), scene_progress, fill=accent_rgb, font=font_small)

    # 4. Central Visual B-roll directive badge
    draw.rounded_rectangle([(90, 180), (width - 90, 360)], radius=16, fill=(24, 24, 32), outline=(50, 50, 65))
    draw.text((120, 205), "🎬 VISUAL B-ROLL DIRECTIVE:", fill=cyan_rgb, font=font_small)
    # Wrap b-roll text
    broll_words = visual_broll.split()
    broll_lines: list[str] = []
    curr_line = ""
    for w in broll_words:
        if len(curr_line) + len(w) + 1 <= 55:
            curr_line = f"{curr_line} {w}".strip()
        else:
            broll_lines.append(curr_line)
            curr_line = w
    if curr_line:
        broll_lines.append(curr_line)
    for l_idx, bl in enumerate(broll_lines[:4]):
        draw.text((120, 240 + l_idx * 26), bl, fill=(230, 230, 240), font=font_small)

    # 5. Core Hero Kinetic Typography (On-Screen Text)
    draw.rounded_rectangle([(90, 480), (width - 90, 1100)], radius=24, fill=(18, 18, 24), outline=accent_rgb, width=3)
    
    # Glowing decorative tag
    draw.rounded_rectangle([(140, 520), (380, 570)], radius=12, fill=accent_rgb)
    draw.text((160, 535), "⚡ ON-SCREEN HOOK", fill=(10, 10, 15), font=font_small)

    # Main text centered
    words = on_screen_text.split()
    lines: list[str] = []
    curr = ""
    for w in words:
        if len(curr) + len(w) + 1 <= 24:
            curr = f"{curr} {w}".strip()
        else:
            lines.append(curr)
            curr = w
    if curr:
        lines.append(curr)

    y_start = 640
    for l_idx, text_line in enumerate(lines[:6]):
        draw.text((140, y_start + l_idx * 60), text_line.upper(), fill=(255, 255, 255), font=font_small)

    # 6. Spoken Dialogue / Voiceover box at bottom
    draw.rounded_rectangle([(90, 1200), (width - 90, 1600)], radius=20, fill=(20, 20, 28), outline=(60, 60, 80))
    draw.text((130, 1230), "🎙️ SPOKEN VOICEOVER NARRATION:", fill=accent_rgb, font=font_small)
    
    vo_words = voiceover.split()
    vo_lines: list[str] = []
    c_vo = ""
    for w in vo_words:
        if len(c_vo) + len(w) + 1 <= 48:
            c_vo = f"{c_vo} {w}".strip()
        else:
            vo_lines.append(c_vo)
            c_vo = w
    if c_vo:
        vo_lines.append(c_vo)
    for l_idx, vl in enumerate(vo_lines[:8]):
        draw.text((130, 1275 + l_idx * 34), f"\"{vl}\"", fill=(220, 220, 230), font=font_small)

    # 7. Bottom Branding Footer
    draw.text((90, 1780), f"Zentra AI Autonomous Studio  |  Google ADK 2.0 Video Engine", fill=(120, 120, 135), font=font_small)
    draw.text((width - 250, 1780), "9:16 VERTICAL REEL", fill=cyan_rgb, font=font_small)

    img.save(str(output_png), "PNG")
    return output_png


def synthesize_voiceover_audio(text: str, output_mp3: Path) -> bool:
    """Synthesizes voiceover dialogue using gTTS if available."""
    try:
        from gtts import gTTS
        clean_text = text.replace('"', '').replace("'", "").strip()
        if not clean_text:
            clean_text = "Watch till the end to discover how this works."
        tts = gTTS(text=clean_text, lang='en', tld='com', slow=False)
        tts.save(str(output_mp3))
        return True
    except Exception as e:
        logger.warning(f"Voiceover TTS synthesis skipped ({e}). Using ambient audio generation.")
        return False


def compose_in_dashboard_reel_video(
    reel: ReelDraft,
    account: AccountContext,
    narrative: CoreNarrative,
    output_mp4_path: Path,
) -> Path:
    """Renders and compiles a complete vertical 1080x1920 MP4 video for in-dashboard playback."""
    ffmpeg_bin = _get_ffmpeg_path()
    output_mp4_path.parent.mkdir(parents=True, exist_ok=True)

    scenes = reel.scenes or []
    if not scenes:
        logger.warning("No scenes found in ReelDraft. Generating single default scene.")
        from ..models.state import ReelScene
        scenes = [
            ReelScene(
                timestamp_start_sec=0.0,
                timestamp_end_sec=float(reel.duration_seconds or 15),
                visual_broll_prompt=narrative.hook,
                spoken_voiceover=narrative.hook,
                on_screen_text=narrative.hook[:40].upper(),
            )
        ]

    total_scenes = len(scenes)
    duration_total = float(reel.duration_seconds or 30)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        concat_txt = tmp_path / "concat.txt"
        scene_files: list[Path] = []
        audio_files: list[Path] = []

        concat_lines: list[str] = []

        for idx, sc in enumerate(scenes, start=1):
            sc_duration = max(1.5, sc.timestamp_end_sec - sc.timestamp_start_sec)
            scene_img = tmp_path / f"scene_{idx}.png"
            render_scene_frame(
                output_png=scene_img,
                scene_idx=idx,
                total_scenes=total_scenes,
                account=account,
                start_sec=sc.timestamp_start_sec,
                end_sec=sc.timestamp_end_sec,
                on_screen_text=sc.on_screen_text,
                visual_broll=sc.visual_broll_prompt,
                voiceover=sc.spoken_voiceover,
            )
            scene_files.append(scene_img)

            # Concat entry (format: file 'path' \n duration X)
            concat_lines.append(f"file '{scene_img.resolve()}'")
            concat_lines.append(f"duration {sc_duration:.2f}")

            # Try generating voiceover audio snippet
            sc_audio = tmp_path / f"audio_{idx}.mp3"
            if synthesize_voiceover_audio(sc.spoken_voiceover, sc_audio):
                audio_files.append(sc_audio)

        # Concat demuxer requirement: last file must be repeated without duration
        if scene_files:
            concat_lines.append(f"file '{scene_files[-1].resolve()}'")

        concat_txt.write_text("\n".join(concat_lines), encoding="utf-8")

        # Compile Video using FFmpeg
        # We produce 1080x1920 24fps H.264 video with AAC audio
        has_audio = len(audio_files) == len(scenes) and len(audio_files) > 0
        combined_audio = tmp_path / "combined_audio.mp3"

        if has_audio:
            # Concatenate scene audio clips
            audio_concat_txt = tmp_path / "audio_concat.txt"
            audio_concat_txt.write_text(
                "\n".join([f"file '{a.resolve()}'" for a in audio_files]),
                encoding="utf-8"
            )
            subprocess.run([
                ffmpeg_bin, "-y", "-f", "concat", "-safe", "0",
                "-i", str(audio_concat_txt),
                "-c", "copy", str(combined_audio)
            ], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        cmd = [
            ffmpeg_bin,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_txt),
        ]

        if combined_audio.exists():
            cmd.extend([
                "-i", str(combined_audio),
                "-c:a", "aac",
                "-b:a", "128k",
            ])
        else:
            # Generate a subtle ambient synthetic audio track (lo-fi hum at 110Hz + 220Hz harmonic)
            cmd.extend([
                "-f", "lavfi",
                "-i", f"sine=frequency=110:duration={duration_total},volume=0.15",
                "-c:a", "aac",
                "-b:a", "128k",
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", "24",
            "-t", str(duration_total),
            "-movflags", "+faststart",
            str(output_mp4_path),
        ])

        logger.info(f"🎞️ Compiling vertical MP4 reel with FFmpeg (duration: {duration_total}s)...")
        res = subprocess.run(cmd, capture_output=True, text=True)

        if res.returncode != 0:
            logger.error(f"FFmpeg compilation failed: {res.stderr}")
            raise RuntimeError(f"FFmpeg error: {res.stderr[:200]}")

        logger.info(f"✓ Vertical Reel MP4 generated successfully: {output_mp4_path.name} ({output_mp4_path.stat().st_size} bytes)")
        return output_mp4_path
