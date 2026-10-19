"""Google Vids Storyboard Exporter & Workspace Bridge Agent.

Formats Reel screenplays into structured blueprints and optimized prompts
for Google Workspace's Google Vids (vids.google.com / vids.new).
"""
from __future__ import annotations

from typing import Any
from ..models.state import AccountContext, CoreNarrative, ReelDraft


def build_google_vids_prompt(
    reel: ReelDraft,
    account: AccountContext,
    narrative: CoreNarrative,
) -> str:
    """Generates an optimized prompt tailored for Google Vids' 'Help me create a video' bar."""
    duration = reel.duration_seconds or 45
    lines = [
        f"Create a {duration}-second vertical (9:16) social media video for Instagram.",
        f"Channel: {account.name} ({account.handle})",
        f"Target Audience: {narrative.cohort_name}",
        f"Tone & Emotion: {narrative.target_emotion} (high production value, fast-paced retention)",
        f"Core Hook: \"{narrative.hook}\"",
        "",
        "Scene Breakdown & Storyboard:",
    ]

    for idx, sc in enumerate(reel.scenes, start=1):
        lines.append(
            f"Scene {idx} ({sc.timestamp_start_sec:.1f}s - {sc.timestamp_end_sec:.1f}s):"
        )
        lines.append(f"  • Visual B-roll: {sc.visual_broll_prompt}")
        lines.append(f"  • Spoken Voiceover: \"{sc.spoken_voiceover}\"")
        lines.append(f"  • On-Screen Graphic: \"{sc.on_screen_text}\"")

    lines.append("")
    lines.append(f"Background Audio Mood: {reel.music_mood or 'Modern lo-fi deep tech groove'}")
    lines.append(f"Call to Action: {narrative.call_to_action}")
    if account.mandatory_disclaimers:
        lines.append(f"Legal Disclaimer: {account.mandatory_disclaimers[0]}")

    return "\n".join(lines)


def build_google_vids_markdown(
    reel: ReelDraft,
    account: AccountContext,
    narrative: CoreNarrative,
) -> str:
    """Builds a formatted Markdown storyboard table for Google Drive / Docs import."""
    duration = reel.duration_seconds or 45
    md = [
        f"# Google Vids Production Storyboard: {account.name}",
        f"**Handle**: `{account.handle}` | **Target Duration**: `{duration}s` | **Aspect Ratio**: `9:16 (Vertical)`",
        f"**Audience**: {narrative.cohort_name} | **Target Emotion**: {narrative.target_emotion}",
        f"**Core Hook**: > *\"{narrative.hook}\"*",
        "",
        "## Scene-by-Scene Storyboard Table",
        "",
        "| Scene # | Timing | Visual Cue / B-Roll | Spoken Voiceover Dialogue | On-Screen Graphic |",
        "| :---: | :---: | :--- | :--- | :--- |",
    ]

    for idx, sc in enumerate(reel.scenes, start=1):
        timing = f"{sc.timestamp_start_sec:.1f}s – {sc.timestamp_end_sec:.1f}s"
        broll = sc.visual_broll_prompt.replace("|", "/")
        vo = sc.spoken_voiceover.replace("|", "/")
        text = sc.on_screen_text.replace("|", "/")
        md.append(f"| {idx} | {timing} | {broll} | \"{vo}\" | **{text}** |")

    md.extend([
        "",
        "## Production Audio & Polish",
        f"- **Music Mood**: {reel.music_mood}",
        f"- **Call to Action**: {narrative.call_to_action}",
        f"- **Captions & Tags**: `{' '.join(reel.hashtags)}`",
        "",
        "## Google Vids Workspace Instructions",
        "1. Open [Google Vids (vids.new)](https://vids.new) in your Google Workspace.",
        "2. Click **'Help me create a video'** in the central creation bar.",
        "3. Paste the prompt generated above or attach this storyboard document.",
        "4. Google Vids will automatically populate the timeline, voiceover, and stock footage.",
    ])

    return "\n".join(md)


def export_google_vids_blueprint(
    reel: ReelDraft,
    account: AccountContext,
    narrative: CoreNarrative,
) -> dict[str, Any]:
    """Generates the full Google Vids export blueprint."""
    prompt = build_google_vids_prompt(reel, account, narrative)
    markdown = build_google_vids_markdown(reel, account, narrative)

    scenes_data = []
    for idx, sc in enumerate(reel.scenes, start=1):
        scenes_data.append({
            "scene_number": idx,
            "start_time_sec": sc.timestamp_start_sec,
            "end_time_sec": sc.timestamp_end_sec,
            "duration_sec": round(sc.timestamp_end_sec - sc.timestamp_start_sec, 1),
            "visual_broll": sc.visual_broll_prompt,
            "voiceover": sc.spoken_voiceover,
            "on_screen_text": sc.on_screen_text,
        })

    return {
        "title": f"{account.name} — {narrative.target_emotion} ({reel.duration_seconds}s Reel)",
        "duration_seconds": reel.duration_seconds,
        "aspect_ratio": "9:16",
        "target_audience": narrative.cohort_name,
        "target_emotion": narrative.target_emotion,
        "vids_launcher_url": "https://vids.new",
        "google_vids_prompt": prompt,
        "markdown_storyboard": markdown,
        "scenes": scenes_data,
        "music_mood": reel.music_mood,
        "call_to_action": narrative.call_to_action,
    }
