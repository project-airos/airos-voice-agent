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
from typing import List, Tuple, Iterable
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


def parse_markdown(filename: str, node=None, log_level="INFO") -> Tuple[List[str], List[str]]:
    """Parse markdown file and extract speaker segments.

    Args:
        filename: Path to markdown file
        node: Dora node for logging (optional)
        log_level: Log level for filtering

    Returns:
        Tuple of (daniu_segments, yifan_segments) as lists of strings

    Format:
    【大牛】Text spoken by Daniu using Luo Xiang voice.
    【一帆】Text spoken by Yifan using Doubao voice.
    """
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    daniu_segments = []
    yifan_segments = []
    current_speaker = None
    current_text = ""

    lines = content.split('\n')

    for line in lines:
        # Match speaker tags: 【大牛】 or **【大牛】** or 【一帆】 or **【一帆】**
        match = re.match(r'\**【(大牛|一帆)】\**\s*(.*)', line.strip())
        if match:
            # Save previous speaker's text
            if current_speaker and current_text.strip():
                if current_speaker == '大牛':
                    daniu_segments.append(current_text.strip())
                else:
                    yifan_segments.append(current_text.strip())

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
        if current_speaker == '大牛':
            daniu_segments.append(current_text.strip())
        else:
            yifan_segments.append(current_text.strip())

    if node:
        send_log(node, "INFO", f"Parsed {len(daniu_segments)} segments from 大牛, {len(yifan_segments)} segments from 一帆", log_level)

    return daniu_segments, yifan_segments


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

    # Parse markdown
    daniu_segments, yifan_segments = parse_markdown(args.input_file, node, args.log_level)

    # Apply text segmentation to long passages
    daniu_chunks = []
    for segment in daniu_segments:
        chunks = split_long_text(segment, max_length, punctuation_marks, node, args.log_level)
        daniu_chunks.extend(chunks)

    yifan_chunks = []
    for segment in yifan_segments:
        chunks = split_long_text(segment, max_length, punctuation_marks, node, args.log_level)
        yifan_chunks.extend(chunks)

    send_log(node, "INFO", f"After text segmentation: {len(daniu_chunks)} total segments to process", args.log_level)

    # Send segments sequentially, waiting for completion signals
    daniu_idx = 0
    yifan_idx = 0

    for event in node:
        if event["type"] == "INPUT":
            # Check for segment completion signals
            if event["id"] == "daniu_segment_complete":
                send_log(node, "DEBUG", "Received daniu_segment_complete", args.log_level)
                if daniu_idx < len(daniu_chunks):
                    segment = daniu_chunks[daniu_idx]
                    send_log(node, "INFO", f"大牛: {segment}", args.log_level)
                    node.send_output("daniu_text", pa.array([segment]))
                    daniu_idx += 1
                else:
                    send_log(node, "DEBUG", "All daniu segments sent", args.log_level)

            elif event["id"] == "yifan_segment_complete":
                send_log(node, "DEBUG", "Received yifan_segment_complete", args.log_level)
                if yifan_idx < len(yifan_chunks):
                    segment = yifan_chunks[yifan_idx]
                    send_log(node, "INFO", f"一帆: {segment}", args.log_level)
                    node.send_output("yifan_text", pa.array([segment]))
                    yifan_idx += 1
                else:
                    send_log(node, "DEBUG", "All yifan segments sent", args.log_level)

    # Check if all segments are done and send completion signal
    if daniu_idx >= len(daniu_chunks) and yifan_idx >= len(yifan_chunks):
        send_log(node, "INFO", "All segments processed. Sending script_complete.", args.log_level)
        node.send_output("script_complete", pa.array([True]))


if __name__ == "__main__":
    main()
