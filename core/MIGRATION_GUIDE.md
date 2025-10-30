# Migration Guide

This guide explains how to migrate existing applications and add new ones to the airos-voice-agent multi-app architecture.

## Table of Contents

1. [Migrating an Existing App](#migrating-an-existing-app)
2. [Adding a New App from Dora Examples](#adding-a-new-app-from-dora-examples)
3. [Creating a New App from Scratch](#creating-a-new-app-from-scratch)
4. [Porting Configuration](#porting-configuration)
5. [Testing the Migration](#testing-the-migration)

---

## Migrating an Existing App

### From `examples/` to `apps/`

The original structure had applications in `examples/`:

```
Old Structure:
examples/
└── openai-realtime/
    ├── dataflow.yml
    ├── maas_config.toml.example
    └── README.md

New Structure:
apps/
└── openai-chat/
    ├── docker-compose.yml       ← NEW
    ├── dataflow.yml
    ├── maas_config.toml.example
    ├── .env.example             ← NEW
    └── README.md                ← UPDATED
```

### Step-by-Step Migration

1. **Create app directory:**
   ```bash
   cd /path/to/airos-voice-agent
   mkdir -p apps/your-app-name
   ```

2. **Copy existing files:**
   ```bash
   cp -r examples/old-app/* apps/your-app-name/
   ```

3. **Create docker-compose.yml:**
   ```bash
   # Option 1: Use template
   cp core/configs/compose-templates/docker-compose.app.template.yml \
      apps/your-app-name/docker-compose.yml

   # Option 2: Copy from existing app
   cp apps/openai-chat/docker-compose.yml \
      apps/your-app-name/docker-compose.yml
   ```

4. **Customize docker-compose.yml:**
   ```yaml
   # apps/your-app-name/docker-compose.yml
   services:
     server:
       environment:
         APP_NAME: your-app-name              # ← Set your app name
         EXAMPLE_DIR: /opt/airos/apps/your-app-name  # ← Set app path
         APP_PORT: 8123                       # ← Set your port
         DATAFLOW_NAME: your-app-name         # ← Set dataflow name
   ```

5. **Create .env.example:**
   ```bash
   cp docker/.env.example apps/your-app-name/.env.example
   ```

6. **Update paths in dataflow.yml:**
   ```yaml
   # Update build paths to use new location
   - id: asr
     build: pip install -e ../../nodes/dora-asr  # ← Still correct

   # Update config path
   - id: maas-client
     env:
       MAAS_CONFIG_PATH: /opt/airos/apps/your-app-name/maas_config.toml
   ```

7. **Update README.md:**
   - Simplify to app-specific info
   - Reference `core/README.md` for shared infrastructure
   - Include app-specific troubleshooting

8. **Test the migration:**
   ```bash
   cd apps/your-app-name

   # Build image
   docker build -t airos-voice-agent:latest ../..

   # Download models
   docker compose --profile setup up downloader

   # Start app
   docker compose --profile your-app-name up server
   ```

---

## Adding a New App from Dora Examples

Dora has example applications we can port:

- `chatbot-alicloud-0908` → `apps/alicloud-chat`
- `podcast-generator` → `apps/podcast-generator`
- `chatbot-openai-websocket-browser` → `apps/browser-multiclient`

### Example: Migrating `chatbot-alicloud-0908`

1. **Get the example from Dora:**
   ```bash
   cd /tmp
   git clone --depth 1 --branch cloud-model-mcp \
     https://github.com/kippalbot/dora.git
   cd dora/examples/chatbot-alicloud-0908
   ```

2. **Copy to airos-voice-agent:**
   ```bash
   cd /path/to/airos-voice-agent
   mkdir -p apps/alicloud-chat
   cp -r /tmp/dora/examples/chatbot-alicloud-0908/* apps/alicloud-chat/
   ```

3. **Adapt for airos-voice-agent:**
   ```bash
   # Use app template as reference
   cd apps/alicloud-chat

   # Create docker-compose.yml
   cp ../openai-chat/docker-compose.yml docker-compose.yml

   # Create .env.example
   cp ../../docker/.env.example .env.example

   # Update paths in dataflow.yml:
   # - build paths should be: pip install -e ../../nodes/dora-xxx
   # - config path should be: /opt/airos/apps/alicloud-chat/config.toml
   ```

4. **Customize for Alicloud:**
   ```yaml
   # docker-compose.yml
   environment:
     APP_NAME: alicloud-chat
     APP_PORT: 8124  # Different port from openai-chat
     EXAMPLE_DIR: /opt/airos/apps/alicloud-chat

   # maas_config.toml
   [alibaba_cloud]
   api_key = "env:ALIBABA_CLOUD_API_KEY"
   model = "qwen-plus"
   ```

5. **Update README:**
   - Document Alicloud-specific setup
   - Explain differences from OpenAI version
   - Include troubleshooting

---

## Creating a New App from Scratch

### Using the App Template

1. **Create from template:**
   ```bash
   cd apps/
   cp -r app-template my-new-app
   cd my-new-app
   ```

2. **Customize docker-compose.yml:**
   ```yaml
   # Set app-specific variables
   APP_NAME: my-new-app
   APP_PORT: 9000
   EXAMPLE_DIR: /opt/airos/apps/my-new-app
   DATAFLOW_NAME: my-new-app
   WS_SERVER_NAME: wserver
   ```

3. **Customize dataflow.yml:**
   ```yaml
   nodes:
     # Use shared nodes
     - id: speech-monitor
       path: dora-speechmonitor
       build: pip install -e ../../nodes/dora-speechmonitor

     # Customize for your use case
     - id: asr
       env:
         ASR_ENGINE: whisper  # or funasr
         LANGUAGE: en         # or zh, auto

     - id: primespeech
       env:
         VOICE_NAME: EnglishVoice  # or Doubao, Luo Xiang
         TEXT_LANG: en
   ```

4. **Configure LLM:**
   ```toml
   # config.toml
   [openai]
   model = "gpt-4o"  # or gpt-4o-mini, etc.

   [anthropic]
   model = "claude-3-5-sonnet-20241022"
   ```

5. **Update README.md:**
   - Document your app's purpose
   - Include setup instructions
   - Add troubleshooting section

### Minimal App Example

Here's a minimal app that just echoes back what you say:

```
apps/simple-echo/
├── docker-compose.yml
├── dataflow.yml
├── config.toml.example
└── README.md
```

**dataflow.yml:**
```yaml
nodes:
  - id: wserver
    path: dynamic
    inputs:
      audio: primespeech/audio
      asr_transcription: asr/transcription
      speech_started: speech-monitor/speech_started
      question_ended: speech-monitor/question_ended
      segment_complete: primespeech/segment_complete
    outputs:
      - audio
      - text

  - id: speech-monitor
    path: dora-speechmonitor
    build: pip install -e ../../nodes/dora-speechmonitor
    inputs:
      audio: wserver/audio
    outputs: [speech_started, speech_ended, question_ended, audio_segment]

  - id: asr
    path: dora-asr
    build: pip install -e ../../nodes/dora-asr
    inputs:
      audio: speech-monitor/audio_segment
    outputs: [transcription]

  - id: echo-client
    path: dynamic  # Simple echo without LLM
    inputs:
      text: asr/transcription
    outputs:
      - text

  - id: text-segmenter
    path: dora-text-segmenter
    build: pip install -e ../../nodes/dora-text-segmenter
    inputs:
      text: echo-client/text
      tts_complete: primespeech/segment_complete
    outputs: [text_segment]

  - id: primespeech
    path: dora-primespeech
    build: pip install -e ../../nodes/dora-primespeech
    inputs:
      text: text-segmenter/text_segment
    outputs: [audio, segment_complete]
```

---

## Porting Configuration

### Environment Variables

**Old style** (hardcoded in docker-compose):
```yaml
environment:
  EXAMPLE_DIR: /opt/airos/examples/openai-realtime
  DATAFLOW_FILE: dataflow.yml
```

**New style** (variables with defaults):
```yaml
environment:
  APP_NAME: ${APP_NAME:-my-app}
  EXAMPLE_DIR: ${EXAMPLE_DIR:-/opt/airos/apps/my-app}
  DATAFLOW_FILE: ${DATAFLOW_FILE:-dataflow.yml}
  DATAFLOW_NAME: ${DATAFLOW_NAME:-my-app}
```

### Model Paths

**Old style** (hardcoded):
```yaml
ASR_MODELS_DIR: /root/.dora/models/asr
PRIMESPEECH_MODEL_DIR: /root/.dora/models/primespeech
```

**New style** (from env):
```yaml
ASR_MODELS_DIR: /root/.dora/models/asr  # Same, but mounted as volume
PRIMESPEECH_MODEL_DIR: /root/.dora/models/primespeech
```

### Ports

**Old style** (single app):
```yaml
ports:
  - "8123:8123"
```

**New style** (configurable):
```yaml
ports:
  - "${APP_PORT:-8123}:${APP_PORT:-8123}"
```

### Config Files

**Old style** (relative paths):
```yaml
MAAS_CONFIG_PATH: ./maas_config.toml
```

**New style** (absolute paths):
```yaml
MAAS_CONFIG_PATH: /opt/airos/apps/my-app/maas_config.toml
```

### Volume Mounts

**Old style** (repo directory):
```yaml
volumes:
  - ${REPO_DIR:-..}:/opt/airos
```

**New style** (same, but more flexible):
```yaml
volumes:
  - ${REPO_DIR:-..}:/opt/airos
  - ${MODELS_DIR:?Please set MODELS_DIR}:/root/.dora/models:ro
```

---

## Testing the Migration

### 1. Build Test

```bash
# Build the base image
docker build -t airos-voice-agent:latest .

# Verify it builds without errors
# Check that all layers are cached
```

### 2. Setup Test

```bash
cd apps/your-app-name

# Download models (if not already done)
docker compose --profile setup up downloader

# Check models were downloaded
ls -la ./models/
```

### 3. Start Test

```bash
# Start the app
docker compose --profile your-app-name up server

# Check logs for success
# Look for: "🚀 Launching WebSocket server on 0.0.0.0:8123"
```

### 4. Connection Test

```bash
# Test WebSocket connection
curl http://localhost:8123

# Or use Moly client to connect
# Configure WebSocket URL: ws://localhost:8123
```

### 5. Functionality Test

```bash
# Speak into microphone
# Verify transcription appears in logs
# Verify LLM responds
# Verify TTS audio output
```

### 6. Isolation Test

```bash
# Start another app on different port
cd apps/openai-chat
APP_PORT=8124 docker compose --profile openai-chat up server

# Verify both apps run simultaneously
# Test connections to both
```

### 7. Cleanup Test

```bash
# Stop all apps
docker compose down

# Verify no port conflicts
netstat -an | grep 8123

# Restart and verify
docker compose up server
```

### Automated Tests

Run the smoke test suite:

```bash
cd apps/your-app-name
docker compose --profile tests up tests
```

This should test:
- ASR model loading
- TTS model loading
- Basic transcription
- Basic synthesis

---

## Common Issues and Solutions

### Issue: "Example dir not found"

**Error:**
```
[airos] ❌ Cannot cd into /opt/airos/apps/your-app
```

**Solution:**
```yaml
# In docker-compose.yml
environment:
  EXAMPLE_DIR: /opt/airos/apps/your-app-name
```

### Issue: "Port already in use"

**Error:**
```
Error starting userland proxy: listen tcp 0.0.0.0:8123: bind: address already in use
```

**Solution:**
```bash
# Use different port
echo "APP_PORT=9000" >> .env
```

### Issue: "Models not found"

**Error:**
```
FileNotFoundError: model.bin
```

**Solution:**
```bash
# Download models
docker compose --profile setup up downloader

# Verify volume mount
docker compose exec server ls -la /root/.dora/models/
```

### Issue: "Multiple dataflows contain dynamic node id"

**Error:**
```
Error: Multiple dataflows contain dynamic node id wserver
```

**Solution:**
```bash
# Stop all Dora instances
dora destroy

# Start fresh
docker compose up server
```

### Issue: "Config file not found"

**Error:**
```
Error: Cannot read config.toml
```

**Solution:**
```yaml
# In docker-compose.yml
environment:
  MAAS_CONFIG_PATH: /opt/airos/apps/your-app-name/config.toml
```

### Issue: "Build path not found"

**Error:**
```
ERROR: Can't find package at ../../node-hub/dora-asr
```

**Solution:**
```yaml
# In dataflow.yml - use correct path
- id: asr
  build: pip install -e ../../nodes/dora-asr  # Not node-hub!
```

---

## Checklist

Use this checklist when migrating or creating a new app:

- [ ] Created app directory in `apps/`
- [ ] Copied/migrated existing files
- [ ] Created `docker-compose.yml` from template
- [ ] Set `APP_NAME`, `APP_PORT`, `EXAMPLE_DIR`
- [ ] Created `.env.example`
- [ ] Updated paths in `dataflow.yml`
- [ ] Updated `MAAS_CONFIG_PATH` in dataflow
- [ ] Updated `README.md`
- [ ] Tested build
- [ ] Tested model download
- [ ] Tested app start
- [ ] Tested WebSocket connection
- [ ] Tested end-to-end functionality
- [ ] Tested isolation (multiple apps)
- [ ] Cleaned up test runs

---

## Summary

The migration process:

1. **Preserves functionality** while improving structure
2. **Adds isolation** through per-app configuration
3. **Shares resources** (image, models) efficiently
4. **Enables scaling** to multiple apps easily

For questions or issues, refer to:
- `core/README.md` - Architecture overview
- `apps/openai-chat/` - Example migrated app
- `apps/app-template/` - Template for new apps
