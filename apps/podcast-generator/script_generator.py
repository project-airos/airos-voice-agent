#!/usr/bin/env python3
"""
Script Generator - Generate podcast scripts using LLM APIs
Takes a topic and generates a high-quality dialogue between 大牛 and 一帆
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


def generate_script_with_openai(topic: str, api_key: str, duration_minutes: int = 5) -> str:
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


def generate_script_with_anthropic(topic: str, api_key: str, duration_minutes: int = 5) -> str:
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
    parser = argparse.ArgumentParser(description='Generate podcast script using LLM')
    parser.add_argument('--topic', required=True, help='Podcast topic')
    parser.add_argument('--output-file', help='Output file path (optional)')
    parser.add_argument('--provider', default='openai', choices=['openai', 'anthropic'], help='LLM provider')
    parser.add_argument('--duration', type=int, default=5, help='Target duration in minutes')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    args = parser.parse_args()

    # Get API key from environment
    if args.provider == 'openai':
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            print("Error: OPENAI_API_KEY environment variable not set")
            return 1
    else:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            print("Error: ANTHROPIC_API_KEY environment variable not set")
            return 1

    print(f"Generating podcast script for topic: {args.topic}")
    print(f"Provider: {args.provider}")
    print(f"Target duration: {args.duration} minutes")
    print()

    # Generate script
    try:
        if args.provider == 'openai':
            script = generate_script_with_openai(args.topic, api_key, args.duration)
        else:
            script = generate_script_with_anthropic(args.topic, api_key, args.duration)

        # Output script
        if args.output_file:
            os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
            with open(args.output_file, 'w', encoding='utf-8') as f:
                f.write(f"# {args.topic}\n\n")
                f.write(script)
            print(f"Script saved to: {args.output_file}")
        else:
            print("Generated script:")
            print("=" * 70)
            print(script)
            print("=" * 70)

        # Also send to dataflow if running as a node
        if os.environ.get('DORA_NODE') == '1':
            node = Node("script-generator")
            send_log(node, "INFO", f"Generated script for topic: {args.topic}", args.log_level)
            node.send_output("script", pa.array([script]))
            node.send_output("topic", pa.array([args.topic]))

        return 0

    except Exception as e:
        print(f"Error generating script: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
