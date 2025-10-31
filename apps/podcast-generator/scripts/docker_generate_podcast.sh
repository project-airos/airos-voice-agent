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

echo "=========================================="
echo "Step 1: Generating script with LLM..."
echo "=========================================="
echo ""

mkdir -p output
mkdir -p "$(dirname "${PG_OUTPUT_FILE:?Output file not set}")"

python3 script_generator.py \
    --topic "${PG_TOPIC:?Topic not set}" \
    --provider "${PG_PROVIDER:?Provider not set}" \
    --duration "${PG_DURATION:?Duration not set}" \
    --output-file "output/script_temp.md"

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
python3 script_segmenter.py --input-file "output/script_temp.md"

wait "${VOICE_PID}"

echo ""
echo "=========================================="
echo "✅ Podcast generation complete!"
echo "=========================================="
echo ""
echo "📁 Output file: ${PG_OUTPUT_FILE}"
echo "📄 Script file: output/script_temp.md"
echo ""
