#!/bin/bash
# Generate Podcast inside Docker - topic → LLM script → TTS → final audio

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
COMPOSE_CMD=(docker compose --profile setup --profile podcast-generator -f "$COMPOSE_FILE")

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
Usage: $0 <topic> [duration_minutes] [llm_provider] [output_file] [tts_backend]

Arguments:
  topic          - Topic for the podcast (required)
  duration       - Duration in minutes (default: 5)
  llm_provider   - openai or anthropic (default: openai)
  output_file    - Output WAV file path (default: output/ai_generated_podcast.wav)
  tts_backend    - primespeech or minimax (default: primespeech)

Examples:
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

TOPIC="${1:-}"
DURATION="${2:-5}"
PROVIDER="${3:-openai}"
OUTPUT_FILE="${4:-output/ai_generated_podcast.wav}"
TTS_BACKEND="${5:-primespeech}"  # primespeech or minimax

if [ -z "$TOPIC" ]; then
    usage
    exit 1
fi

# -----------------------------------------------------------------------------
# Validate inputs / environment
# -----------------------------------------------------------------------------

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
echo "📝 Topic: $TOPIC"
echo "⏱️  Duration: ${DURATION} minutes"
echo "🤖 LLM Provider: $PROVIDER"
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
