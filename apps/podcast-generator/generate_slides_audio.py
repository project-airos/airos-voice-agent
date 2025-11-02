#!/usr/bin/env python3
"""
Generate slide-by-slide audio tracks using the MiniMax TTS service.

This script reads a markdown file that contains Reveal.js-style slide sections
with YAML front matter. For each slide it:

1. Resolves speaker defaults (voice, pace, etc.) from the front matter.
2. Synthesizes one audio track per speaker segment via MiniMax TTS.
3. Saves individual speaker files (e.g., slide-01_host.wav) and a combined
   slide mix (e.g., slide-01.wav) that concatenates the segments in order.

Example:
    ./generate_slides_audio.py --script-file sample_scripts_for_slides.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shlex
import ssl
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
    sys.stderr.write(
        "Missing dependency: PyYAML is required (pip install pyyaml).\n"
    )
    raise

try:
    import websockets
except ModuleNotFoundError:  # pragma: no cover - optional dependency for dry-run
    websockets = None


@dataclass
class SpeakerSettings:
    """Resolved speaker defaults."""

    speaker_id: str
    voice_id: str
    display_name: str
    default_speed: float
    default_volume: float
    default_pitch: int
    default_style: Optional[str] = None


@dataclass
class SlideSegment:
    """Single script segment for a slide."""

    speaker: str
    text: str
    overrides: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SlideScript:
    """Slide metadata including ordered segments."""

    index: int
    title: str
    raw_heading: str
    segments: List[SlideSegment]


def parse_env_file(path: Path) -> Dict[str, str]:
    """Parse a simple .env file into a dictionary without exporting values."""
    env: Dict[str, str] = {}
    if not path.is_file():
        return env

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if value:
            lexer = shlex.shlex(value, posix=True)
            lexer.whitespace_split = True
            tokens = list(lexer)
            if tokens:
                value = tokens[0]
        env[key] = value
    return env


def load_env_overrides() -> Dict[str, str]:
    """
    Load env vars from .env files in the script directory and repository root.

    Values do not override already-set environment variables.
    """
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir.parent / ".env",
        script_dir / ".env",
    ]
    merged: Dict[str, str] = {}
    for candidate in candidates:
        merged.update(parse_env_file(candidate))

    for key, value in merged.items():
        if key not in os.environ:
            os.environ[key] = value
    return merged


_ENV_OVERRIDES = load_env_overrides()

MINIMAX_VOICE_ALIASES: Dict[str, str] = {
    # Friendly identifiers mapped to MiniMax production voice IDs.
    "minimax:cn_female_002": "moss_audio_9c223de9-7ce1-11f0-9b9f-463feaa3106a",
    "cn_female_002": "moss_audio_9c223de9-7ce1-11f0-9b9f-463feaa3106a",
    "minimax:cn_male_001": "moss_audio_aaa1346a-7ce7-11f0-8e61-2e6e3c7ee85d",
    "cn_male_001": "moss_audio_aaa1346a-7ce7-11f0-8e61-2e6e3c7ee85d",
}


def normalize_audio_format(raw_format: str) -> Tuple[str, Optional[str]]:
    """
    Normalize audio format values to MiniMax-supported settings.

    Returns (normalized_format, warning_message_or_None).
    """
    fmt = (raw_format or "").strip().lower()
    if fmt in {"", "pcm", "pcm_s16le", "linear_pcm"}:
        return "pcm", None
    if fmt in {"wav", "wave"}:
        return "pcm", "Audio format 'wav' is not supported by MiniMax API; using 'pcm' instead."
    if fmt in {"mp3", "ogg", "aac"}:
        return fmt, None  # MiniMax may reject unsupported codecs; pass through.
    # Default fallback.
    return "pcm", f"Unknown audio format '{raw_format}' - defaulting to 'pcm'."


def resolve_voice_id(raw_voice_id: str, speaker_id: str) -> str:
    """Normalize friendly voice identifiers into MiniMax voice IDs."""
    if not raw_voice_id:
        raise ValueError(f"Speaker '{speaker_id}' is missing a voice_id.")

    voice_key = raw_voice_id.strip()
    alias = MINIMAX_VOICE_ALIASES.get(voice_key)
    if alias:
        return alias

    lower_key = voice_key.lower()
    alias = MINIMAX_VOICE_ALIASES.get(lower_key)
    if alias:
        return alias

    if ":" in voice_key:
        tail = voice_key.split(":", 1)[1]
        alias = MINIMAX_VOICE_ALIASES.get(tail) or MINIMAX_VOICE_ALIASES.get(tail.lower())
        if alias:
            return alias

    return voice_key


class MiniMaxTTSClient:
    """Thin wrapper around the MiniMax WebSocket API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        sample_rate: int,
        audio_format: str,
        bitrate: int,
        channels: int,
        english_normalization: bool,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.sample_rate = sample_rate
        self.audio_format = audio_format
        self.bitrate = bitrate
        self.channels = channels
        self.english_normalization = english_normalization
        self.url = "wss://api.minimax.io/ws/v1/t2a_v2"

    async def synthesize(
        self,
        *,
        text: str,
        voice_id: str,
        speed: float,
        volume: float,
        pitch: int,
    ) -> Tuple[bytes, int]:
        """Synthesize text to PCM audio."""
        if websockets is None:
            raise ModuleNotFoundError(
                "websockets package is required to call the MiniMax TTS API. "
                "Install it via 'pip install websockets'."
            )

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with websockets.connect(self.url, additional_headers=headers, ssl=ssl_context) as ws:
            connected = json.loads(await ws.recv())
            if connected.get("event") != "connected_success":
                raise RuntimeError(f"Failed to connect to MiniMax TTS: {connected}")

            start_msg = {
                "event": "task_start",
                "model": self.model,
                "voice_setting": {
                    "voice_id": voice_id,
                    "speed": speed,
                    "vol": volume,
                    "pitch": pitch,
                    "english_normalization": self.english_normalization,
                },
                "audio_setting": {
                    "sample_rate": self.sample_rate,
                    "bitrate": self.bitrate,
                    "format": self.audio_format,
                    "channel": self.channels,
                },
            }
            await ws.send(json.dumps(start_msg))

            started = json.loads(await ws.recv())
            if started.get("event") != "task_started":
                raise RuntimeError(f"Failed to start MiniMax task: {started}")

            await ws.send(json.dumps({"event": "task_continue", "text": text}))

            audio_chunks: List[bytes] = []
            while True:
                response = json.loads(await ws.recv())
                data = response.get("data")
                if data and "audio" in data:
                    audio_hex = data["audio"]
                    if audio_hex:
                        audio_chunks.append(bytes.fromhex(audio_hex))

                if response.get("is_final"):
                    break

                if response.get("event") == "task_failed":
                    raise RuntimeError(f"MiniMax synthesis failed: {response}")

            await ws.send(json.dumps({"event": "task_finish"}))

        return b"".join(audio_chunks), self.sample_rate


def parse_front_matter(text: str) -> Tuple[Dict[str, Any], str]:
    """Extract YAML front matter and return (front_matter, remaining_markdown)."""
    if not text.startswith("---"):
        return {}, text

    sentinel = "\n---"
    closing_idx = text.find(sentinel, 4)
    if closing_idx == -1:
        raise ValueError("Front matter opening '---' found but no closing '---'.")

    fm_body = text[4:closing_idx]
    remainder = text[closing_idx + len(sentinel):]

    front_matter = yaml.safe_load(fm_body) or {}
    return front_matter, remainder.lstrip("\n")


def parse_slide_sections(markdown: str) -> List[Tuple[str, List[str]]]:
    """
    Split markdown into (heading, lines) pairs.

    Heading is a string (e.g., "Slide 01 | Intro").
    Lines contains the raw markdown describing the slide segments.
    """
    slides: List[Tuple[str, List[str]]] = []
    current_heading: Optional[str] = None
    buffer: List[str] = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip("\n")
        if line.startswith("## "):
            if current_heading is not None:
                slides.append((current_heading, buffer))
                buffer = []
            current_heading = line[3:].strip()
        else:
            buffer.append(line)

    if current_heading is not None:
        slides.append((current_heading, buffer))

    return slides


def normalize_slide_heading(heading: str, fallback_index: int) -> Tuple[int, str]:
    """Extract slide index and cleaned title from heading text."""
    import re

    match = re.search(r"slide\s*(\d+)", heading, flags=re.IGNORECASE)
    if match:
        index = int(match.group(1))
    else:
        index = fallback_index

    title_part = heading
    if "|" in heading:
        title_part = heading.split("|", 1)[1].strip()
    elif ":" in heading:
        title_part = heading.split(":", 1)[1].strip()
    else:
        title_part = heading.strip()

    return index, title_part


def parse_slide_segments(lines: Iterable[str], slide_label: str) -> List[SlideSegment]:
    """Parse markdown bullet list for a slide into structured segments."""
    block = "\n".join(line for line in lines if line.strip())
    if not block:
        return []

    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        raise ValueError(f"Failed to parse segments for slide '{slide_label}': {exc}") from exc

    if data is None:
        return []

    segments_raw: List[Dict[str, Any]]
    if isinstance(data, list):
        segments_raw = data
    else:
        raise ValueError(
            f"Expected slide '{slide_label}' segments to be a list, got {type(data).__name__}"
        )

    segments: List[SlideSegment] = []
    for entry in segments_raw:
        if not isinstance(entry, dict):
            raise ValueError(
                f"Slide '{slide_label}' segment must be a mapping, got {type(entry).__name__}"
            )
        speaker = entry.get("speaker")
        text = entry.get("text") or ""
        if not speaker:
            raise ValueError(f"Slide '{slide_label}' segment missing 'speaker'.")
        segments.append(
            SlideSegment(
                speaker=str(speaker).strip(),
                text=str(text).strip(),
                overrides={k: v for k, v in entry.items() if k not in {"speaker", "text"}},
            )
        )

    return segments


def load_slide_script(path: Path) -> Tuple[Dict[str, Any], List[SlideScript]]:
    """Load markdown script with front matter into structured slides."""
    text = path.read_text(encoding="utf-8")
    front_matter, remainder = parse_front_matter(text)
    slide_sections = parse_slide_sections(remainder)

    slides: List[SlideScript] = []
    for idx, (heading, lines) in enumerate(slide_sections, start=1):
        slide_index, slide_title = normalize_slide_heading(heading, idx)
        segments = parse_slide_segments(lines, heading)
        slides.append(
            SlideScript(
                index=slide_index,
                title=slide_title,
                raw_heading=heading,
                segments=segments,
            )
        )

    return front_matter, slides


def resolve_speaker_settings(
    front_matter: Dict[str, Any],
    global_defaults: Dict[str, Any],
) -> Dict[str, SpeakerSettings]:
    """Build speaker map from front matter data."""
    speakers_data = front_matter.get("speakers") or {}
    if not isinstance(speakers_data, dict):
        raise ValueError("Front matter 'speakers' must be a mapping.")

    default_speed = float(global_defaults.get("speed", 1.0))
    default_volume = float(global_defaults.get("volume", 1.0))
    default_pitch = int(global_defaults.get("pitch", 0))

    speakers: Dict[str, SpeakerSettings] = {}
    for speaker_id, cfg in speakers_data.items():
        if not isinstance(cfg, dict):
            raise ValueError(f"Speaker '{speaker_id}' settings must be a mapping.")
        voice_id = resolve_voice_id(cfg.get("voice_id", ""), speaker_id)
        display_name = cfg.get("display_name", speaker_id)
        speakers[speaker_id] = SpeakerSettings(
            speaker_id=speaker_id,
            voice_id=str(voice_id),
            display_name=str(display_name),
            default_speed=float(cfg.get("default_speed", default_speed)),
            default_volume=float(cfg.get("default_volume", default_volume)),
            default_pitch=int(cfg.get("default_pitch", default_pitch)),
            default_style=cfg.get("default_style"),
        )

    return speakers


PACE_PRESETS = {
    "slow": 0.85,
    "slower": 0.75,
    "slowest": 0.65,
    "normal": 1.0,
    "medium": 1.0,
    "default": 1.0,
    "fast": 1.2,
    "faster": 1.35,
    "fastest": 1.5,
}


def resolve_speed(base_speed: float, override: Optional[Any]) -> float:
    """Convert pace override into a MiniMax speed value."""
    if override is None:
        return base_speed
    if isinstance(override, (int, float)):
        return max(0.5, min(2.0, float(override)))
    preset = PACE_PRESETS.get(str(override).strip().lower())
    if preset is None:
        return base_speed
    return max(0.5, min(2.0, preset))


def write_wav(path: Path, pcm_bytes: bytes, sample_rate: int, channels: int) -> None:
    """Write PCM 16-bit audio to a WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)  # 16-bit PCM
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)


def render_slide_filename(slide_index: int, suffix: str) -> str:
    """Return normalized filename for a slide output."""
    return f"slide-{slide_index:02d}{suffix}"


async def synthesize_slide_audio(
    *,
    slide: SlideScript,
    speaker_settings: Dict[str, SpeakerSettings],
    client: MiniMaxTTSClient,
    output_dir: Path,
    channel_count: int,
    segment_gap: float,
) -> None:
    """Generate per-speaker and combined audio for a slide."""
    if not slide.segments:
        return

    print(f"[Slide {slide.index:02d}] {slide.title}")
    combined_pcm = bytearray()
    silence_chunk = b""

    if segment_gap > 0:
        silence_samples = int(client.sample_rate * segment_gap)
        silence_chunk = b"\x00\x00" * silence_samples * channel_count

    for idx, segment in enumerate(slide.segments, start=1):
        speaker_id = segment.speaker
        speaker = speaker_settings.get(speaker_id)
        if not speaker:
            raise ValueError(
                f"Slide {slide.index} references unknown speaker '{speaker_id}'."
            )

        pace_override = segment.overrides.get("pace")
        speed = resolve_speed(speaker.default_speed, pace_override)
        volume = float(segment.overrides.get("volume", speaker.default_volume))
        pitch = int(segment.overrides.get("pitch", speaker.default_pitch))

        text = segment.text.strip()
        if not text:
            continue

        pcm_bytes, sample_rate = await client.synthesize(
            text=text,
            voice_id=speaker.voice_id,
            speed=speed,
            volume=volume,
            pitch=pitch,
        )
        if sample_rate != client.sample_rate:
            raise RuntimeError(
                f"MiniMax returned sample_rate={sample_rate}, expected {client.sample_rate}"
            )

        speaker_suffix = f"_{speaker_id}"
        per_speaker_filename = render_slide_filename(slide.index, f"{speaker_suffix}.wav")
        write_wav(output_dir / per_speaker_filename, pcm_bytes, sample_rate, channel_count)
        print(
            f"    • {speaker.display_name} ({speaker_id}) → {per_speaker_filename}"
        )

        if idx > 1 and silence_chunk:
            combined_pcm.extend(silence_chunk)
        combined_pcm.extend(pcm_bytes)

    if combined_pcm:
        combined_filename = render_slide_filename(slide.index, ".wav")
        write_wav(output_dir / combined_filename, bytes(combined_pcm), client.sample_rate, channel_count)
        print(f"    • mix → {combined_filename}")


async def generate_from_script(args: argparse.Namespace) -> None:
    """Asynchronous entry point for audio generation."""
    script_path = Path(args.script_file).expanduser()
    if not script_path.exists():
        raise FileNotFoundError(f"Script file not found: {script_path}")

    front_matter, slides = load_slide_script(script_path)
    if not slides:
        raise ValueError("No slides found in the script file.")

    defaults = (front_matter.get("defaults") or {}).get("tts") or {}
    sample_rate = int(defaults.get("sample_rate", 32000))
    bitrate = int(defaults.get("bitrate", 128000))
    raw_audio_format = str(defaults.get("format", "pcm"))
    audio_format, format_warning = normalize_audio_format(raw_audio_format)
    audio_channels = int(defaults.get("channel", defaults.get("channels", 1)))
    english_normalization = bool(defaults.get("english_normalization", False))
    model = str(defaults.get("model", "speech-2.5-hd-preview"))

    speaker_config = resolve_speaker_settings(front_matter, defaults)
    if not speaker_config:
        raise ValueError("At least one speaker must be defined in the front matter.")

    output_dir = Path(args.output_dir or front_matter.get("output_dir") or "output/slides_audio")
    output_dir = output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    env_section = front_matter.get("env") or {}
    api_key = (
        args.api_key
        or front_matter.get("minimax_api_key")
        or env_section.get("MINIMAX_API_KEY")
        or os.getenv("MINIMAX_API_KEY")
    )
    if not api_key:
        raise EnvironmentError(
            "MINIMAX_API_KEY is not set. Export it or provide via --api-key."
        )

    client = MiniMaxTTSClient(
        api_key=api_key,
        model=model,
        sample_rate=sample_rate,
        audio_format=audio_format,
        bitrate=bitrate,
        channels=audio_channels,
        english_normalization=english_normalization,
    )

    for slide in slides:
        await synthesize_slide_audio(
            slide=slide,
            speaker_settings=speaker_config,
            client=client,
            output_dir=output_dir,
            channel_count=audio_channels,
            segment_gap=args.segment_gap,
        )

    if format_warning:
        print(f"⚠️  {format_warning}")
    print(f"✅ Generated audio for {len(slides)} slides in {output_dir}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Reveal.js slide audio with MiniMax TTS.")
    parser.add_argument(
        "--script-file",
        required=True,
        help="Markdown file containing YAML front matter and slide sections.",
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for generated audio files (overrides front matter output_dir).",
    )
    parser.add_argument(
        "--api-key",
        help="MiniMax API key (defaults to MINIMAX_API_KEY env variable).",
    )
    parser.add_argument(
        "--segment-gap",
        type=float,
        default=0.35,
        help="Seconds of silence inserted between speaker segments when building slide mix.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate the script without calling the MiniMax API.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    if args.dry_run:
        script_path = Path(args.script_file).expanduser()
        front_matter, slides = load_slide_script(script_path)
        speaker_config = resolve_speaker_settings(
            front_matter,
            (front_matter.get("defaults") or {}).get("tts") or {},
        )
        print(f"Front matter keys: {list(front_matter.keys())}")
        print(f"Speakers: {', '.join(speaker_config.keys())}")
        print(f"Slides: {len(slides)}")
        for slide in slides:
            print(f"  - Slide {slide.index:02d}: {slide.title} ({len(slide.segments)} segments)")
        return

    try:
        asyncio.run(generate_from_script(args))
    except KeyboardInterrupt:
        sys.stderr.write("Interrupted by user.\n")
        sys.exit(130)


if __name__ == "__main__":
    main()
