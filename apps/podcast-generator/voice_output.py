#!/usr/bin/env python3
"""
Voice Output - Concatenate audio with silence padding
Adds random 1-3 seconds of silence when speaker changes
"""
import argparse
import json
import os
import time
import random
from collections import defaultdict
from typing import Dict, List, Optional
from dora import Node
import numpy as np
from scipy.io import wavfile
import pyarrow as pa


def send_log(node, level, message, config_level="INFO"):
    """Send log message through log output channel."""
    LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}

    if LOG_LEVELS.get(level, 0) < LOG_LEVELS.get(config_level, 20):
        return

    formatted_message = f"[{level}] {message}"
    log_data = {
        "node": "voice-output",
        "level": level,
        "message": formatted_message,
        "timestamp": time.time()
    }
    node.send_output("log", pa.array([json.dumps(log_data)]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-file', required=True, help='Path to output WAV file')
    args = parser.parse_args()

    node = Node("voice-output")
    log_level = "INFO"

    # Configuration
    # "Segment" = one incoming text payload; MiniMax streams each segment as
    # multiple audio "fragments". fragment_num == 1 marks the start of a new
    # segment and is the moment to inject speaker-switch silence.
    sample_rate = 32000  # PrimeSpeech default (32 kHz, not 24 kHz!)
    silence_min = 0.5  # minimum silence in seconds
    silence_max = 3.0  # maximum silence in seconds

    # State
    final_audio_chunks: List[np.ndarray] = []
    segment_audio: Dict[int, List[np.ndarray]] = defaultdict(list)
    segment_speakers: Dict[int, str] = {}
    segment_sample_rates: Dict[int, int] = {}
    completed_segments: set[int] = set()
    next_segment_to_write = 0
    last_output_speaker: Optional[str] = None
    output_sample_rate = sample_rate

    def convert_to_int16(array: np.ndarray) -> np.ndarray:
        """Normalize incoming audio arrays to int16."""
        if array.dtype == np.int16:
            return array

        if array.dtype in (np.float32, np.float64):
            safe = np.clip(array, -1.0, 1.0)
            return (safe * 32767).astype(np.int16)

        send_log(
            node,
            "WARNING",
            f"Unknown audio dtype {array.dtype}, casting to int16. Audio artifacts possible.",
            log_level,
        )
        return array.astype(np.int16)

    def flush_ready_segments() -> None:
        """Write any completed segments to the final buffer in order."""
        nonlocal next_segment_to_write, last_output_speaker, output_sample_rate

        while next_segment_to_write in completed_segments:
            speaker = segment_speakers.get(next_segment_to_write)
            chunks = segment_audio.get(next_segment_to_write, [])

            if not chunks:
                send_log(
                    node,
                    "WARNING",
                    f"Segment {next_segment_to_write} marked complete but has no audio. Skipping.",
                    log_level,
                )
                completed_segments.remove(next_segment_to_write)
                segment_speakers.pop(next_segment_to_write, None)
                segment_sample_rates.pop(next_segment_to_write, None)
                next_segment_to_write += 1
                continue

            segment_data = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
            segment_data = convert_to_int16(segment_data)

            segment_rate = segment_sample_rates.get(next_segment_to_write, output_sample_rate)
            if segment_rate != output_sample_rate and not final_audio_chunks:
                output_sample_rate = segment_rate
                send_log(
                    node,
                    "INFO",
                    f"Adopting sample rate {output_sample_rate} Hz from first segment.",
                    log_level,
                )
            elif segment_rate != output_sample_rate:
                send_log(
                    node,
                    "WARNING",
                    f"Segment {next_segment_to_write} sample rate {segment_rate} "
                    f"differs from output {output_sample_rate}. Resampling not supported.",
                    log_level,
                )

            if last_output_speaker is not None and speaker and speaker != last_output_speaker:
                silence_duration = random.uniform(silence_min, silence_max)
                silence_samples = int(output_sample_rate * silence_duration)
                silence = np.zeros(silence_samples, dtype=np.int16)
                final_audio_chunks.append(silence)
                send_log(
                    node,
                    "INFO",
                    f"Inserted {silence_duration:.2f}s silence ({last_output_speaker} → {speaker})",
                    log_level,
                )

            final_audio_chunks.append(segment_data)
            last_output_speaker = speaker or last_output_speaker

            # Cleanup
            completed_segments.remove(next_segment_to_write)
            segment_audio.pop(next_segment_to_write, None)
            segment_speakers.pop(next_segment_to_write, None)
            segment_sample_rates.pop(next_segment_to_write, None)
            next_segment_to_write += 1

    def handle_audio_event(event, speaker_label: str) -> None:
        """Process incoming audio fragments for a speaker."""
        metadata = event.get("metadata", {})
        segment_index = metadata.get("segment_index")

        raw_value = event.get("value")
        if not raw_value or len(raw_value) == 0:
            send_log(node, "WARNING", f"No audio payload for {speaker_label}", log_level)
            return

        audio_data = raw_value[0].as_py()
        if not isinstance(audio_data, np.ndarray):
            audio_data = np.array(audio_data, dtype=np.float32)

        audio_data = convert_to_int16(audio_data)

        if segment_index is None:
            send_log(
                node,
                "ERROR",
                f"{speaker_label} audio missing segment_index metadata; "
                "appending directly may break ordering.",
                log_level,
            )
            final_audio_chunks.append(audio_data)
            return

        fragment_num = metadata.get("fragment_num")
        segment_audio[segment_index].append(audio_data)
        segment_speakers.setdefault(segment_index, speaker_label)

        sample_hint = metadata.get("sample_rate")
        if sample_hint is not None:
            segment_sample_rates.setdefault(segment_index, int(sample_hint))
        else:
            segment_sample_rates.setdefault(segment_index, output_sample_rate)

        send_log(
            node,
            "DEBUG",
            f"Buffered {speaker_label} segment {segment_index} fragment "
            f"{fragment_num if fragment_num is not None else '?'} "
            f"(len={len(audio_data)})",
            log_level,
        )

    def resolve_missing_segment_index(speaker_label: str) -> Optional[int]:
        """Heuristic fallback when segment_complete arrives without metadata."""
        candidates = sorted(
            idx for idx, label in segment_speakers.items()
            if label == speaker_label and idx not in completed_segments
        )
        return candidates[0] if candidates else None

    send_log(node, "INFO", f"Voice Output initialized. Output: {args.output_file}", log_level)
    send_log(node, "INFO", f"Sample rate: {sample_rate} Hz, Silence: {silence_min}-{silence_max}s (random)", log_level)
    send_log(node, "INFO", "Entering event loop, waiting for audio...", log_level)

    # Event loop
    for event in node:
        send_log(node, "DEBUG", f"Received event type: {event['type']}", log_level)

        if event["type"] == "INPUT":
            event_id = event["id"]
            send_log(node, "DEBUG", f"Processing INPUT: {event_id}", log_level)

            if event_id == "daniu_audio":
                send_log(node, "DEBUG", ">>> Received daniu_audio event", log_level)
                try:
                    handle_audio_event(event, "大牛")
                except Exception as exc:
                    send_log(node, "ERROR", f"Error processing 大牛 audio: {exc}", log_level)
                    raise

            elif event_id == "yifan_audio":
                send_log(node, "DEBUG", ">>> Received yifan_audio event", log_level)
                try:
                    handle_audio_event(event, "一帆")
                except Exception as exc:
                    send_log(node, "ERROR", f"Error processing 一帆 audio: {exc}", log_level)
                    raise

            elif event_id == "daniu_segment_complete":
                metadata = event.get("metadata", {})
                segment_index = metadata.get("segment_index")

                if segment_index is None:
                    segment_index = resolve_missing_segment_index("大牛")
                    send_log(
                        node,
                        "WARNING",
                        f"daniu_segment_complete missing segment_index. "
                        f"Heuristic resolved to {segment_index}.",
                        log_level,
                    )

                if segment_index is None:
                    send_log(node, "ERROR", "Unable to resolve segment for 大牛 completion.", log_level)
                else:
                    completed_segments.add(segment_index)
                    send_log(node, "DEBUG", f"Marked segment {segment_index} complete for 大牛", log_level)
                    flush_ready_segments()

            elif event_id == "yifan_segment_complete":
                metadata = event.get("metadata", {})
                segment_index = metadata.get("segment_index")

                if segment_index is None:
                    segment_index = resolve_missing_segment_index("一帆")
                    send_log(
                        node,
                        "WARNING",
                        f"yifan_segment_complete missing segment_index. "
                        f"Heuristic resolved to {segment_index}.",
                        log_level,
                    )

                if segment_index is None:
                    send_log(node, "ERROR", "Unable to resolve segment for 一帆 completion.", log_level)
                else:
                    completed_segments.add(segment_index)
                    send_log(node, "DEBUG", f"Marked segment {segment_index} complete for 一帆", log_level)
                    flush_ready_segments()

            elif event_id == "script_complete":
                flush_ready_segments()

                if segment_audio or completed_segments:
                    send_log(
                        node,
                        "WARNING",
                        "script_complete received but some segments are still buffered. "
                        f"pending_audio={list(segment_audio.keys())}, "
                        f"completed={sorted(completed_segments)}",
                        log_level,
                    )

                send_log(node, "INFO", "Received script_complete, finalizing WAV file...", log_level)

                # Concatenate all audio
                if final_audio_chunks:
                    send_log(node, "INFO", f"Concatenating {len(final_audio_chunks)} audio chunks...", log_level)
                    final_audio = np.concatenate(final_audio_chunks)

                    # Write WAV file
                    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
                    wavfile.write(args.output_file, output_sample_rate, final_audio)

                    duration = len(final_audio) / output_sample_rate
                    send_log(node, "INFO", f"Podcast saved: {args.output_file} ({duration:.2f}s)", log_level)
                    send_log(node, "INFO", "✅ PODCAST GENERATION COMPLETE!", log_level)
                else:
                    send_log(node, "WARNING", "No audio data received, nothing to write", log_level)

                # Exit after completion
                break

    send_log(node, "INFO", "Voice Output shutting down", log_level)


if __name__ == "__main__":
    main()
