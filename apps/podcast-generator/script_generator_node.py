#!/usr/bin/env python3
"""
Script Generator Node - Dora node version
Generates podcast scripts using LLM and outputs to the dataflow
"""
import argparse
import json
import time
import os
from typing import Optional
from dora import Node
import pyarrow as pa
import openai
import anthropic


def send_log(node, level, message, config_level="INFO"):
    """Send log message through log output channel."""
    LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}

    if LOG_LEVELS.get(level, 0) < LOG_LEVELS.get(config_level, 20):
        return

    formatted_message = f"[{level}] {message}"
    log_data = {
        "node": "script-generator",
        "level": level,
        "message": formatted_message,
        "timestamp": time.time()
    }
    node.send_output("log", pa.array([json.dumps(log_data)]))


def generate_script_with_openai(topic: str, api_key: str, duration_minutes: int) -> str:
    """Generate podcast script using OpenAI API."""
    client = openai.OpenAI(api_key=api_key)

    prompt = f"""
Generate a podcast script about "{topic}".

Requirements:
- Format: Dialogue between two speakers: 【大牛】 and 【一帆】
- Duration: Approximately {duration_minutes} minutes when spoken
- Language: Chinese (Simplified)
- Style: Conversational, educational, engaging
- Content: High-quality, informative, factually accurate
- Speakers:
  * 大牛: Technical expert, explains complex topics clearly
  * 一帆: Curious interviewer, asks good questions and engages the audience

Format example:
【大牛】大家好，欢迎来到今天的技术分享。我是大牛。
【一帆】大家好，我是一帆。今天我们聊聊人工智能的最新进展。
【大牛】没错，最近AI领域确实有很多激动人心的突破。

Make sure each speaker tag is on its own line and followed by the text.
Generate engaging content with natural conversation flow.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a skilled podcast scriptwriter who creates engaging educational content in Chinese."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )

    return response.choices[0].message.content


def generate_script_with_anthropic(topic: str, api_key: str, duration_minutes: int) -> str:
    """Generate podcast script using Anthropic API."""
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""
Generate a podcast script about "{topic}".

Requirements:
- Format: Dialogue between two speakers: 【大牛】 and 【一帆】
- Duration: Approximately {duration_minutes} minutes when spoken
- Language: Chinese (Simplified)
- Style: Conversational, educational, engaging
- Content: High-quality, informative, factually accurate
- Speakers:
  * 大牛: Technical expert, explains complex topics clearly
  * 一帆: Curious interviewer, asks good questions and engages the audience

Format example:
【大牛】大家好，欢迎来到今天的技术分享。我是大牛。
【一帆】大家好，我是一帆。今天我们聊聊人工智能的最新进展。
【大牛】没错，最近AI领域确实有很多激动人心的突破。

Make sure each speaker tag is on its own line and followed by the text.
Generate engaging content with natural conversation flow.
"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        temperature=0.7,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.content[0].text


def main():
    parser = argparse.ArgumentParser(description='Dora node - Generate podcast script using LLM')
    parser.add_argument('--provider', default='openai', choices=['openai', 'anthropic'], help='LLM provider')
    parser.add_argument('--duration', type=int, default=5, help='Target duration in minutes')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    args = parser.parse_args()

    node = Node("script-generator")

    send_log(node, "INFO", "Script Generator node started", args.log_level)

    # Get API key from environment
    if args.provider == 'openai':
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            send_log(node, "ERROR", "OPENAI_API_KEY environment variable not set", args.log_level)
            return 1
    else:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            send_log(node, "ERROR", "ANTHROPIC_API_KEY environment variable not set", args.log_level)
            return 1

    # Wait for topic input
    for event in node:
        if event["type"] == "INPUT":
            if event["id"] == "topic":
                try:
                    raw_value = event.get("value")
                    if raw_value and len(raw_value) > 0:
                        topic = raw_value[0].as_py()
                        send_log(node, "INFO", f"Received topic: {topic}", args.log_level)

                        # Generate script
                        send_log(node, "INFO", f"Generating script using {args.provider}...", args.log_level)

                        try:
                            if args.provider == 'openai':
                                script = generate_script_with_openai(topic, api_key, args.duration)
                            else:
                                script = generate_script_with_anthropic(topic, api_key, args.duration)

                            send_log(node, "INFO", "Script generated successfully", args.log_level)

                            # Output to dataflow
                            node.send_output("script", pa.array([script]))
                            node.send_output("complete", pa.array([True]))

                            send_log(node, "INFO", "Script sent to dataflow", args.log_level)

                        except Exception as e:
                            send_log(node, "ERROR", f"Failed to generate script: {e}", args.log_level)
                            return 1

                except Exception as e:
                    send_log(node, "ERROR", f"Error processing topic: {e}", args.log_level)
                    return 1

    return 0


if __name__ == "__main__":
    exit(main())
