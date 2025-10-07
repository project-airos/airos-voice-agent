# Claude Context for Airos Voice Agent

## Project Overview

**Airos Voice Agent** is a local-first, privacy-preserving voice AI assistant framework built on the Dora dataflow runtime. It implements an OpenAI Realtime API-compatible WebSocket server with hybrid local/edge/cloud LLM routing.

**Core Philosophy:**
- **Privacy-first**: Local inference by default, cloud only when needed
- **Voice-native**: Low-latency, duplex audio with robust VAD and interruption
- **Modular**: Swap ASR/TTS/LLM backends via configuration
- **Production-ready**: Docker packaging, monitoring, graceful degradation

**Current Status:** MVP phase - OpenAI Realtime API compatible server working with cloud LLMs

---

## Architecture Overview

### Three-Tier Strategy

```
┌─────────────────────────────────────────────┐
│  Tier 1: Local (fast, private)              │
│  ├─ ASR: FunASR/Whisper (local models)      │
│  ├─ LLM: MLX (Apple Silicon) / llama.cpp    │
│  └─ TTS: PrimeSpeech (local)                │
├─────────────────────────────────────────────┤
│  Tier 2: Edge (balanced)                    │
│  ├─ Local ASR → Cloud LLM → Local TTS       │  ← Current implementation
│  └─ Smart caching & prefetch                │
├─────────────────────────────────────────────┤
│  Tier 3: Cloud (full capability)            │
│  └─ OpenAI/Anthropic via MaaS + MCP         │
└─────────────────────────────────────────────┘
```

### Current Pipeline (Tier 2)

```
WebSocket Client (Moly/Browser)
    ↓ audio (24kHz PCM)
┌───────────────────────────────────┐
│  dora-openai-websocket (Rust)     │  ← Dynamic node
│  - Protocol translation           │
│  - Audio format conversion        │
└───────────────┬───────────────────┘
                ↓ audio (16kHz)
┌───────────────────────────────────┐
│  dora-speechmonitor               │  ← Static node
│  - VAD (Voice Activity Detection) │
│  - Segmentation & buffering       │
│  - Question-end detection         │
└───────────────┬───────────────────┘
                ↓ audio_segment
┌───────────────────────────────────┐
│  dora-asr (FunASR/Whisper)        │  ← Static node
│  - Speech → Text                  │
│  - Punctuation restoration        │
│  - Language detection             │
└───────────────┬───────────────────┘
                ↓ transcription
┌───────────────────────────────────┐
│  dora-maas-client (Rust)          │  ← Static binary
│  - OpenAI/Anthropic API calls     │
│  - MCP tool integration           │
│  - Streaming responses            │
└───────────────┬───────────────────┘
                ↓ text (streaming)
┌───────────────────────────────────┐
│  dora-text-segmenter              │  ← Static node
│  - Chunk LLM output by sentence   │
│  - Backpressure control           │
│  - Queue management               │
└───────────────┬───────────────────┘
                ↓ text_segment
┌───────────────────────────────────┐
│  dora-primespeech (Chinese TTS)   │  ← Static node
│  - Text → Audio (24kHz)           │
│  - Voice cloning capable          │
│  - Segment completion signals     │
└───────────────┬───────────────────┘
                ↓ audio
                ↑ (back to WebSocket client)
```

---

## Key Concepts

### Dora Dataflow Fundamentals

**Node vs Operator:**
- **Node**: Standalone process, full lifecycle control (`path: dora-asr`)
- **Operator**: Lightweight, embedded in runtime (`operator: python: script.py`)
- **Dynamic Node**: Manually started (`path: dynamic`)
- **Static Node**: Auto-started by Dora daemon

**Event-Driven Messaging:**
- Nodes communicate via Apache Arrow messages
- Shared memory (local) or TCP (distributed)
- Zero-copy where possible
- Queue sizes configurable per input

**Dataflow YAML Structure:**
```yaml
nodes:
  - id: node-name
    path: dora-package  # or dynamic, or operator
    build: pip install -e ../../nodes/dora-package  # Optional
    inputs:
      input_name:
        source: other-node/output-name
        queue_size: 10
    outputs:
      - output_name
    env:
      CONFIG_VAR: value
```

### Critical Design Patterns

**1. WebSocket Server (Dynamic Node)**
- Runs separately: `dora-openai-websocket -- --name wserver`
- Connects to static dataflow at runtime
- Each client can spawn new dataflow instance (not implemented yet)

**2. Speech Monitor VAD Logic**
- `ACTIVE_FRAME_THRESHOLD_MS`: Minimum speech duration to trigger
- `USER_SILENCE_THRESHOLD_MS`: Silence to end speech segment
- `QUESTION_END_SILENCE_MS`: Additional silence to trigger question end
- **Critical**: Question end detection prevents premature LLM calls

**3. Text Segmentation Flow**
- LLM streams tokens → Text Segmenter buffers
- Segmenter sends one chunk at a time to TTS
- Waits for `segment_complete` signal before sending next
- **Why**: Prevents TTS queue overflow, enables interruption

**4. MaaS Client Configuration**
```toml
[openai]
api_base = "https://api.openai.com/v1"
openai_api_key = "env:OPENAI_API_KEY"  # Reads from environment
model = "gpt-4o-mini"
temperature = 0.7

[mcp.playwright]
command = "npx"
args = ["-y", "@playwright/mcp"]
headless = true
```

---

## Directory Structure Deep Dive

```
airos-voice-agent/
├── .gitignore                 # Excludes: models, *.toml, *.log, venv, etc.
├── README.md                  # High-level project overview
├── QUICKSTART.md              # 10-minute Docker setup
├── MIGRATION.md               # Migration tracking from Dora
├── CLAUDE.md                  # ← YOU ARE HERE
│
├── docker/                    # Production deployment
│   ├── Dockerfile             # Multi-stage: Rust builder + Python runtime
│   │                          # Clones Dora repo, builds binaries
│   ├── docker-compose.yml     # Services: server, downloader, notebook
│   ├── entrypoint.sh          # Startup: dora up → build → start → websocket
│   ├── requirements.txt       # Python deps (torch, funasr, transformers)
│   └── .env.example           # MODELS_DIR, OPENAI_API_KEY, etc.
│
├── examples/
│   └── openai-realtime/       # Current working example (Tier 2)
│       ├── dataflow.yml       # Main pipeline definition
│       │                      # Adapted from Dora chatbot-openai-0905
│       ├── maas_config.toml.example  # LLM + MCP configuration
│       ├── viewer.py          # Optional monitoring script
│       └── README.md          # Example-specific guide
│
├── nodes/                     # Dora node implementations
│   │                          # ⚠️ Populated during Docker build from Dora repo
│   ├── dora-asr/              # ASR: FunASR (Chinese), Whisper (multilingual)
│   ├── dora-primespeech/      # TTS: Chinese voices, GPU-capable
│   ├── dora-speechmonitor/    # VAD + segmentation
│   └── dora-text-segmenter/   # LLM output chunking
│
├── configs/                   # (Future) Routing rules, model configs
├── scripts/
│   └── build-docker.sh        # Helper: builds Docker image
│
└── (Future directories)
    ├── core/                  # Multiple dataflow variants
    │   ├── dataflow-local.yml
    │   ├── dataflow-hybrid.yml
    │   └── dataflow-cloud.yml
    └── nodes/                 # Custom nodes
        ├── audio-input/       # Cross-platform audio capture
        ├── llm-router/        # Smart local/cloud routing
        └── memory/            # Vector DB for context
```

---

## Key Files Explained

### `docker/Dockerfile`

**Two-stage build:**

1. **Builder stage** (`rust:1.85-slim`)
   - Clones Dora repo (branch: `cloud-model-mcp`)
   - Compiles Rust binaries:
     - `dora-openai-websocket` - WebSocket server
     - `dora-maas-client` - Cloud LLM client
     - `dora` - CLI for orchestration

2. **Runtime stage** (`python:3.12-slim`)
   - Installs system deps (ffmpeg, portaudio, nodejs)
   - Installs Python deps (torch CPU, funasr, transformers)
   - Installs MCP servers (Playwright for browser automation)
   - Copies Dora node-hub components
   - Copies compiled Rust binaries
   - Sets up entrypoint

**Key environment variables:**
- `MODELS_DIR` → `/root/.dora/models` (volume mount)
- `EXAMPLE_DIR` → `/opt/airos/examples/openai-realtime`
- `DATAFLOW_FILE` → `dataflow.yml`

### `docker/entrypoint.sh`

**Startup sequence:**
1. `dora destroy` - Clean slate
2. `dora up` - Start daemon + coordinator
3. Wait for Dora to be ready
4. `cd $EXAMPLE_DIR`
5. Auto-create config from `.example` if needed
6. `dora build $DATAFLOW_FILE` - Install node dependencies
7. `dora start $DATAFLOW_FILE --detach` - Start static nodes
8. Optionally tail logs for debugging
9. `exec dora-openai-websocket -- --name wserver` - Start WebSocket server

**Key insight**: Static dataflow MUST be running before WebSocket server starts, because wserver is a dynamic node that connects to the existing dataflow.

### `examples/openai-realtime/dataflow.yml`

**Node definitions:**

```yaml
nodes:
  # Dynamic node - started manually
  - id: wserver
    path: dynamic
    inputs:
      audio: primespeech/audio           # Audio from TTS
      asr_transcription: asr/transcription
      speech_started: speech-monitor/speech_started
      question_ended: speech-monitor/question_ended
      segment_complete: primespeech/segment_complete
    outputs:
      - audio  # From WebSocket client
      - text   # Greetings/commands

  # Static nodes - auto-started by Dora
  - id: speech-monitor
    path: dora-speechmonitor
    inputs:
      audio: wserver/audio
    outputs: [speech_started, speech_ended, question_ended, audio_segment]
    env:
      VAD_THRESHOLD: 0.5
      QUESTION_END_SILENCE_MS: 1500

  - id: asr
    path: dora-asr
    inputs:
      audio: speech-monitor/audio_segment
    outputs: [transcription]
    env:
      ASR_ENGINE: funasr
      LANGUAGE: zh

  - id: maas-client
    path: dora-maas-client  # Rust binary in PATH
    inputs:
      text: asr/transcription
      text_to_audio: wserver/text  # For greetings
    outputs: [text]
    env:
      MAAS_CONFIG_PATH: /opt/airos/examples/openai-realtime/maas_config.toml

  - id: text-segmenter
    path: dora-text-segmenter
    inputs:
      text: maas-client/text
      tts_complete: primespeech/segment_complete
    outputs: [text_segment]

  - id: primespeech
    path: dora-primespeech
    inputs:
      text: text-segmenter/text_segment
    outputs: [audio, segment_complete]
    env:
      VOICE_NAME: Doubao
      TEXT_LANG: zh
```

**Path conventions:**
- `path: dora-package` - Installed via pip, found in PATH
- `path: dora-maas-client` - Rust binary, copied to `/usr/local/bin/`
- `path: dynamic` - Started externally

**Build commands:**
- `build: pip install -e ../../nodes/dora-asr`
- Runs during `dora build dataflow.yml`
- Editable install (-e) for development

### `examples/openai-realtime/maas_config.toml`

**Structure:**
```toml
[openai]
api_base = "https://api.openai.com/v1"
openai_api_key = "env:OPENAI_API_KEY"  # Special syntax: reads from env
model = "gpt-4o-mini"
temperature = 0.7
max_tokens = 256

# Optional: Anthropic
[anthropic]
api_key = "env:ANTHROPIC_API_KEY"
model = "claude-3-5-sonnet-20241022"

# MCP Server: Browser automation
[mcp.playwright]
command = "npx"
args = ["-y", "@playwright/mcp"]
env = { BROWSER_TYPE = "chromium", HEADLESS = "true" }

# MCP Server: File system access
[mcp.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
```

**How MaaS uses this:**
1. Reads config on startup
2. Initializes LLM client (OpenAI/Anthropic)
3. Spawns MCP servers as subprocesses
4. Routes LLM tool calls to appropriate MCP server
5. Returns results to LLM for final response

---

## Development Workflow

### Quick Reference Commands

```bash
# Build Docker image
./scripts/build-docker.sh

# Start server
cd docker
docker compose --profile openai-realtime up server

# View logs
docker compose logs -f server

# Stop everything
docker compose down

# Rebuild after code changes
docker compose build server
docker compose up server

# Interactive debugging
docker compose run --rm server bash

# Access Jupyter notebook
docker compose --profile dev up notebook
# Open: http://localhost:8888?token=airos
```

### Local Development (Without Docker)

**Prerequisites:**
1. Install Dora CLI: `pip install dora-rs`
2. Build Rust binaries from Dora repo:
   ```bash
   cd /path/to/dora
   cargo build --release -p dora-openai-websocket
   cargo build --release -p dora-maas-client
   cp target/release/dora-* /usr/local/bin/
   ```
3. Install Python nodes:
   ```bash
   cd /path/to/dora/node-hub
   pip install -e dora-asr
   pip install -e dora-primespeech
   pip install -e dora-speechmonitor
   pip install -e dora-text-segmenter
   ```

**Run locally:**
```bash
cd examples/openai-realtime

# Create config
cp maas_config.toml.example maas_config.toml
nano maas_config.toml  # Set API key

# Start Dora
dora up

# Build dataflow
dora build dataflow.yml

# Start static nodes
dora start dataflow.yml --name voice-agent --detach

# Start WebSocket server (in another terminal)
dora-openai-websocket -- --name wserver

# Monitor
dora list
dora logs voice-agent speech-monitor
dora logs voice-agent asr
```

### Making Changes

**Changing node configuration:**
```bash
# Edit dataflow.yml
nano examples/openai-realtime/dataflow.yml

# Restart dataflow
dora stop voice-agent
dora start dataflow.yml --name voice-agent --detach
```

**Changing node code:**
```bash
# Edit node source (example)
cd /path/to/dora/node-hub/dora-asr
nano dora_asr/main.py

# Restart just that node (if using editable install)
dora stop voice-agent
dora start dataflow.yml --name voice-agent --detach
```

**Changing WebSocket server:**
```bash
# Edit Rust code in Dora repo
cd /path/to/dora/node-hub/dora-openai-websocket
nano src/main.rs

# Rebuild
cargo build --release

# Restart
# Ctrl+C in server terminal
dora-openai-websocket -- --name wserver
```

---

## Common Tasks

### Adding a New Node

**Example: Add conversation memory**

1. **Create node directory:**
   ```bash
   mkdir -p nodes/dora-memory
   cd nodes/dora-memory
   ```

2. **Create package structure:**
   ```
   dora-memory/
   ├── pyproject.toml
   ├── dora_memory/
   │   ├── __init__.py
   │   └── main.py
   ```

3. **Implement node (main.py):**
   ```python
   from dora import Node
   import pyarrow as pa

   node = Node()

   memory = []

   for event in node:
       if event["type"] == "INPUT":
           if event["id"] == "user_message":
               user_text = event["value"][0].as_py()
               memory.append({"role": "user", "content": user_text})

           elif event["id"] == "assistant_message":
               assistant_text = event["value"][0].as_py()
               memory.append({"role": "assistant", "content": assistant_text})

           # Send updated memory as JSON
           import json
           node.send_output("memory", pa.array([json.dumps(memory)]))
   ```

4. **Add to dataflow.yml:**
   ```yaml
   - id: memory
     build: pip install -e ../../nodes/dora-memory
     path: dora-memory
     inputs:
       user_message: asr/transcription
       assistant_message: maas-client/text
     outputs:
       - memory
   ```

5. **Wire to LLM:**
   ```yaml
   - id: maas-client
     inputs:
       text: asr/transcription
       conversation_history: memory/memory  # Add this
   ```

### Switching LLM Providers

**From OpenAI to Anthropic:**

1. **Edit maas_config.toml:**
   ```toml
   # Comment out or remove OpenAI section
   # [openai]
   # ...

   # Add Anthropic
   [anthropic]
   api_key = "env:ANTHROPIC_API_KEY"
   model = "claude-3-5-sonnet-20241022"
   temperature = 0.7
   max_tokens = 256
   ```

2. **Set environment variable:**
   ```bash
   # In docker/.env
   ANTHROPIC_API_KEY=sk-ant-your-key
   ```

3. **Update maas-client config in dataflow.yml (if needed):**
   ```yaml
   env:
     MAAS_CONFIG_PATH: /opt/airos/examples/openai-realtime/maas_config.toml
     DEFAULT_PROVIDER: anthropic  # Add this if maas-client supports it
   ```

4. **Restart:**
   ```bash
   docker compose down
   docker compose --profile openai-realtime up server
   ```

### Adding a New Voice

**Steps:**

1. **Download voice model** (if using PrimeSpeech):
   - Add to model download script
   - Or manually place in `$MODELS_DIR/primespeech/voices/`

2. **Update dataflow.yml:**
   ```yaml
   - id: primespeech
     env:
       VOICE_NAME: NewVoiceName
   ```

3. **Restart TTS node:**
   ```bash
   dora stop voice-agent
   dora start dataflow.yml --name voice-agent --detach
   ```

### Enabling GPU Acceleration

**For ASR (FunASR):**

1. **Install CUDA in Docker** (edit Dockerfile):
   ```dockerfile
   FROM nvidia/cuda:12.1-runtime-ubuntu22.04 AS runtime
   # ... rest of runtime stage
   ```

2. **Install PyTorch with CUDA:**
   ```dockerfile
   RUN pip install torch --index-url https://download.pytorch.org/whl/cu121
   ```

3. **Enable in dataflow.yml:**
   ```yaml
   - id: asr
     env:
       USE_GPU: "true"
   ```

4. **Run with GPU:**
   ```bash
   docker compose --profile openai-realtime up server --gpus all
   ```

---

## Troubleshooting Guide

### Issue: "Multiple dataflows contain dynamic node id wserver"

**Cause:** WebSocket server trying to start before static dataflow, or multiple instances running.

**Fix:**
```bash
dora destroy  # Nuclear option
dora up
dora start dataflow.yml --name voice-agent --detach
dora-openai-websocket -- --name wserver
```

**Prevention:** Always start static dataflow BEFORE dynamic nodes.

---

### Issue: Models not found / Git LFS pointers instead of files

**Symptoms:**
```
FileNotFoundError: model.bin
# Or files are ~130 bytes instead of >100MB
```

**Cause:** Git LFS not pulling actual files.

**Fix:**
```bash
cd $MODELS_DIR/asr/funasr/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch
git lfs pull

# Or re-download
cd /path/to/dora/examples/model-manager
python download_models.py --download funasr
```

---

### Issue: No audio output / TTS not working

**Debug steps:**

1. **Check if audio data reaches TTS:**
   ```bash
   dora logs voice-agent primespeech | grep "Received text"
   ```

2. **Check TTS model path:**
   ```bash
   docker compose exec server ls -la /root/.dora/models/primespeech
   # Should have: G2PWModel, hifigan, fastspeech2, voices/
   ```

3. **Check TTS errors:**
   ```bash
   dora logs voice-agent primespeech | grep -i error
   ```

4. **Test TTS directly:**
   ```bash
   docker compose exec server python -c "
   from dora_primespeech.synthesizer import Synthesizer
   synth = Synthesizer('/root/.dora/models/primespeech', 'Doubao')
   audio = synth.synthesize('你好世界')
   print('Success! Audio length:', len(audio))
   "
   ```

---

### Issue: ASR not transcribing / No transcription output

**Debug steps:**

1. **Check if audio reaches ASR:**
   ```bash
   dora logs voice-agent asr | grep "Received audio"
   ```

2. **Check VAD is detecting speech:**
   ```bash
   dora logs voice-agent speech-monitor | grep "Speech STARTED"
   ```

3. **Check ASR engine loading:**
   ```bash
   dora logs voice-agent asr | grep -i "loading\|initialized"
   ```

4. **Test ASR directly:**
   ```bash
   # From Dora repo
   cd examples/setup-new-chatbot/asr-validation
   python test_basic_asr.py
   ```

---

### Issue: WebSocket connection refused / Can't connect with Moly

**Debug steps:**

1. **Check if server is running:**
   ```bash
   docker compose ps
   # Should show 'server' as 'Up'
   ```

2. **Check port binding:**
   ```bash
   netstat -an | grep 8123
   # Or:
   curl http://localhost:8123
   ```

3. **Check logs for errors:**
   ```bash
   docker compose logs server | tail -50
   ```

4. **Try different URL formats:**
   - `ws://localhost:8123`
   - `ws://127.0.0.1:8123`
   - `ws://0.0.0.0:8123`
   - `ws://host.docker.internal:8123` (if Moly in Docker)

---

### Issue: MaaS client errors / LLM not responding

**Debug steps:**

1. **Check API key:**
   ```bash
   docker compose exec server printenv OPENAI_API_KEY
   ```

2. **Check config file:**
   ```bash
   docker compose exec server cat /opt/airos/examples/openai-realtime/maas_config.toml
   ```

3. **Test API directly:**
   ```bash
   curl https://api.openai.com/v1/chat/completions \
     -H "Authorization: Bearer $OPENAI_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}]}'
   ```

4. **Check maas-client logs:**
   ```bash
   dora logs voice-agent maas-client
   ```

---

## Migration History

### From Dora `chatbot-openai-0905`

**Date:** 2025-10-06

**Changes made:**
1. Cloned Docker setup from `dora/docker/`
2. Copied `chatbot-openai-0905` → `examples/openai-realtime/`
3. Updated all paths: `../../node-hub/` → `../../nodes/`
4. Renamed config: `maas_mcp_browser_config_zh.local.toml` → `maas_config.toml`
5. Adapted Dockerfile to clone Dora repo during build
6. Created standalone repo structure

**Rationale:**
- Independence from Dora monorepo
- Cleaner project structure
- Ability to iterate without affecting Dora examples
- Foundation for future local/hybrid modes

**Dependencies still on Dora:**
- Rust binaries (dora-openai-websocket, dora-maas-client)
- Python nodes (dora-asr, dora-primespeech, etc.)

**Future:** Fork and customize these components.

---

## Important Conventions

### Code Style

**Python:**
- Black formatting (88 chars)
- Type hints where helpful
- Docstrings for public functions
- Use `logging` module, not `print()`

**Rust:**
- `cargo fmt` formatting
- Use `tracing` for logging
- Handle errors explicitly (no unwrap in production)

**YAML:**
- 2-space indentation
- Comments explain WHY, not WHAT
- Group related nodes together

### Naming Conventions

**Nodes:**
- Lowercase with hyphens: `speech-monitor`, `text-segmenter`
- Descriptive names: `dora-asr` not `asr-node`

**Outputs:**
- Snake case: `audio_segment`, `speech_started`
- Past tense for events: `speech_started`, `question_ended`
- Present tense for data: `transcription`, `audio`

**Environment Variables:**
- SCREAMING_SNAKE_CASE: `OPENAI_API_KEY`, `MODELS_DIR`
- Prefixes for namespacing: `ASR_ENGINE`, `TTS_VOICE_NAME`

### Configuration Management

**Priority (highest to lowest):**
1. Environment variables
2. `.toml` config files
3. `dataflow.yml` env section
4. Node defaults

**Example:**
```yaml
# In dataflow.yml
env:
  VOICE_NAME: ${VOICE_NAME:-Doubao}  # Uses env var, defaults to Doubao
```

```bash
# Override at runtime
VOICE_NAME=LuoXiang docker compose up
```

---

## Performance Optimization

### Latency Breakdown (Typical)

```
User speaks → VAD trigger:           50-100ms
VAD → ASR processing:                200-500ms (FunASR GPU)
ASR → LLM first token:               300-800ms (cloud)
LLM → TTS synthesis:                 100-300ms (local)
TTS → Audio playback starts:         50-100ms
──────────────────────────────────────────────
Total (first audio):                 700-1800ms
```

**Optimization targets:**
1. **VAD tuning**: Lower `ACTIVE_FRAME_THRESHOLD_MS` for faster trigger
2. **ASR GPU**: Enable GPU for 2-3x speedup
3. **LLM streaming**: Already enabled, sends partial responses
4. **TTS prewarming**: Keep model loaded in memory
5. **Network**: Use edge LLM deployment for <100ms latency

### Memory Usage (Typical)

```
Dora daemon:                         ~50MB
dora-openai-websocket:               ~20MB
speech-monitor:                      ~100MB
dora-asr (FunASR):                   ~2GB (GPU) / ~500MB (CPU)
maas-client:                         ~30MB
text-segmenter:                      ~50MB
primespeech (TTS):                   ~1.5GB
──────────────────────────────────────────────
Total:                               ~4-5GB
```

**Docker container limits:**
```yaml
# In docker-compose.yml
deploy:
  resources:
    limits:
      memory: 8G
      cpus: '4'
```

---

## Testing

### Manual Testing Checklist

Before considering a change complete:

- [ ] Docker image builds successfully
- [ ] Models download without errors
- [ ] Server starts and shows "🚀 Launching WebSocket server"
- [ ] Moly connects without errors
- [ ] Audio pipeline works end-to-end:
  - [ ] Speak into microphone → see transcription in logs
  - [ ] Transcription → LLM generates response
  - [ ] Response → hear TTS audio output
- [ ] Can interrupt during TTS playback
- [ ] WebSocket disconnects gracefully
- [ ] Can reconnect after disconnect
- [ ] Logs are clean (no errors/warnings)

### Automated Testing (Future)

```bash
# Unit tests
pytest nodes/dora-asr/tests/

# Integration tests
pytest tests/integration/

# End-to-end test
python tests/e2e/test_full_pipeline.py
```

---

## Security Considerations

### Current State (MVP)

⚠️ **NOT production-ready for public deployment:**
- No authentication on WebSocket
- API keys in environment variables (readable by container)
- No rate limiting
- No input sanitization on MCP commands

### Required for Production

1. **Authentication:**
   ```rust
   // In dora-openai-websocket
   async fn handle_connection(stream, auth_token) {
       if !verify_token(auth_token) {
           return Err("Unauthorized");
       }
       // ... rest of handler
   }
   ```

2. **API key management:**
   - Use Docker secrets or HashiCorp Vault
   - Never log API keys
   - Rotate regularly

3. **Input validation:**
   - Sanitize all text inputs
   - Limit audio upload size
   - Validate MCP commands against allowlist

4. **Rate limiting:**
   - Per-IP limits on WebSocket connections
   - Per-user limits on LLM calls
   - Token bucket for audio uploads

5. **HTTPS/WSS:**
   ```nginx
   server {
       listen 443 ssl;
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://localhost:8123;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

---

## Future Roadmap

### Phase 1: Stability (Current)
- [x] Docker setup working
- [x] OpenAI Realtime API compatibility
- [ ] Complete end-to-end testing
- [ ] Model download automation
- [ ] Documentation complete

### Phase 2: Local Inference
- [ ] Add `dataflow-local.yml` with MLX/llama.cpp
- [ ] LLM router node (smart local/cloud switching)
- [ ] Local ASR (Whisper.cpp)
- [ ] Benchmark local vs cloud latency

### Phase 3: Memory & Personalization
- [ ] Vector DB integration (ChromaDB/Qdrant)
- [ ] Conversation history persistence
- [ ] User preferences storage
- [ ] RAG for knowledge retrieval

### Phase 4: Multi-platform
- [ ] iOS app (WebSocket client)
- [ ] Android app
- [ ] Web UI (React + WebSocket)
- [ ] Cross-platform audio nodes (Pulse/WASAPI)

### Phase 5: Advanced Features
- [ ] Multi-speaker support
- [ ] Voice cloning
- [ ] Multi-language switching
- [ ] Wake word detection
- [ ] Home automation integration

---

## References

### External Resources

- **Dora Framework**: https://dora-rs.ai
  - Concepts: https://dora-rs.ai/docs/guides/getting-started/
  - Python API: https://dora-rs.ai/docs/guides/getting-started/conversation_py/
  - Rust API: https://docs.rs/dora-node-api/

- **OpenAI Realtime API**: https://platform.openai.com/docs/guides/realtime
  - WebSocket protocol reference
  - Audio format specifications

- **Model Context Protocol (MCP)**: https://modelcontextprotocol.io/
  - MCP servers: https://github.com/modelcontextprotocol/servers
  - Playwright MCP: https://github.com/executeautomation/mcp-playwright

- **FunASR**: https://github.com/alibaba-damo-academy/FunASR
  - Chinese ASR model documentation
  - ONNX export guides

- **PrimeSpeech**: (Internal to Dora)
  - Voice cloning capabilities
  - G2PW phoneme conversion

### Internal Documentation

- `README.md` - Project overview
- `QUICKSTART.md` - Setup guide
- `MIGRATION.md` - Migration tracking
- `examples/openai-realtime/README.md` - Example-specific docs
- `CLAUDE.md` - This file

### Related Dora Examples

- `examples/chatbot-openai-0905` - Original source
- `examples/chatbot-alicloud-0908` - Alicloud variant
- `examples/mac-aec-chat` - Local-only macOS version
- `examples/chatbot-openai-websocket-browser` - Multi-client server

---

## When Things Go Wrong

### Emergency Commands

```bash
# Nuclear option - reset everything
docker compose down -v
dora destroy
rm -rf ~/.dora/cache

# Rebuild from scratch
docker system prune -a
./scripts/build-docker.sh
docker compose --profile openai-realtime up server

# Check system resources
docker stats
df -h  # Disk space
free -h  # Memory
```

### Getting Help

1. **Check logs first:**
   ```bash
   docker compose logs server | tail -100
   ```

2. **Search issues:** GitHub issues in this repo

3. **Dora community:** https://discord.gg/6eMGGutkfE

4. **Debug interactively:**
   ```bash
   docker compose run --rm server bash
   # Inside container:
   dora up
   dora list
   python -c "import dora; print(dora.__version__)"
   ```

---

## Conclusion

This document should give you (Claude Code or future developer) everything needed to:
- Understand the project architecture
- Make common changes confidently
- Debug issues systematically
- Extend functionality incrementally

**Key takeaways:**
1. Dora is event-driven, dataflow-oriented
2. Static nodes auto-start, dynamic nodes connect manually
3. WebSocket server MUST start AFTER static dataflow
4. Models are large - always check downloads
5. Current focus: Tier 2 (local ASR/TTS, cloud LLM)

Good luck! 🚀

---

**Last updated:** 2025-10-06
**Version:** 0.1.0 (MVP)
**Maintainer:** @weishao
