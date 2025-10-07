# OpenAI Realtime API Compatible Voice Agent

This example implements an OpenAI Realtime API compatible WebSocket server for voice interaction with cloud LLMs.

## Features

- **WebSocket Server**: Compatible with Moly client and OpenAI Realtime API
- **Cloud LLM Integration**: Connect to OpenAI, Anthropic, or other providers via MaaS client
- **Voice Pipeline**: Speech Monitor → ASR → LLM → Text Segmenter → TTS
- **Browser Automation**: Optional MCP Playwright integration for web tasks

## Architecture

```
Client (Moly/Browser)
    ↓ WebSocket (audio + text)
WebSocket Server (wserver)
    ↓
Speech Monitor (VAD + segmentation)
    ↓
ASR (FunASR/Whisper)
    ↓
MaaS Client (OpenAI/Anthropic)
    ↓
Text Segmenter (streaming chunks)
    ↓
PrimeSpeech TTS
    ↓ audio back to client
```

## Quick Start (Docker)

### 1. Setup Environment

```bash
cd ../../docker

# Copy and edit environment file
cp .env.example .env
nano .env  # Set MODELS_DIR and OPENAI_API_KEY
```

### 2. Build Image

```bash
docker build -t airos-voice-agent:latest -f Dockerfile ..
```

### 3. Download Models

```bash
# This will populate your MODELS_DIR with ASR and TTS models
docker compose run downloader
```

### 4. Configure MaaS

```bash
cd ../examples/openai-realtime

# Copy and edit configuration
cp maas_config.toml.example maas_config.toml

# Set your API key in maas_config.toml:
# openai_api_key = "sk-your-key-here"
# Or use environment variable: env:OPENAI_API_KEY
```

### 5. Run Server

```bash
cd ../../docker

# Start the server
docker compose --profile openai-realtime up server

# You should see:
# [airos] 🚀 Launching WebSocket server on 0.0.0.0:8123
```

### 6. Connect with Moly

1. Open Moly client
2. Configure "Dora Realtime" provider:
   - WebSocket URL: `ws://localhost:8123`
   - API Key: (any placeholder value)
   - System Prompt: Set to Chinese or English based on your TTS voice

3. Start chatting!

## Quick Start (Local Development)

### Prerequisites

- Python 3.12+
- Rust toolchain
- Conda (optional but recommended)
- Git with LFS

### 1. Install Dependencies

```bash
# Create conda environment
conda create -n airos python=3.12
conda activate airos

# Install Dora CLI
pip install dora-rs

# Install Python nodes
cd ../../nodes
pip install -e dora-asr
pip install -e dora-primespeech
pip install -e dora-speechmonitor
pip install -e dora-text-segmenter

# Build Rust components (from Dora repo)
cd /path/to/dora
cargo build --release -p dora-openai-websocket
cargo build --release -p dora-maas-client

# Copy binaries to PATH or use full path when running
```

### 2. Download Models

```bash
# From Dora repo
cd examples/model-manager
python download_models.py --download funasr
python download_models.py --download primespeech
```

### 3. Configure and Run

```bash
cd /path/to/airos-voice-agent/examples/openai-realtime

# Copy config
cp maas_config.toml.example maas_config.toml
# Edit maas_config.toml with your API key

# Start Dora
dora up

# Build and start dataflow
dora build dataflow.yml
dora start dataflow.yml --name voice-agent --detach

# Start WebSocket server
dora-openai-websocket -- --name wserver
```

## Configuration

### Environment Variables

```bash
# ASR Configuration
export ASR_ENGINE=funasr  # or whisper
export LANGUAGE=zh  # or en, auto
export ASR_MODELS_DIR=~/.dora/models/asr

# TTS Configuration
export VOICE_NAME=Doubao  # Chinese voice
export PRIMESPEECH_MODEL_DIR=~/.dora/models/primespeech
export TEXT_LANG=zh

# Server Configuration
export HOST=0.0.0.0
export PORT=8123
export RUST_LOG=info
```

### MaaS Configuration (maas_config.toml)

```toml
[openai]
api_base = "https://api.openai.com/v1"
openai_api_key = "env:OPENAI_API_KEY"  # or direct key
model = "gpt-4o-mini"
temperature = 0.7
max_tokens = 256

[mcp.playwright]
command = "npx"
args = ["-y", "@playwright/mcp"]
headless = true
```

## Troubleshooting

### WebSocket Connection Failed

```bash
# Check if server is running
docker compose ps

# Check logs
docker compose logs server

# Ensure port 8123 is not blocked
```

### No Audio Output

```bash
# Check if models are downloaded
ls $MODELS_DIR/primespeech

# Check TTS node logs
docker compose logs server | grep primespeech
```

### ASR Not Transcribing

```bash
# Verify models exist
ls $MODELS_DIR/asr/funasr

# Check ASR logs
docker compose logs server | grep asr

# Test audio input
docker compose logs server | grep "Audio frame received"
```

### MaaS Client Errors

```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Check maas_config.toml exists
cat maas_config.toml

# Test API connectivity
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

## Advanced Usage

### Custom System Prompt

Edit `maas_config.toml`:

```toml
[openai]
system_prompt = """
You are a helpful AI assistant.
Keep responses concise and conversational.
"""
```

### Enable Browser Automation

Ensure `maas_config.toml` has MCP Playwright configured:

```toml
[mcp.playwright]
command = "npx"
args = ["-y", "@playwright/mcp"]
headless = true
browser_type = "chromium"
```

Then ask the AI to:
- "Open Google and search for..."
- "Navigate to example.com"
- "Take a screenshot"

### Switch to Different Voice

Edit `dataflow.yml`:

```yaml
env:
  VOICE_NAME: Luo Xiang  # Or: Yang Mi, Zhou Jielun, Maple, etc.
```

Restart the dataflow:

```bash
dora stop voice-agent
dora start dataflow.yml --name voice-agent --detach
```

## Files

- `dataflow.yml` - Main Dora dataflow configuration
- `maas_config.toml` - Cloud LLM and MCP configuration
- `viewer.py` - Optional monitoring/debugging script
- `README.md` - This file

## Next Steps

- Try different TTS voices
- Experiment with different LLM providers (Anthropic, local models)
- Add custom MCP tools
- Implement conversation history persistence
- Add authentication to WebSocket server

## References

- [Dora Framework](https://github.com/dora-rs/dora)
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime)
- [Moly Client](https://github.com/moly-ai/moly)
- [MCP Protocol](https://modelcontextprotocol.io/)
