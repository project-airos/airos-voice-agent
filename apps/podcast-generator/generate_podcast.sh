#!/bin/bash
# Generate Podcast inside Docker - topic → LLM script → TTS → final audio

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
COMPOSE_CMD=(docker compose --profile setup --profile podcast-generator -f "$COMPOSE_FILE")

DEFAULT_SPEAKER1_TAG="大牛"
DEFAULT_SPEAKER2_TAG="一帆"

USE_EXISTING_SCRIPT=0
PREPARED_SCRIPT_FILE=""
RESOLVED_SPEAKER1="$DEFAULT_SPEAKER1_TAG"
RESOLVED_SPEAKER2="$DEFAULT_SPEAKER2_TAG"
PG_EXISTING_SCRIPT_FILE=""
PROMPT_FILE_TITLE=""
PROMPT_FILE_DURATION=""
PROMPT_FILE_IS_SCRIPT=0
AUTO_DETECTED_SCRIPT_FROM_TOPIC_FILE=0

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

print_header() {
    echo "=========================================="
    echo "🎙️  AI Podcast Generator (Docker)"
    echo "=========================================="
    echo ""
}

usage() {
    cat <<EOF
Usage: $0 [--topic-file FILE] <topic> [duration_minutes] [llm_provider] [output_file] [tts_backend]

Arguments:
  --topic-file   - Read topic prompt from FILE (multiline supported). Overrides inline topic argument.
  --script-file  - Use an existing markdown script instead of generating one with the LLM.
                   Skips script generation entirely.
  --speaker1-tag - Speaker tag in the existing script that maps to ${DEFAULT_SPEAKER1_TAG} (default: auto-detect)
  --speaker2-tag - Speaker tag in the existing script that maps to ${DEFAULT_SPEAKER2_TAG} (default: auto-detect)
  topic          - Topic for the podcast (required if --topic-file not provided)
  duration       - Duration in minutes (default: 5)
  llm_provider   - openai or anthropic (default: openai)
  output_file    - Output WAV file path (default: output/ai_generated_podcast.wav)
  tts_backend    - minimax or primespeech (default: minimax)

Examples:
  $0 --topic-file prompts/startup_panel.txt 6 openai output/startup.wav
  $0 '人工智能的未来' 5 openai output/ai.wav primespeech
  $0 '区块链技术' 10 anthropic output/blockchain.wav minimax
  $0 '可再生能源'
EOF
}

have_env_value() {
    local var_name="$1"
    local value="${!var_name:-}"

    if [ -n "$value" ]; then
        return 0
    fi

    if [ -f ".env" ]; then
        local line
        line="$(grep -E "^[[:space:]]*${var_name}[[:space:]]*=" ".env" | tail -n 1 || true)"
        if [ -n "$line" ]; then
            line="${line#*=}"
            # Trim whitespace and strip matching quotes
            line="$(echo "$line" | sed -e 's/[[:space:]]*$//' -e 's/^[[:space:]]*//' -e 's/^\"\(.*\)\"$/\1/' -e "s/^'\(.*\)'$/\1/")"
            if [ -n "$line" ]; then
                return 0
            fi
        fi
    fi

    return 1
}

get_env_value() {
    local var_name="$1"
    local value="${!var_name:-}"

    if [ -n "$value" ]; then
        echo "$value"
        return 0
    fi

    if [ -f ".env" ]; then
        local line
        line="$(grep -E "^[[:space:]]*${var_name}[[:space:]]*=" ".env" | tail -n 1 || true)"
        if [ -n "$line" ]; then
            line="${line#*=}"
            line="$(echo "$line" | sed -e 's/[[:space:]]*$//' -e 's/^[[:space:]]*//' -e 's/^\"\(.*\)\"$/\1/' -e "s/^'\(.*\)'$/\1/")"
            if [ -n "$line" ]; then
                echo "$line"
                return 0
            fi
        fi
    fi

    return 1
}

ensure_env_value() {
    local var_name="$1"
    local hint="$2"
    if ! have_env_value "$var_name"; then
        echo "❌ Error: $var_name is not set in the environment or .env file."
        echo "   Hint: $hint"
        exit 1
    fi
}

parse_topic_file() {
    local file="$1"
    PROMPT_FILE_TITLE=""
    PROMPT_FILE_DURATION=""
    PROMPT_FILE_IS_SCRIPT=0

    local python_output
    python_output="$(
        python3 - "$file" <<'PY'
import base64
import re
import shlex
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
title = ""
duration = ""
is_script = False

heading_match = re.search(r'^\s*#\s*(.+)$', text, re.MULTILINE)
if heading_match:
    title = heading_match.group(1).strip()

tag_pattern = re.compile(r'^\s*(\*\*)?【[^】]+】', re.MULTILINE)
colon_pattern = re.compile(r'^\s*(\*\*)?[^\s:：]{1,32}\s*[：:]', re.MULTILINE)
if len(tag_pattern.findall(text)) >= 2 or len(colon_pattern.findall(text)) >= 2:
    is_script = True

if not title:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            title = stripped
            break

duration_match = None
if title:
    duration_match = re.search(r'([0-9]+)(?:\s*[–—~\-]\s*([0-9]+))?\s*分钟', title)
if not duration_match:
    duration_match = re.search(r'时长\s*[：:]\s*([0-9]+)', text)

duration_value = ""
if duration_match:
    values = [group for group in duration_match.groups() if group]
    if values:
        duration_value = values[-1]
    else:
        duration_value = duration_match.group(1)

print(f"PROMPT_FILE_CONTENT_B64={shlex.quote(base64.b64encode(text.encode('utf-8')).decode('ascii'))}")
print(f"PROMPT_FILE_TITLE={shlex.quote(title)}")
print(f"PROMPT_FILE_DURATION={shlex.quote(duration_value)}")
print(f"PROMPT_FILE_IS_SCRIPT={1 if is_script else 0}")
PY
    )"

    eval "$python_output"

    if [ -n "${PROMPT_FILE_CONTENT_B64:-}" ]; then
        TOPIC="$(
            python3 - "$PROMPT_FILE_CONTENT_B64" <<'PY'
import base64
import sys

print(base64.b64decode(sys.argv[1]).decode('utf-8'), end='')
PY
        )"
    else
        TOPIC=""
    fi

    unset PROMPT_FILE_CONTENT_B64
}

# -----------------------------------------------------------------------------
# Pre-flight checks
# -----------------------------------------------------------------------------

if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Error: docker command not found. Please install Docker first."
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "❌ Error: docker compose is not available. Please install Docker Compose v2."
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ Error: docker-compose.yml not found at $COMPOSE_FILE"
    exit 1
fi

# -----------------------------------------------------------------------------
# Parse arguments
# -----------------------------------------------------------------------------

TOPIC_FILE=""
TOPIC=""
SCRIPT_FILE=""
SPEAKER1_TAG_OVERRIDE=""
SPEAKER2_TAG_OVERRIDE=""
POSITIONAL_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --topic-file)
            if [[ $# -lt 2 ]]; then
                echo "❌ Error: --topic-file requires a file path argument."
                usage
                exit 1
            fi
            TOPIC_FILE="$2"
            shift 2
            ;;
        --topic-file=*)
            TOPIC_FILE="${1#*=}"
            shift
            ;;
        --script-file)
            if [[ $# -lt 2 ]]; then
                echo "❌ Error: --script-file requires a file path argument."
                usage
                exit 1
            fi
            SCRIPT_FILE="$2"
            shift 2
            ;;
        --script-file=*)
            SCRIPT_FILE="${1#*=}"
            shift
            ;;
        --speaker1-tag)
            if [[ $# -lt 2 ]]; then
                echo "❌ Error: --speaker1-tag requires a value."
                usage
                exit 1
            fi
            SPEAKER1_TAG_OVERRIDE="$2"
            shift 2
            ;;
        --speaker1-tag=*)
            SPEAKER1_TAG_OVERRIDE="${1#*=}"
            shift
            ;;
        --speaker2-tag)
            if [[ $# -lt 2 ]]; then
                echo "❌ Error: --speaker2-tag requires a value."
                usage
                exit 1
            fi
            SPEAKER2_TAG_OVERRIDE="$2"
            shift 2
            ;;
        --speaker2-tag=*)
            SPEAKER2_TAG_OVERRIDE="${1#*=}"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo "❌ Error: Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

if [[ $# -gt 0 ]]; then
    POSITIONAL_ARGS+=("$@")
fi

set -- "${POSITIONAL_ARGS[@]}"

if [ -n "$TOPIC_FILE" ]; then
    if [ ! -f "$TOPIC_FILE" ]; then
        echo "❌ Error: Topic file not found: $TOPIC_FILE"
        exit 1
    fi
    parse_topic_file "$TOPIC_FILE"

    if [ -z "$SCRIPT_FILE" ] && [ "${PROMPT_FILE_IS_SCRIPT:-0}" -eq 1 ]; then
        AUTO_DETECTED_SCRIPT_FROM_TOPIC_FILE=1
        SCRIPT_FILE="$TOPIC_FILE"
        if [ -n "$PROMPT_FILE_TITLE" ]; then
            TOPIC="$PROMPT_FILE_TITLE"
        else
            TOPIC="Custom script"
        fi
    fi
fi

if [ -n "$SCRIPT_FILE" ]; then
    if [ -n "$TOPIC_FILE" ] && [ "$AUTO_DETECTED_SCRIPT_FROM_TOPIC_FILE" -eq 0 ]; then
        echo "⚠️  Warning: --topic-file is ignored when --script-file is provided."
    fi
    if [ -z "$TOPIC" ]; then
        TOPIC="Custom script"
    fi
else
    if [ -z "$TOPIC" ]; then
        TOPIC="${1:-}"
        if [ $# -gt 0 ]; then
            shift
        fi
    fi
fi

DURATION_SOURCE_SUFFIX=""
if [ $# -gt 0 ]; then
    DURATION="$1"
    shift
else
    if [[ "${PROMPT_FILE_DURATION:-}" =~ ^[0-9]+$ ]]; then
        DURATION="$PROMPT_FILE_DURATION"
        DURATION_SOURCE_SUFFIX=" (from prompt file)"
    else
        DURATION="5"
    fi
fi

PROVIDER="${1:-openai}"
if [ $# -gt 0 ]; then
    shift
fi

OUTPUT_FILE="${1:-output/ai_generated_podcast.wav}"
if [ $# -gt 0 ]; then
    shift
fi

TTS_BACKEND="${1:-minimax}"  # minimax or primespeech

if [ -z "$TOPIC" ]; then
    usage
    exit 1
fi

if [ -n "$SCRIPT_FILE" ]; then
    if [ ! -f "$SCRIPT_FILE" ]; then
        echo "❌ Error: Script file not found: $SCRIPT_FILE"
        exit 1
    fi

    if [ ! -s "$SCRIPT_FILE" ]; then
        echo "❌ Error: Script file is empty: $SCRIPT_FILE"
        exit 1
    fi

    USE_EXISTING_SCRIPT=1
    PREPARED_SCRIPT_FILE="output/script_prepared.md"
    mkdir -p "$(dirname "$PREPARED_SCRIPT_FILE")"

    if [ "$AUTO_DETECTED_SCRIPT_FROM_TOPIC_FILE" -eq 1 ]; then
        echo "ℹ️  Detected script-style content in topic file; using it as a pre-written script."
    fi

    python_result="$(
        CANONICAL1="$DEFAULT_SPEAKER1_TAG" \
        CANONICAL2="$DEFAULT_SPEAKER2_TAG" \
        SPEAKER1_ALIAS="$SPEAKER1_TAG_OVERRIDE" \
        SPEAKER2_ALIAS="$SPEAKER2_TAG_OVERRIDE" \
        python3 - "$SCRIPT_FILE" "$PREPARED_SCRIPT_FILE" <<'PY'
import os
import re
import sys
from pathlib import Path

source_path = Path(sys.argv[1])
dest_path = Path(sys.argv[2])

canonical1 = os.environ.get("CANONICAL1", "大牛")
canonical2 = os.environ.get("CANONICAL2", "一帆")
alias1_override = os.environ.get("SPEAKER1_ALIAS", "").strip()
alias2_override = os.environ.get("SPEAKER2_ALIAS", "").strip()

TAG_PATTERNS = [
    re.compile(r"^(?P<indent>\s*)(?P<start>\*\*)?【\s*(?P<name>[^】]+?)\s*】(?P<end>\*\*)?(?P<spacing>\s*)(?P<text>.*)$"),
    re.compile(r"^(?P<indent>\s*)(?P<start>\*\*)?\[\s*(?P<name>[^\]]+?)\s*\](?P<end>\*\*)?(?P<spacing>\s*)(?P<text>.*)$"),
    re.compile(r"^(?P<indent>\s*)(?P<start>\*\*)?(?P<name>[^\s:：\[\]{}<>/\\]{1,64})(?P<end>\*\*)?\s*[:：](?P<spacing>\s*)(?P<text>.*)$"),
]

content = source_path.read_text(encoding="utf-8")
lines = content.splitlines()
had_trailing_newline = content.endswith(("\n", "\r"))

unique_tags = []

def extract_name(line: str):
    for pattern in TAG_PATTERNS:
        match = pattern.match(line)
        if match:
            name = match.group("name").strip()
            return name if name else None
    return None

for line in lines:
    name = extract_name(line)
    if name and name not in unique_tags:
        unique_tags.append(name)

if alias1_override:
    alias1 = alias1_override
    if alias1 not in unique_tags:
        sys.stderr.write(f"❌ Error: Speaker 1 tag '{alias1}' not found in script.\n")
        raise SystemExit(1)
else:
    alias1 = unique_tags[0] if unique_tags else ""

remaining_tags = [tag for tag in unique_tags if tag != alias1]

if alias2_override:
    alias2 = alias2_override
    if alias2 not in unique_tags:
        sys.stderr.write(f"❌ Error: Speaker 2 tag '{alias2}' not found in script.\n")
        raise SystemExit(1)
else:
    alias2 = remaining_tags[0] if remaining_tags else ""

if not alias1 or not alias2:
    sys.stderr.write(
        "❌ Error: Could not detect two distinct speaker tags in the script.\n"
    )
    raise SystemExit(1)

if alias1 == alias2:
    sys.stderr.write("❌ Error: Speaker tags must be different.\n")
    raise SystemExit(1)

if len(unique_tags) > 2:
    extras = ", ".join(tag for tag in unique_tags if tag not in {alias1, alias2})
    sys.stderr.write(
        f"⚠️  Warning: Detected extra speaker tags: {extras}. Only the first two will be used.\n"
    )

def rewrite_line(line: str) -> str:
    for pattern in TAG_PATTERNS:
        match = pattern.match(line)
        if not match:
            continue

        name = match.group("name").strip()
        if name == alias1:
            canonical = canonical1
        elif name == alias2:
            canonical = canonical2
        else:
            return line

        indent = match.group("indent") or ""
        start = match.group("start") or ""
        end = match.group("end") or ""
        spacing = match.group("spacing") or ""
        text = match.group("text") or ""

        rebuilt = f"{indent}{start}【{canonical}】{end}"
        if text:
            rebuilt += f"{spacing}{text}" if spacing else f" {text}"
        return rebuilt

    return line

converted_lines = [rewrite_line(line) for line in lines]
converted = "\n".join(converted_lines)
if had_trailing_newline:
    converted += "\n"

tag_pattern = re.compile(r"【\s*([^】]+?)\s*】")
after_tags = set(tag_pattern.findall(converted))
if canonical1 not in after_tags or canonical2 not in after_tags:
    sys.stderr.write(
        "❌ Error: Failed to normalize speaker tags to canonical values.\n"
    )
    raise SystemExit(1)

dest_path.write_text(converted, encoding="utf-8")

sys.stdout.write(f"{alias1}\t{alias2}")
PY
    )"

    if [ -z "$python_result" ]; then
        echo "❌ Error: Failed to normalize speaker tags."
        exit 1
    fi

    IFS=$'\t' read -r RESOLVED_SPEAKER1 RESOLVED_SPEAKER2 <<< "$python_result"
    PG_EXISTING_SCRIPT_FILE="$PREPARED_SCRIPT_FILE"
fi

# -----------------------------------------------------------------------------
# Validate inputs / environment
# -----------------------------------------------------------------------------

PROVIDER_DISPLAY="$PROVIDER"

if [ "$USE_EXISTING_SCRIPT" -eq 0 ]; then
    case "$PROVIDER" in
        openai)
            ensure_env_value "OPENAI_API_KEY" "export OPENAI_API_KEY=sk-your-key or add it to .env"
            ;;
        anthropic)
            ensure_env_value "ANTHROPIC_API_KEY" "export ANTHROPIC_API_KEY=sk-ant-your-key or add it to .env"
            ;;
        *)
            echo "❌ Error: Unknown provider: $PROVIDER (use 'openai' or 'anthropic')"
            exit 1
            ;;
    esac
else
    PROVIDER_DISPLAY="manual (pre-written script)"
fi

case "$TTS_BACKEND" in
    primespeech)
        DATAFLOW_FILE="dataflow-ai.yml"
        ;;
    minimax)
        ensure_env_value "MINIMAX_API_KEY" "export MINIMAX_API_KEY=your-minimax-key or add it to .env"
        if [ -n "${MINIMAX_API_KEY:-}" ]; then
            echo "🔐 Debug: MiniMax API key detected in environment variables (value hidden)."
        elif grep -Eq "^[[:space:]]*MINIMAX_API_KEY[[:space:]]*=" ".env" 2>/dev/null; then
            echo "🔐 Debug: MiniMax API key loaded from .env (value hidden)."
        else
            echo "🔐 Debug: MiniMax API key detected (value hidden)."
        fi
        DATAFLOW_FILE="dataflow-ai-minimax.yml"
        ;;
    *)
        echo "❌ Error: Unknown TTS backend: $TTS_BACKEND (use 'primespeech' or 'minimax')"
        exit 1
        ;;
esac

MODELS_DIR_VALUE="$(get_env_value MODELS_DIR || true)"

if [ "$TTS_BACKEND" = "primespeech" ]; then
    if [ -z "$MODELS_DIR_VALUE" ]; then
        echo "❌ Error: MODELS_DIR must be set for PrimeSpeech (local TTS)."
        echo "   Hint: add MODELS_DIR to .env or export it before running the script."
        exit 1
    fi
else
    if [ -z "$MODELS_DIR_VALUE" ]; then
        DEFAULT_MODELS_DIR="$SCRIPT_DIR/models"
        echo "ℹ️  MODELS_DIR not set; defaulting to $DEFAULT_MODELS_DIR"
        mkdir -p "$DEFAULT_MODELS_DIR"
        MODELS_DIR_VALUE="$DEFAULT_MODELS_DIR"
    fi
fi

export MODELS_DIR="$MODELS_DIR_VALUE"

if [ ! -f "$DATAFLOW_FILE" ]; then
    echo "❌ Error: Dataflow file not found: $DATAFLOW_FILE"
    exit 1
fi

print_header
if [ -n "$TOPIC_FILE" ]; then
    echo "🗂️  Topic file: $TOPIC_FILE"
fi
if [ "$USE_EXISTING_SCRIPT" -eq 1 ]; then
    echo "📄 Script file: $SCRIPT_FILE"
    echo "👥 Speaker tag mapping: '$RESOLVED_SPEAKER1' → ${DEFAULT_SPEAKER1_TAG}, '$RESOLVED_SPEAKER2' → ${DEFAULT_SPEAKER2_TAG}"
fi
echo "📝 Topic:"
echo "$TOPIC"
echo ""
echo "⏱️  Duration: ${DURATION} minutes${DURATION_SOURCE_SUFFIX}"
echo "🤖 LLM Provider: $PROVIDER_DISPLAY"
echo "🎤 TTS Backend: $TTS_BACKEND"
echo "🔊 Output: $OUTPUT_FILE"
echo "📄 Docker compose file: $COMPOSE_FILE"
echo ""

# -----------------------------------------------------------------------------
# Run inside Docker
# -----------------------------------------------------------------------------

DATAFLOW_NAME="podcast-generator"

echo "🐳 Launching container to run workflow..."
echo ""

"${COMPOSE_CMD[@]}" run --rm --no-deps \
    --entrypoint /bin/bash \
    --workdir /opt/airos/apps/podcast-generator \
    -e PG_TOPIC="$TOPIC" \
    -e PG_DURATION="$DURATION" \
    -e PG_PROVIDER="$PROVIDER" \
    -e PG_OUTPUT_FILE="$OUTPUT_FILE" \
    -e PG_DATAFLOW_FILE="$DATAFLOW_FILE" \
    -e PG_DATAFLOW_NAME="$DATAFLOW_NAME" \
    -e PG_USE_EXISTING_SCRIPT="$USE_EXISTING_SCRIPT" \
    -e PG_EXISTING_SCRIPT_FILE="$PG_EXISTING_SCRIPT_FILE" \
    -e PG_SPEAKER1_ALIAS="$RESOLVED_SPEAKER1" \
    -e PG_SPEAKER2_ALIAS="$RESOLVED_SPEAKER2" \
    server \
    -lc "scripts/docker_generate_podcast.sh"

echo "🎉 All done!"

# Get duration if possible
if command -v ffprobe &> /dev/null; then
    DURATION=$(ffprobe -v quiet -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_FILE" 2>/dev/null || echo "unknown")
    if [ "$DURATION" != "unknown" ]; then
        echo "⏱️  Duration: $(echo $DURATION | cut -d. -f1) seconds"
    fi
fi

echo ""
echo "🎉 Enjoy your AI-generated podcast!"
