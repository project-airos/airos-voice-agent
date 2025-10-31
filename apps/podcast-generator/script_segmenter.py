#!/usr/bin/env python3
"""
Script Segmenter - Parse markdown and orchestrate TTS generation
Sends text segments sequentially to two PrimeSpeech nodes
Includes intelligent text segmentation for long passages
"""
import argparse
import json
import time
import os
import re
from typing import Iterable, List, Optional, Tuple
from dora import Node
import pyarrow as pa


def send_log(node, level, message, config_level="INFO"):
    """Send log message through log output channel."""
    LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}

    if LOG_LEVELS.get(level, 0) < LOG_LEVELS.get(config_level, 20):
        return

    formatted_message = f"[{level}] {message}"
    log_data = {
        "node": "script-segmenter",
        "level": level,
        "message": formatted_message,
        "timestamp": time.time()
    }
    node.send_output("log", pa.array([json.dumps(log_data)]))


def find_split_index(text: str, max_length: int, split_marks: Iterable[str]) -> int:
    """Find a split index at or before max_length using provided marks or whitespace.

    Copied from dora-text-segmenter for sentence-aware splitting.
    """
    if max_length <= 0:
        return -1

    limit = min(len(text), max_length)

    # Try to split at punctuation marks first
    if split_marks:
        for idx in range(limit, 0, -1):
            if text[idx - 1] in split_marks:
                return idx

    # Fall back to whitespace
    for idx in range(limit, 0, -1):
        if text[idx - 1].isspace():
            return idx

    return -1


def split_long_text(
    text: str,
    max_length: int,
    punctuation_marks: str,
    node=None,
    log_level: str = "INFO",
) -> List[str]:
    """Split long text into chunks that respect sentence boundaries.

    Args:
        text: Text to split
        max_length: Maximum characters per segment
        punctuation_marks: String of punctuation marks for splitting
        node: Dora node for logging (optional)
        log_level: Log level for filtering

    Returns:
        List of text segments (all <= max_length if possible)
    """
    if max_length <= 0 or len(text) <= max_length:
        return [text]

    # Build split marks from punctuation
    split_marks = set(punctuation_marks)

    chunks: List[str] = []
    remainder = text

    if node:
        send_log(
            node,
            "DEBUG",
            f"Splitting long text (len={len(text)}) with max={max_length} chars",
            log_level,
        )

    while remainder:
        if len(remainder) <= max_length:
            chunks.append(remainder)
            break

        # Find best split point
        split_idx = find_split_index(remainder, max_length, split_marks)

        if split_idx > 0:
            chunks.append(remainder[:split_idx].strip())
            remainder = remainder[split_idx:].strip()
        else:
            # No good split point found, force split at max_length
            chunks.append(remainder[:max_length].strip())
            remainder = remainder[max_length:].strip()

        if node and chunks:
            send_log(
                node,
                "DEBUG",
                f"Created chunk {len(chunks)}: {chunks[-1][:50]}...",
                log_level,
            )

    return chunks


def parse_markdown(filename: str, node=None, log_level="INFO") -> List[Tuple[str, str]]:
    """Parse markdown file and extract ordered speaker segments.

    Args:
        filename: Path to markdown file
        node: Dora node for logging (optional)
        log_level: Log level for filtering

    Returns:
        List of (speaker, text) tuples where speaker is "daniu" or "yifan".

    Format in markdown:
    【大牛】Text spoken by Daniu using Luo Xiang voice.
    【一帆】Text spoken by Yifan using Doubao voice.
    """
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    segments: List[Tuple[str, str]] = []
    current_speaker = None
    current_text = ""

    lines = content.split('\n')

    for line in lines:
        # Match speaker tags: 【大牛】 or **【大牛】** or 【一帆】 or **【一帆】**
        match = re.match(r'\**【(大牛|一帆)】\**\s*(.*)', line.strip())
        if match:
            # Save previous speaker's text
            if current_speaker and current_text.strip():
                speaker_key = "daniu" if current_speaker == '大牛' else "yifan"
                segments.append((speaker_key, current_text.strip()))

            # Start new speaker
            current_speaker = match.group(1)
            current_text = match.group(2) if match.group(2) else ""
        else:
            # Accumulate text for current speaker
            if current_speaker:
                if line.strip():  # Skip empty lines
                    current_text += " " + line.strip()

    # Don't forget the last speaker
    if current_speaker and current_text.strip():
        speaker_key = "daniu" if current_speaker == '大牛' else "yifan"
        segments.append((speaker_key, current_text.strip()))

    if node:
        daniu_count = sum(1 for speaker, _ in segments if speaker == "daniu")
        yifan_count = sum(1 for speaker, _ in segments if speaker == "yifan")
        send_log(
            node,
            "INFO",
            f"Parsed {daniu_count} segments from 大牛, {yifan_count} segments from 一帆",
            log_level,
        )

    return segments


def main():
    parser = argparse.ArgumentParser(description='Parse markdown and send segments to TTS')
    parser.add_argument('--input-file', required=True, help='Path to markdown script')
    parser.add_argument('--log-level', default='INFO', help='Logging level (DEBUG, INFO, WARNING, ERROR)')
    args = parser.parse_args()

    node = Node("script-segmenter")

    send_log(node, "INFO", "Script Segmenter started", args.log_level)

    # Text segmentation configuration
    # Convert max duration to character count
    max_duration = float(os.environ.get('MAX_SEGMENT_DURATION', '10.0'))  # seconds
    chars_per_second = float(os.environ.get('TTS_CHARS_PER_SECOND', '4.5'))  # Chinese chars/sec
    max_length = int(max_duration * chars_per_second)

    punctuation_marks = os.environ.get('PUNCTUATION_MARKS', '。！？.!?，,、；;:')

    send_log(node, "INFO", f"Text segmentation config: max_duration={max_duration}s, chars_per_second={chars_per_second}, max_length={max_length} chars", args.log_level)

    # Parse markdown and keep segments in script order
    ordered_segments = parse_markdown(args.input_file, node, args.log_level)

    # Apply text segmentation to long passages while preserving order
    ordered_chunks: List[Tuple[str, str]] = []
    daniu_total = 0
    yifan_total = 0

    for speaker, segment in ordered_segments:
        chunks = split_long_text(segment, max_length, punctuation_marks, node, args.log_level)
        for chunk in chunks:
            ordered_chunks.append((speaker, chunk))
            if speaker == "daniu":
                daniu_total += 1
            else:
                yifan_total += 1

    send_log(
        node,
        "INFO",
        f"After text segmentation: {len(ordered_chunks)} total segments "
        f"(大牛: {daniu_total}, 一帆: {yifan_total})",
        args.log_level,
    )

    total_segments = len(ordered_chunks)
    next_segment_idx = 0
    completed_segments = 0
    daniu_completed = 0
    yifan_completed = 0
    active_speaker: Optional[str] = None

    def send_next_segment() -> bool:
        """Send the next segment in script order if no segment is active."""
        nonlocal next_segment_idx, active_speaker

        if active_speaker is not None:
            return False

        if next_segment_idx >= total_segments:
            return False

        speaker, segment = ordered_chunks[next_segment_idx]
        next_segment_idx += 1
        active_speaker = speaker

        if speaker == "daniu":
            send_log(node, "INFO", f"大牛: {segment}", args.log_level)
            node.send_output("daniu_text", pa.array([segment]))
        else:
            send_log(node, "INFO", f"一帆: {segment}", args.log_level)
            node.send_output("yifan_text", pa.array([segment]))

        return True

    def all_segments_sent() -> bool:
        return next_segment_idx >= total_segments

    def all_segments_completed() -> bool:
        return completed_segments >= total_segments

    def finalize_script() -> None:
        send_log(node, "INFO", "All segments processed. Sending script_complete.", args.log_level)
        node.send_output("script_complete", pa.array([True]))

    # Prime the pipeline with the first segment (if any)
    initial_segment_sent = send_next_segment()

    if not initial_segment_sent and total_segments == 0:
        finalize_script()
        return

    script_complete_sent = False

    for event in node:
        event_type = event.get("type")

        if event_type == "STOP":
            send_log(node, "INFO", "Received STOP event, terminating.", args.log_level)
            break

        if event_type != "INPUT":
            continue

        event_id = event.get("id")

        if event_id == "daniu_segment_complete":
            send_log(node, "DEBUG", "Received daniu_segment_complete", args.log_level)
            daniu_completed += 1

            if active_speaker != "daniu":
                send_log(
                    node,
                    "WARNING",
                    "Received daniu_segment_complete without matching active segment.",
                    args.log_level,
                )
            else:
                active_speaker = None
                completed_segments += 1

            send_next_segment()

            if not script_complete_sent and all_segments_sent() and all_segments_completed():
                finalize_script()
                script_complete_sent = True
                break

        elif event_id == "yifan_segment_complete":
            send_log(node, "DEBUG", "Received yifan_segment_complete", args.log_level)
            yifan_completed += 1

            if active_speaker != "yifan":
                send_log(
                    node,
                    "WARNING",
                    "Received yifan_segment_complete without matching active segment.",
                    args.log_level,
                )
            else:
                active_speaker = None
                completed_segments += 1

            send_next_segment()

            if not script_complete_sent and all_segments_sent() and all_segments_completed():
                finalize_script()
                script_complete_sent = True
                break

    if not script_complete_sent and all_segments_completed():
        finalize_script()


if __name__ == "__main__":
    main()
