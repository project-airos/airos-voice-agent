# OpenAI Chat - Voice Agent

OpenAI Realtime API compatible voice chat application with cloud LLMs.

## Quick Start

### 1. Setup Environment

```bash
# Copy and edit environment file
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

### 2. Download Models (One-time Setup)

```bash
# Download ASR and TTS models
docker compose --profile setup up downloader
```

This will populate the shared models volume (default: `./models`) with:
- FunASR models (Chinese ASR, ~2GB)
- PrimeSpeech base models (~8GB)
- Voice models (Doubao, Luo Xiang, Maple, Cove)

### 3. Run the Application

```bash
# Start the server
docker compose --profile openai-chat up server

# View logs
docker compose logs -f server
```

You should see:
```
[airos] 🚀 Launching WebSocket server on 0.0.0.0:8123
```

### 4. Connect with Moly

1. Open Moly client
2. Configure "Dora Realtime" provider:
   - WebSocket URL: `ws://localhost:8123`
   - API Key: (any placeholder value)
   - System Prompt: Set to Chinese or English based on your TTS voice

3. Start chatting!

## Configuration

### API Keys

Set your API keys in `.env`:

```bash
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key  # optional
```

### MaaS Configuration

```bash
# Copy and edit configuration
cp maas_config.toml.example maas_config.toml

# The config uses environment variables by default:
# openai_api_key = "env:OPENAI_API_KEY"
```

### Ports

Default port: `8123`

Change via `APP_PORT` environment variable:

```bash
echo "APP_PORT=9000" >> .env
docker compose up server
```

## Architecture

This app uses the Dora dataflow pipeline:

```
WebSocket Client
    ↓ audio
Speech Monitor (VAD)
    ↓ audio_segment
ASR (FunASR - Chinese)
    ↓ transcription
MaaS Client (OpenAI/Anthropic)
    ↓ text (streaming)
Text Segmenter
    ↓ text_segment
PrimeSpeech TTS (Chinese voices)
    ↓ audio back to client
```

## Development

### Access Container Shell

```bash
docker compose run --rm server bash
```

### Run Tests

```bash
docker compose --profile tests up tests
```

### Jupyter Notebook

```bash
docker compose --profile dev up notebook
# Open http://localhost:8888?token=airos
```

## Troubleshooting

### Port already in use

```bash
# Change port
echo "APP_PORT=9000" >> .env
docker compose up server
```

### WebSocket connection refused

```bash
# Check if server is running
docker compose ps

# Check logs
docker compose logs server
```

### No audio output

```bash
# Check model directory
docker compose exec server ls -la /root/.dora/models/primespeech

# Re-download models
docker compose --profile setup up downloader
```

## Files

- `dataflow.yml` - Dora pipeline definition
- `docker-compose.yml` - Application services
- `maas_config.toml` - LLM and MCP configuration
- `.env.example` - Environment variables template
- `README.md` - This file

## Next Steps

- Try different TTS voices (edit `dataflow.yml`)
- Switch LLM providers (edit `maas_config.toml`)
- Add custom MCP tools for browser automation
- Experiment with different ASR engines (Whisper)

## Shared Infrastructure

This app uses the shared infrastructure from `core/`:

- **Base Image**: Built from `core/docker/Dockerfile.template`
- **Shared Nodes**: Located in `/opt/airos/nodes/`
- **Entrypoint**: `/usr/local/bin/entrypoint.sh`

All apps are isolated and can run independently while sharing:
- Docker base image
- Model volume (mounted read-only)
- Common nodes and dependencies

## Multi-App Support

The `apps/` directory can contain multiple voice applications:

- `openai-chat` - OpenAI Realtime API compatible (this app)
- `alicloud-chat` - Alicloud variant (future)
- `browser-multiclient` - Multi-client WebSocket server (future)
- `podcast-generator` - Audio content generation (future)

Each app:
- Has its own `docker-compose.yml`
- Uses a different port
- Shares the same base image and models
- Can run independently
