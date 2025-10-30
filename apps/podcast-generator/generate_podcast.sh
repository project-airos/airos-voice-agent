#!/bin/bash
# Generate Podcast - Complete workflow from topic to final audio
# This script automates the entire process: topic → LLM script → TTS → final audio

set -e

echo "=========================================="
echo "🎙️  AI Podcast Generator"
echo "=========================================="
echo ""

# Check arguments
TOPIC="${1:-}"
DURATION="${2:-5}"
PROVIDER="${3:-openai}"
OUTPUT_FILE="${4:-output/ai_generated_podcast.wav}"

if [ -z "$TOPIC" ]; then
    echo "❌ Error: Please provide a topic"
    echo ""
    echo "Usage: $0 <topic> [duration_minutes] [llm_provider] [output_file]"
    echo ""
    echo "Examples:"
    echo "  $0 '人工智能的未来' 5 openai output/ai.wav"
    echo "  $0 '区块链技术' 10 anthropic output/blockchain.wav"
    echo "  $0 '可再生能源' 5 openai output/energy.wav"
    exit 1
fi

echo "📝 Topic: $TOPIC"
echo "⏱️  Duration: ${DURATION} minutes"
echo "🤖 LLM Provider: $PROVIDER"
echo "🔊 Output: $OUTPUT_FILE"
echo ""

# Check API key
if [ "$PROVIDER" = "openai" ]; then
    if [ -z "$OPENAI_API_KEY" ]; then
        echo "❌ Error: OPENAI_API_KEY environment variable not set"
        echo "   Set it with: export OPENAI_API_KEY=sk-your-key"
        exit 1
    fi
elif [ "$PROVIDER" = "anthropic" ]; then
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        echo "❌ Error: ANTHROPIC_API_KEY environment variable not set"
        echo "   Set it with: export ANTHROPIC_API_KEY=sk-ant-your-key"
        exit 1
    fi
else
    echo "❌ Error: Unknown provider: $PROVIDER"
    exit 1
fi

# Create output directory
mkdir -p output

echo "=========================================="
echo "Step 1: Generating script with LLM..."
echo "=========================================="
echo ""

# Generate script using Python
python3 script_generator.py \
    --topic "$TOPIC" \
    --provider "$PROVIDER" \
    --duration "$DURATION" \
    --output-file "output/script_temp.md"

if [ $? -ne 0 ]; then
    echo "❌ Error generating script"
    exit 1
fi

echo ""
echo "=========================================="
echo "Step 2: Starting TTS dataflow..."
echo "=========================================="
echo ""

# Check if dataflow is already running
if dora list 2>/dev/null | grep -q "podcast-generator"; then
    echo "⚠️  Dataflow already running, using existing instance"
else
    echo "🚀 Starting dataflow..."
    dora destroy 2>/dev/null || true
    dora up
    sleep 2

    echo "📋 Building dataflow..."
    dora build dataflow.yml

    echo "▶️  Starting static nodes..."
    dora start dataflow.yml --name podcast-generator --detach
    sleep 5
fi

echo ""
echo "=========================================="
echo "Step 3: Running podcast generation..."
echo "=========================================="
echo ""

# Start voice output in background
echo "🔊 Starting voice output..."
python3 voice_output.py --output-file "$OUTPUT_FILE" &
VOICE_PID=$!

# Wait a moment for voice_output to initialize
sleep 2

# Start script segmenter
echo "📝 Starting script segmenter..."
python3 script_segmenter.py --input-file "output/script_temp.md"

# Wait for voice output to finish
wait $VOICE_PID

echo ""
echo "=========================================="
echo "✅ Podcast generation complete!"
echo "=========================================="
echo ""
echo "📁 Output file: $OUTPUT_FILE"
echo "📄 Script file: output/script_temp.md"
echo ""

# Get duration if possible
if command -v ffprobe &> /dev/null; then
    DURATION=$(ffprobe -v quiet -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_FILE" 2>/dev/null || echo "unknown")
    if [ "$DURATION" != "unknown" ]; then
        echo "⏱️  Duration: $(echo $DURATION | cut -d. -f1) seconds"
    fi
fi

echo ""
echo "🎉 Enjoy your AI-generated podcast!"
