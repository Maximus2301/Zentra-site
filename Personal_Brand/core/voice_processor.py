"""
Voice Processor and Linguistic DNA Extractor.
Transcribes Telegram voice notes via local Whisper-tiny and extracts creator cadence/voice vectors.
"""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict
import imageio_ffmpeg
from transformers import pipeline

logger = logging.getLogger("personal_brand.voice_processor")

_ASR_PIPELINE = None


def get_asr_pipeline():
    """Lazy loader for cached Whisper-tiny pipeline."""
    global _ASR_PIPELINE
    if _ASR_PIPELINE is None:
        logger.info("Loading cached whisper-tiny ASR pipeline...")
        _ASR_PIPELINE = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-tiny",
            device="cpu",
        )
    return _ASR_PIPELINE


def convert_audio_to_wav(input_path: Path, output_path: Path) -> bool:
    """Converts audio (e.g. OGG/Opus from Telegram) to 16kHz mono WAV via bundled FFmpeg."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", str(input_path),
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        str(output_path),
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return output_path.exists()
    except Exception as e:
        logger.error(f"FFmpeg conversion failed: {e}")
        return False


def transcribe_voice_note(audio_path: Path) -> str:
    """
    Transcribes audio file to text using local Whisper.
    Handles Telegram OGA/OGG formats seamlessly.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        wav_path = Path(tmp_wav.name)

    try:
        success = convert_audio_to_wav(audio_path, wav_path)
        if not success:
            raise RuntimeError("Audio format conversion to WAV failed.")

        asr = get_asr_pipeline()
        result = asr(str(wav_path))
        text = result.get("text", "").strip()
        return text
    finally:
        if wav_path.exists():
            try:
                wav_path.unlink()
            except Exception:
                pass


def extract_voice_dna(transcript: str) -> Dict[str, Any]:
    """
    Extracts tone, cadence, and linguistic features from a voice transcript.
    """
    clean_text = transcript.strip()
    words = clean_text.split()
    sentences = [s.strip() for s in clean_text.replace("!", ".").replace("?", ".").split(".") if s.strip()]

    word_count = len(words)
    sentence_count = max(1, len(sentences))
    avg_sentence_len = round(word_count / sentence_count, 1)

    # Detect cadence
    if avg_sentence_len <= 10:
        cadence = "Ultra-punchy and direct. Short, rapid statements with high velocity."
    elif avg_sentence_len <= 18:
        cadence = "Conversational and structured. Balanced pacing with clear takeaways."
    else:
        cadence = "Detailed, expository, and explanatory. Deep narrative flow."

    # First-person vs observational perspective detection (domain-neutral)
    first_person_words = {"i", "we", "my", "our", "me", "personally", "experienced", "learned"}
    fp_count = sum(1 for w in words if w.lower().strip(".,!?") in first_person_words)
    is_first_person = (fp_count / max(1, word_count)) > 0.04

    perspective = (
        "First-person authentic storyteller ('In my experience', 'Here is what worked for me')"
        if is_first_person
        else "Clear, direct domain educator and observer"
    )

    # Attempt AI-powered Voice DNA extraction if free-tier LLM is available
    try:
        from pydantic import BaseModel
        from .llm_client import call_structured_llm, has_llm_provider

        if has_llm_provider() and word_count >= 5:
            class _VoiceDNA(BaseModel):
                archetype: str
                cadence: str
                perspective: str
                tone_attributes: list[str]
                encouraged_words: list[str]
                forbidden_words: list[str]

            extracted = call_structured_llm(
                prompt=f"Analyze this creator's authentic speaking/writing sample and extract their Voice DNA:\n\n\"{clean_text}\"",
                system_instruction=(
                    "You are a brand voice linguist. Extract the speaker's natural archetype (without assuming tech unless they mention tech), "
                    "sentence cadence, perspective, 3-4 tone attributes, and natural vocabulary patterns."
                ),
                response_schema=_VoiceDNA,
                temperature=0.4,
            )
            return {
                "voice_sample_transcript": clean_text,
                "archetype": extracted.archetype,
                "cadence": extracted.cadence,
                "perspective": extracted.perspective,
                "average_sentence_length": avg_sentence_len,
                "extracted_attributes": extracted.tone_attributes,
                "encouraged_words": extracted.encouraged_words,
                "forbidden_words": extracted.forbidden_words,
            }
    except Exception as e:
        logger.debug(f"LLM voice DNA extraction skipped ({e}); using statistical analysis.")

    return {
        "voice_sample_transcript": clean_text,
        "archetype": "Authentic Domain Creator",
        "cadence": cadence,
        "perspective": perspective,
        "average_sentence_length": avg_sentence_len,
        "extracted_attributes": [
            "Natural conversational rhythm",
            cadence,
            perspective,
            "Grounded in real-world observations",
        ],
    }
