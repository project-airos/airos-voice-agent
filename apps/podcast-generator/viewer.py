#!/usr/bin/env python3
"""
Viewer - Monitor podcast generation pipeline in real-time
Color-coded output for different nodes and events
"""
import json
import time
import sys
from dora import Node


def colorize(text, color_code):
    """Add ANSI color codes to text if output is a TTY."""
    if sys.stdout.isatty():
        return f"\033[{color_code}m{text}\033[0m"
    return text


def format_timestamp():
    """Get current timestamp for logging."""
    return time.strftime("%H:%M:%S.%f")[:-3]


def main():
    print("=" * 70)
    print(colorize("🎙️  Podcast Generator Viewer", "36"))
    print("=" * 70)
    print("Monitoring pipeline events...\n")

    node = Node("viewer")

    for event in node:
        if event["type"] == "INPUT":
            event_id = event["id"]

            # Handle log events
            if event_id in ["segmenter_log", "daniu_log", "yifan_log", "output_log"]:
                try:
                    raw_value = event.get("value")
                    if raw_value and len(raw_value) > 0:
                        log_data = json.loads(raw_value[0].as_py())

                        level = log_data.get("level", "INFO")
                        message = log_data.get("message", "")
                        node_name = log_data.get("node", "unknown")

                        # Color code by level
                        level_colors = {
                            "DEBUG": "90",  # Bright black
                            "INFO": "36",    # Cyan
                            "WARNING": "93", # Bright yellow
                            "ERROR": "91",   # Bright red
                        }

                        color = level_colors.get(level, "37")  # Default white

                        # Add emoji based on node
                        node_icons = {
                            "script-segmenter": "📝 Script Segmenter",
                            "primespeech-daniu": "🎤 大牛",
                            "primespeech-yifan": "🎙️ 一帆",
                            "voice-output": "🔊 Voice Output",
                        }

                        icon = node_icons.get(node_name, f"  {node_name}")

                        # Format output
                        timestamp = format_timestamp()
                        formatted = f"[{timestamp}] {icon}: {colorize(message, color)}"

                        print(formatted)
                        sys.stdout.flush()

                except Exception as e:
                    print(f"Error parsing log: {e}")

            # Handle text events
            elif event_id in ["daniu_text", "yifan_text"]:
                try:
                    raw_value = event.get("value")
                    if raw_value and len(raw_value) > 0:
                        text = raw_value[0].as_py()

                        if event_id == "daniu_text":
                            icon = "🎤 大牛"
                            color_code = "35"  # Magenta
                        else:
                            icon = "🎙️ 一帆"
                            color_code = "34"  # Blue

                        timestamp = format_timestamp()
                        formatted = f"[{timestamp}] {colorize(icon, color_code)}: {text}"
                        print(formatted)
                        sys.stdout.flush()

                except Exception as e:
                    print(f"Error parsing text: {e}")

            # Handle completion
            elif event_id == "script_complete":
                timestamp = format_timestamp()
                completion_msg = colorize("✅ PODCAST GENERATION COMPLETE!", "92")
                print(f"\n[{timestamp}] {completion_msg}")
                print("=" * 70)
                sys.stdout.flush()
                break


if __name__ == "__main__":
    main()
