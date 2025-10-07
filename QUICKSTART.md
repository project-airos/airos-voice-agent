# Airos Voice Agent - Quick Start Guide

Get up and running with Airos Voice Agent in 10 minutes.

## Prerequisites

- **Docker** & Docker Compose
- **50GB** disk space for models
- **OpenAI API key** (or other LLM provider)
- **Optional**: Moly client for voice chat UI

## Step-by-Step Setup

### 1. Clone and Setup Environment

```bash
# Clone your repo
cd airos-voice-agent

# Create environment file
cd docker
cp .env.example .env

# Edit .env - REQUIRED CHANGES:
nano .env
```

**In `.env`, set these values:**

```bash
MODELS_DIR=/path/to/your/models  # e.g., /home/user/airos-models
OPENAI_API_KEY=sk-your-openai-key-here
```

### 2. Build Docker Image

```bash
# From project root
./scripts/build-docker.sh

# Or manually:
docker build -t airos-voice-agent:latest -f docker/Dockerfile .
```

**Expected time:** 10-15 minutes (compiles Rust binaries, installs dependencies)

### 3. Download Models

**Option A: Using Docker (Recommended)**

```bash
cd docker

# This downloads ~12GB of ASR and TTS models
docker compose run downloader
```

**Expected time:** 20-40 minutes depending on internet speed

**Models downloaded:**
- FunASR (Chinese ASR): ~2GB
- PrimeSpeech (Chinese TTS): ~8GB
- Voice models: Doubao, Luo Xiang, Maple, Cove (~2GB)

**Option B: Local download (without Docker)**

```bash
# Set where to save models (optional)
export MODELS_DIR="$HOME/.dora/models"

# Run download script
./scripts/download-models-local.sh
```

Then point Docker to these models in `.env`:
```bash
MODELS_DIR=/Users/yourusername/.dora/models
```

### 4. Configure MaaS (LLM)

```bash
cd ../examples/openai-realtime

# Copy configuration template
cp maas_config.toml.example maas_config.toml

# Option A: Use environment variable (recommended)
# Your OPENAI_API_KEY from .env will be used automatically

# Option B: Edit config directly
nano maas_config.toml
# Change: openai_api_key = "env:OPENAI_API_KEY"
# To: openai_api_key = "sk-your-actual-key"
```

### 5. Run the Server

```bash
cd ../../docker

# Start the voice agent server
docker compose --profile openai-realtime up server

# Wait for this message:
# [airos] 🚀 Launching WebSocket server on 0.0.0.0:8123
```

### 6. Connect with Moly

1. Download Moly client: [https://moly.ai](https://moly.ai) or similar OpenAI Realtime-compatible client

2. Configure connection:
   - **WebSocket URL**: `ws://localhost:8123`
   - **API Key**: (enter any text, e.g., "fake-key")
   - **Provider**: Select "Dora Realtime" or "Custom"

3. Set system prompt (important for Chinese):
   ```
   你是一个友好的AI助手。请用中文回答所有问题，保持简洁。
   ```

4. Click "Connect" and start talking!

## Verification

### Check Server Status

```bash
# In another terminal
docker compose ps

# Should show 'server' as 'Up'
```

### View Logs

```bash
# Real-time logs
docker compose logs -f server

# Look for:
# ✅ Dora is ready
# ✅ funasr_onnx: ...
# [airos] 🚀 Launching WebSocket server
```

### Test Audio Flow

When you speak into Moly:

```bash
# You should see in logs:
[wserver] 📊 Audio frame received from Moly
[speech-monitor] Speech STARTED
[asr] 📝 Transcription: 你好
[maas-client] 🤖 LLM response: 你好！有什么可以帮助你的吗？
[primespeech] 🔊 Synthesizing audio...
```

## Troubleshooting

### Port 8123 Already in Use

```bash
# Change port in docker/.env
PORT=8124

# Restart
docker compose down
docker compose --profile openai-realtime up server
```

### Models Not Found

```bash
# Check models directory
ls $MODELS_DIR

# Should contain:
# - asr/funasr/
# - primespeech/

# If empty, re-run downloader
docker compose run downloader
```

### No Audio Output

```bash
# Check TTS models specifically
ls $MODELS_DIR/primespeech

# Should have:
# - G2PWModel/
# - hifigan/
# - fastspeech2/
# - voices/

# If missing, check downloader logs
docker compose logs downloader
```

### OpenAI API Error

```bash
# Verify API key
echo $OPENAI_API_KEY

# Test directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Should return list of models
```

### Moly Won't Connect

1. Verify server is running: `docker compose ps`
2. Check port: `curl http://localhost:8123`
3. Try `ws://0.0.0.0:8123` instead of `localhost`
4. Check firewall settings

## What's Next?

### Try Different Voices

Edit `examples/openai-realtime/dataflow.yml`:

```yaml
env:
  VOICE_NAME: Luo Xiang  # Available: Doubao, Luo Xiang, Yang Mi, Maple...
```

Restart:
```bash
docker compose down
docker compose --profile openai-realtime up server
```

### Enable Browser Automation

Already enabled by default! Try asking:
- "帮我搜索天气" (Search weather)
- "打开Google" (Open Google)
- "截个屏" (Take screenshot)

### Use Different LLM

Edit `maas_config.toml`:

```toml
[anthropic]
api_key = "sk-ant-..."
model = "claude-3-5-sonnet-20241022"
```

Update `dataflow.yml` to use Anthropic instead of OpenAI.

### Monitor Performance

```bash
# See detailed logs
docker compose logs -f server | grep -E "Speech|ASR|TTS|LLM"

# CPU/Memory usage
docker stats
```

## Clean Up

```bash
# Stop server
docker compose down

# Remove containers (keeps models)
docker compose rm -f

# Remove everything including models
rm -rf $MODELS_DIR
docker system prune -a
```

## Getting Help

- Check logs: `docker compose logs server`
- GitHub Issues: [your-repo]/issues
- Documentation: See `examples/openai-realtime/README.md`
- Dora Docs: https://dora-rs.ai

## Production Deployment

For production deployment:
1. Use `restart: always` in docker-compose.yml
2. Set up HTTPS/WSS with nginx/caddy
3. Add authentication to WebSocket
4. Mount models as read-only: `:ro`
5. Use Docker secrets for API keys
6. Set resource limits

See `ARCHITECTURE.md` for detailed production setup.
