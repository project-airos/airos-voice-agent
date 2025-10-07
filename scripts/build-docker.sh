#!/bin/bash
# Build Airos Voice Agent Docker image

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🏗️  Building Airos Voice Agent Docker image..."
echo "   Project root: $PROJECT_ROOT"

cd "$PROJECT_ROOT"

# Build the image
docker build \
  -t airos-voice-agent:latest \
  -f docker/Dockerfile \
  .

echo "✅ Build complete!"
echo ""
echo "Next steps:"
echo "1. Set up your .env file: cp docker/.env.example docker/.env"
echo "2. Edit docker/.env and set MODELS_DIR and OPENAI_API_KEY"
echo "3. Download models: cd docker && docker compose run downloader"
echo "4. Run server: docker compose --profile openai-realtime up server"
