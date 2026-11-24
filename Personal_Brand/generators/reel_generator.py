"""
9:16 Kinetic Reel Generator & FFmpeg Motion Renderer for Personal Brand Engine.
Generates retention-engineered Reel scripts + teleprompter copy, synthesizes $0
neural voiceover (edge-tts -> gTTS fallback, or user-provided voice note), and
compiles a 1080x1920 H.264 MP4 with smooth FFmpeg zoompan motion.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw, ImageOps
from pydantic import BaseModel, Field

from ..config.settings import BrandSettings, settings
from ..core.llm_client import SEO_AEO_META_RULES, build_brand_context_block, call_structured_llm
from .render_utils import (
    apply_subtle_radial_glow,
    draw_author_header,
    load_circular_avatar,
    resolve_font,
    wrap_text,
)

logger = logging.getLogger("personal_brand.reel_generator")


class ReelScene(BaseModel):
    """Single timed beat in a 9:16 vertical Reel."""
    scene_number: int = Field(..., ge=1, le=8)
    duration_sec: float = Field(default=4.0, ge=2.0, le=10.0)
    on_screen_text: str = Field(..., description="Large bold kinetic caption (3-8 words max)")
    spoken_voiceover: str = Field(..., description="Natural spoken line (1-2 short punchy sentences)")
    visual_direction: str = Field(..., description="B-roll or camera cue if creator films manually")


class ReelScript(BaseModel):
    """Complete 9:16 Instagram Reel package optimized for multimodal search & watch retention."""
    topic: str
    pillar: str
    primary_search_keyword: str = Field(
        default="",
        description="2-5 word target search phrase locked across spoken audio, on-screen text, and caption",
    )
    aeo_question: str = Field(
        default="",
        description="Explicit user question answered in this Reel",
    )
    aeo_direct_answer: str = Field(
        default="",
        description="Citation-ready 40-60 word direct factual answer with entity attribution",
    )
    title: str
    hook_0_to_3s: str = Field(..., description="Visual & verbal pattern interrupt in first 3 seconds")
    scenes: List[ReelScene]
    teleprompter_script: str = Field(..., description="Full clean read-through script if creator records on camera")
    audio_vibe: str = Field(default="Upbeat minimal lo-fi / subtle cinematic beat")
    alt_text: str = Field(
        default="",
        description="15-30 word descriptive accessibility & search description for Reel cover/video",
    )
    caption: str = Field(
        ...,
        description="SEO/AEO-optimized Reel caption: <=125-char keyword hook, AEO answer, save/share CTA",
    )
    hashtags: List[str] = Field(default_factory=list, description="3-5 hyper-relevant semantic search hashtags")


def generate_reel_script(
    topic: str,
    pillar_id: Optional[str] = None,
    brand: Optional[BrandSettings] = None,
    hook_override: Optional[str] = None,
    angle_summary: Optional[str] = None,
    primary_search_keyword: Optional[str] = None,
    aeo_question: Optional[str] = None,
    alternate_hook: bool = False,
) -> ReelScript:
    """Generates a retention-engineered, multimodal-SEO 9:16 Reel script."""
    b = brand or settings
    brand_context = build_brand_context_block(b)

    system_instruction = f"""You are a Viral Short-Form Video Director & Search Strategist for {b.name or 'the creator'} ({b.handle or '@creator'}).

{brand_context}

{SEO_AEO_META_RULES}

Create a 20–35 second Instagram Reel (5 scenes) tailored strictly to this creator's niche, voice cadence, and target audience.
Rules:
1. Scene 1 (0–3s) MUST deliver an immediate pattern-interrupt hook that stops scrolling.
2. MULTIMODAL KEYWORD LOCK: Naturally speak `primary_search_keyword` inside `spoken_voiceover` AND show it inside `on_screen_text` (Scene 1 or 2) AND front-load it in the first 125 chars of `caption`. Meta's AI indexes audio + visual text + caption together!
3. Keep `on_screen_text` ultra-concise (3–8 bold words per scene) so viewers read effortlessly on mobile.
4. Keep `spoken_voiceover` natural, conversational, and faithful to the creator's Voice DNA (zero robotic phrasing).
5. Final scene MUST include a clear DM-share ("Send this to...") or Save CTA.
6. `teleprompter_script` must combine the spoken voiceover cleanly into a single easy-to-read script.
"""

    parts = [f"Topic: {topic}", f"Pillar: {pillar_id or 'Viral Reach'}"]
    if primary_search_keyword:
        parts.append(f"Primary Search Keyword: {primary_search_keyword}")
    if aeo_question:
        parts.append(f"AEO Question to Answer: {aeo_question}")
    if hook_override:
        parts.append(f"Selected Hook Direction: {hook_override}")
    if angle_summary:
        parts.append(f"Angle Context: {angle_summary}")
    if alternate_hook:
        parts.append("ALTERNATE HOOK REQUESTED: Write a radically stronger, higher-tension 0-3s opening hook.")

    script = call_structured_llm(
        prompt="\n".join(parts),
        system_instruction=system_instruction,
        response_schema=ReelScript,
        temperature=0.84 if alternate_hook else 0.76,
    )
    for idx, sc in enumerate(script.scenes, 1):
        sc.scene_number = idx
    return script


def _get_ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists():
            return exe
    except Exception:
        pass
    sys_exe = shutil.which("ffmpeg")
    if sys_exe:
        return sys_exe
    raise RuntimeError("FFmpeg binary not found.")


async def _edge_tts_save(text: str, out_mp3: Path, voice: str = "en-US-AndrewNeural") -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_mp3))


def _synthesize_scene_audio(text: str, out_mp3: Path, voice: str = "en-US-AndrewNeural") -> bool:
    """Synthesizes $0 neural voiceover via edge-tts, falling back to gTTS."""
    clean = text.strip()
    if not clean:
        return False

    try:
        # Handle running inside an active asyncio loop (FastAPI/Telegram) or standalone thread
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(lambda: asyncio.run(_edge_tts_save(clean, out_mp3, voice))).result(timeout=20)
        else:
            asyncio.run(_edge_tts_save(clean, out_mp3, voice))

        if out_mp3.exists() and out_mp3.stat().st_size > 200:
            return True
    except Exception as e:
        logger.debug(f"edge-tts failed ({e}), trying gTTS fallback...")

    try:
        from gtts import gTTS
        tts = gTTS(text=clean, lang="en", slow=False)
        tts.save(str(out_mp3))
        return out_mp3.exists() and out_mp3.stat().st_size > 200
    except Exception as e:
        logger.warning(f"TTS fallback skipped ({e}).")
        return False


def _probe_duration_sec(ffmpeg_bin: str, media_path: Path, default_sec: float = 4.0) -> float:
    """Extracts audio duration using ffmpeg stderr output (works without ffprobe)."""
    res = subprocess.run(
        [ffmpeg_bin, "-i", str(media_path)],
        capture_output=True,
        text=True,
    )
    import re
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", res.stderr or "")
    if match:
        hrs, mins, secs = float(match.group(1)), float(match.group(2)), float(match.group(3))
        dur = hrs * 3600 + mins * 60 + secs
        if dur > 0.5:
            return dur
    return default_sec


class ReelRenderer:
    """Renders 1080x1920 vertical kinetic MP4 Reels at $0 media cost."""

    def __init__(self, brand: Optional[BrandSettings] = None):
        self.brand = brand or settings
        self.width = 1080
        self.height = 1920
        self.palette = self.brand.active_palette

        fp = self.brand.font_paths
        self.font_bold = fp.get("headline_bold")
        self.font_reg = fp.get("body_regular")

        self.f_kinetic = resolve_font(self.font_bold, 72, "bold")
        self.f_kinetic_sm = resolve_font(self.font_bold, 56, "bold")
        self.f_sub = resolve_font(self.font_reg, 34, "regular")
        self.f_badge = resolve_font(self.font_bold, 24, "bold")
        self.f_footer = resolve_font(self.font_bold, 24, "bold")
        self.avatar_img = load_circular_avatar(self.brand, size=76)

    def render_scene_image(
        self,
        scene: ReelScene,
        total_scenes: int,
        out_png: Path,
        bg_photo_path: Optional[Path] = None,
    ) -> Path:
        """Renders a 1080x1920 vertical scene frame."""
        bg_color = self.palette.get("bg_color", "#0B0F17")

        if bg_photo_path and bg_photo_path.exists():
            base = Image.open(bg_photo_path).convert("RGB")
            img = ImageOps.fit(base, (self.width, self.height), method=Image.Resampling.LANCZOS)
            scrim = Image.new("RGBA", (self.width, self.height), (8, 10, 16, 175))
            img = Image.alpha_composite(img.convert("RGBA"), scrim).convert("RGB")
            active_pal = {**self.palette, "text_primary": "#FFFFFF", "text_muted": "#CBD5E1"}
        else:
            img = Image.new("RGB", (self.width, self.height), color=bg_color)
            apply_subtle_radial_glow(
                img,
                accent_hex=self.palette.get("accent", "#10B981"),
                bg_hex=bg_color,
                center=(540, 880),
                radius=680,
                intensity=0.16,
            )
            active_pal = self.palette

        draw = ImageDraw.Draw(img)

        # Top segmented reel progress bars
        seg_gap = 12
        seg_w = (940 - seg_gap * max(0, total_scenes - 1)) / max(1, total_scenes)
        for i in range(total_scenes):
            x1 = 70 + i * (seg_w + seg_gap)
            fill = active_pal.get("accent", "#10B981") if (i + 1) <= scene.scene_number else active_pal.get("card_border", "#1E293B")
            draw.rounded_rectangle((x1, 70, x1 + seg_w, 78), radius=4, fill=fill)

        # Author pill
        draw_author_header(
            img=img,
            draw=draw,
            brand=self.brand,
            palette=active_pal,
            x=70,
            y=120,
            avatar_size=76,
            avatar_img=self.avatar_img,
        )

        # Scene pill
        pill_txt = f"0{scene.scene_number} / 0{total_scenes}"
        pb = draw.textbbox((0, 0), pill_txt, font=self.f_badge)
        pw = (pb[2] - pb[0]) + 36
        draw.rounded_rectangle((1010 - pw, 134, 1010, 182), radius=18, fill=active_pal.get("header_pill_bg", "#1E293B"))
        draw.text((1010 - pw + 18, 144), pill_txt, font=self.f_badge, fill=active_pal.get("header_pill_text", "#38BDF8"))

        # Center kinetic headline card
        k_font = self.f_kinetic if len(scene.on_screen_text) <= 36 else self.f_kinetic_sm
        k_step = 88 if k_font is self.f_kinetic else 70
        k_lines = wrap_text(scene.on_screen_text.upper(), k_font, 860, draw)[:5]

        block_h = len(k_lines) * k_step
        start_y = max(460, (self.height // 2) - (block_h // 2) - 120)

        # Accent bar above headline
        draw.rounded_rectangle((70, start_y - 34, 210, start_y - 24), radius=5, fill=active_pal.get("accent", "#10B981"))

        cy = start_y
        for line in k_lines:
            draw.text((70, cy), line, font=k_font, fill=active_pal.get("text_primary", "#F8FAFC"))
            cy += k_step

        # Voiceover subtitle box at lower third (Instagram safe zone above bottom UI)
        sub_lines = wrap_text(scene.spoken_voiceover, self.f_sub, 860, draw)[:4]
        if sub_lines:
            box_y = max(cy + 70, 1320)
            box_h = len(sub_lines) * 46 + 48
            draw.rounded_rectangle(
                (70, box_y, 1010, box_y + box_h),
                radius=20,
                fill=active_pal.get("card_bg", "#121824"),
                outline=active_pal.get("card_border", "#1E293B"),
                width=2,
            )
            sy = box_y + 24
            for sline in sub_lines:
                draw.text((100, sy), sline, font=self.f_sub, fill=active_pal.get("text_secondary", "#E2E8F0"))
                sy += 46

        # Safe-zone bottom creator handle
        draw.text((70, 1780), f"{self.brand.handle or '@creator'}  •  {self.brand.creator.get('genre') or 'Personal Brand'}", font=self.f_footer, fill=active_pal.get("text_muted", "#64748B"))

        img.save(out_png, "PNG")
        return out_png

    def render(
        self,
        script: ReelScript,
        output_dir: Path,
        bg_photo_path: Optional[Path] = None,
        user_audio_path: Optional[Path] = None,
    ) -> Path:
        """Compiles a kinetic 1080x1920 MP4 Reel and saves metadata + teleprompter script."""
        output_dir.mkdir(parents=True, exist_ok=True)
        ffmpeg_bin = _get_ffmpeg_exe()
        out_mp4 = output_dir / "reel_01.mp4"

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            scene_clips: List[Path] = []
            total_scenes = len(script.scenes)

            for sc in script.scenes:
                png_path = tmp / f"scene_{sc.scene_number:02d}.png"
                self.render_scene_image(sc, total_scenes, png_path, bg_photo_path=bg_photo_path)

                # Save preview frame of first scene for quick cover/thumbnail inspection
                if sc.scene_number == 1:
                    shutil.copy2(png_path, output_dir / "reel_cover.png")

                scene_audio = tmp / f"voice_{sc.scene_number:02d}.mp3"
                has_tts = False
                if not user_audio_path:
                    has_tts = _synthesize_scene_audio(sc.spoken_voiceover, scene_audio)

                dur = sc.duration_sec
                if has_tts:
                    dur = max(2.5, _probe_duration_sec(ffmpeg_bin, scene_audio, sc.duration_sec) + 0.35)

                fps = 24
                frames = int(dur * fps)
                clip_mp4 = tmp / f"clip_{sc.scene_number:02d}.mp4"

                # Subtle smooth zoom-in motion (1.0 -> 1.06) per scene so the Reel feels dynamic
                zoom_filter = (
                    f"scale=1200:-1,"
                    f"zoompan=z='min(zoom+0.0008,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                    f"d={frames}:s=1080x1920:fps={fps}"
                )

                cmd = [ffmpeg_bin, "-y", "-loop", "1", "-i", str(png_path)]
                if has_tts:
                    cmd.extend(["-i", str(scene_audio)])
                else:
                    cmd.extend(["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo"])

                cmd.extend([
                    "-vf", zoom_filter,
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-t", f"{dur:.2f}",
                    "-shortest",
                    str(clip_mp4),
                ])

                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    raise RuntimeError(f"FFmpeg scene render failed: {res.stderr[-300:]}")
                scene_clips.append(clip_mp4)

            concat_list = tmp / "clips.txt"
            concat_list.write_text(
                "\n".join(f"file '{c.resolve()}'" for c in scene_clips),
                encoding="utf-8",
            )

            concat_mp4 = tmp / "concat.mp4"
            res = subprocess.run(
                [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(concat_mp4)],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                raise RuntimeError(f"FFmpeg concat failed: {res.stderr[-300:]}")

            if user_audio_path and user_audio_path.exists():
                # Overlay creator's own voice note onto the compiled video
                res = subprocess.run(
                    [
                        ffmpeg_bin, "-y",
                        "-i", str(concat_mp4),
                        "-i", str(user_audio_path),
                        "-map", "0:v:0", "-map", "1:a:0",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                        "-shortest", "-movflags", "+faststart",
                        str(out_mp4),
                    ],
                    capture_output=True,
                    text=True,
                )
                if res.returncode != 0:
                    shutil.copy2(concat_mp4, out_mp4)
            else:
                shutil.move(str(concat_mp4), str(out_mp4))

        meta_path = output_dir / "reel_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(script.model_dump_json(indent=2))

        (output_dir / "teleprompter.txt").write_text(script.teleprompter_script, encoding="utf-8")
        return out_mp4
