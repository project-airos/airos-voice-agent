#!/bin/bash
# Download models locally (without Docker)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="${MODELS_DIR:-$HOME/.dora/models}"

echo "🔽 Downloading models to: $MODELS_DIR"
echo ""

# Create directory
mkdir -p "$MODELS_DIR"

cd "$SCRIPT_DIR/models"

# Download FunASR
echo "⬇️  Step 1/3: Downloading FunASR (Chinese ASR, ~2GB)..."
python download_models.py --download funasr
echo "✅ FunASR complete"
echo ""

# Download PrimeSpeech base
echo "⬇️  Step 2/3: Downloading PrimeSpeech base models (~8GB)..."
python download_models.py --download primespeech
echo "✅ PrimeSpeech base complete"
echo ""

# Download voices
echo "⬇️  Step 3/3: Downloading voice models..."
echo "   Default voices: Doubao (Chinese), Luo Xiang (Chinese), Maple (English), Cove (English)"
python download_models.py --download voices --voices "Doubao,Luo Xiang,Maple,Cove"
echo "✅ Voices complete"
echo ""

# Summary
echo "📊 Download Summary:"
du -sh "$MODELS_DIR"/* 2>/dev/null || echo "   (No models found)"
echo ""

# Verify
echo "🔍 Verifying models..."
if [ -d "$MODELS_DIR/asr/funasr" ]; then
    echo "   ✅ ASR models found"
else
    echo "   ❌ ASR models missing"
fi

if [ -d "$MODELS_DIR/primespeech" ]; then
    echo "   ✅ PrimeSpeech models found"
else
    echo "   ❌ PrimeSpeech models missing"
fi

echo ""
echo "🎉 Model download complete!"
echo ""
echo "Next steps:"
echo "1. Set MODELS_DIR in docker/.env: MODELS_DIR=$MODELS_DIR"
echo "2. Build Docker image: ./scripts/build-docker.sh"
echo "3. Start server: cd docker && docker compose --profile openai-realtime up server"
