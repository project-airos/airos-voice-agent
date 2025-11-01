#!/usr/bin/env bash
# Internal helper executed inside the Docker container.
# Performs full podcast generation: script → dataflow → audio.

set -euo pipefail

cleanup() {
    local status=$?
    trap - EXIT
    echo ""
    echo "=========================================="
    echo "🧹 Cleaning up dataflow..."
    echo "=========================================="
    dora stop "${PG_DATAFLOW_NAME:-podcast-generator}" >/dev/null 2>&1 || true
    dora destroy >/dev/null 2>&1 || true
    exit "$status"
}
trap cleanup EXIT

cd /opt/airos/apps/podcast-generator

SCRIPT_OUTPUT_FILE="output/script_temp.md"

mkdir -p output
mkdir -p "$(dirname "${PG_OUTPUT_FILE:?Output file not set}")"

if [ "${PG_USE_EXISTING_SCRIPT:-0}" = "1" ]; then
    echo "=========================================="
    echo "Step 1: Using provided script..."
    echo "=========================================="
    echo ""

    if [ -z "${PG_EXISTING_SCRIPT_FILE:-}" ]; then
        echo "❌ Error: PG_EXISTING_SCRIPT_FILE is not set while PG_USE_EXISTING_SCRIPT=1."
        exit 1
    fi

    if [ ! -f "${PG_EXISTING_SCRIPT_FILE}" ]; then
        echo "❌ Error: Provided script file not found inside container: ${PG_EXISTING_SCRIPT_FILE}"
        exit 1
    fi

    if [ ! -s "${PG_EXISTING_SCRIPT_FILE}" ]; then
        echo "❌ Error: Provided script file is empty inside container: ${PG_EXISTING_SCRIPT_FILE}"
        exit 1
    fi

    if [ "${PG_EXISTING_SCRIPT_FILE}" != "$SCRIPT_OUTPUT_FILE" ]; then
        cp "${PG_EXISTING_SCRIPT_FILE}" "$SCRIPT_OUTPUT_FILE"
    fi

    echo "📄 Script ready: $SCRIPT_OUTPUT_FILE"
    if [ -n "${PG_SPEAKER1_ALIAS:-}" ] || [ -n "${PG_SPEAKER2_ALIAS:-}" ]; then
        echo "👥 Speaker tags mapped to canonical voices:"
        echo "   ${PG_SPEAKER1_ALIAS:-大牛} → 大牛"
        echo "   ${PG_SPEAKER2_ALIAS:-一帆} → 一帆"
    fi
else
    echo "=========================================="
    echo "Step 1: Generating script with LLM..."
    echo "=========================================="
    echo ""

    python3 script_generator.py \
        --topic "${PG_TOPIC:?Topic not set}" \
        --provider "${PG_PROVIDER:?Provider not set}" \
        --duration "${PG_DURATION:?Duration not set}" \
        --output-file "$SCRIPT_OUTPUT_FILE"
fi

echo ""
echo "=========================================="
echo "Step 2: Starting TTS dataflow in Docker..."
echo "=========================================="
echo ""

echo "📄 Using dataflow: ${PG_DATAFLOW_FILE:?Dataflow not set}"

dora destroy >/dev/null 2>&1 || true
dora up
sleep 2
dora build "${PG_DATAFLOW_FILE}"
dora start "${PG_DATAFLOW_FILE}" --name "${PG_DATAFLOW_NAME}" --detach
sleep 5

echo ""
echo "=========================================="
echo "Step 3: Running podcast generation..."
echo "=========================================="
echo ""

echo "🔊 Starting voice output..."
python3 voice_output.py --output-file "${PG_OUTPUT_FILE}" &
VOICE_PID=$!

sleep 2

echo "📝 Starting script segmenter..."
python3 script_segmenter.py --input-file "$SCRIPT_OUTPUT_FILE"

wait "${VOICE_PID}"

echo ""
echo "=========================================="
echo "✅ Podcast generation complete!"
echo "=========================================="
echo ""
echo "📁 Output file: ${PG_OUTPUT_FILE}"
echo "📄 Script file: $SCRIPT_OUTPUT_FILE"
echo ""
