# Migration from Dora Examples - Summary

This document tracks the migration of the chatbot-openai-0905 example and Docker setup from the Dora repository to Airos Voice Agent.

## ✅ Completed

### Directory Structure
```
airos-voice-agent/
├── .gitignore                    ✅ Created
├── README.md                     ✅ Existing
├── QUICKSTART.md                 ✅ Created
├── MIGRATION.md                  ✅ This file
├── docker/
│   ├── Dockerfile                ✅ Adapted from Dora
│   ├── docker-compose.yml        ✅ Adapted from Dora
│   ├── entrypoint.sh             ✅ Adapted from Dora
│   ├── requirements.txt          ✅ Created
│   └── .env.example              ✅ Created
├── examples/
│   └── openai-realtime/
│       ├── dataflow.yml          ✅ Ported from chatbot-openai-0905
│       ├── maas_config.toml.example ✅ Ported
│       ├── viewer.py             ✅ Ported
│       └── README.md             ✅ Created
├── nodes/                        ⚠️ Populated during Docker build
│   ├── dora-asr/                 (from Dora)
│   ├── dora-primespeech/         (from Dora)
│   ├── dora-speechmonitor/       (from Dora)
│   └── dora-text-segmenter/      (from Dora)
└── scripts/
    └── build-docker.sh           ✅ Created
```

### Key Changes from Original

#### 1. Path Updates
- Changed all `../../node-hub/` → `../../nodes/`
- Updated MaaS config path to `/opt/airos/examples/openai-realtime/`

#### 2. Docker Adaptations
- Dockerfile clones Dora repo during build (doesn't depend on local Dora)
- Copies only required node-hub components
- Updated working directory to `/opt/airos`
- Simplified to single example (openai-realtime)

#### 3. Configuration
- Renamed `maas_mcp_browser_config.toml` → `maas_config.toml`
- Created `.env.example` with clearer variable names
- Simplified docker-compose profiles

## 📋 Next Steps (TODO)

### Immediate (Required for first run)

1. **Create .env file**
   ```bash
   cd docker
   cp .env.example .env
   # Edit: Set MODELS_DIR and OPENAI_API_KEY
   ```

2. **Build Docker image**
   ```bash
   ./scripts/build-docker.sh
   ```

3. **Download models**
   ```bash
   cd docker
   docker compose run downloader
   ```

4. **Test server**
   ```bash
   docker compose --profile openai-realtime up server
   ```

### Short-term (Within 1-2 weeks)

- [ ] Add model download script that actually works (current downloader is placeholder)
- [ ] Test complete pipeline end-to-end
- [ ] Add local development setup (without Docker)
- [ ] Create ARCHITECTURE.md with system diagrams
- [ ] Add GitHub Actions for automated builds
- [ ] Create example configs for different LLM providers (Anthropic, local)

### Medium-term (1-2 months)

- [ ] Implement LLM router for smart local/cloud switching
- [ ] Add mac-aec-chat as local-only example
- [ ] Create cross-platform audio input nodes
- [ ] Add authentication to WebSocket server
- [ ] Implement conversation history/memory
- [ ] Add metrics and monitoring dashboard

### Long-term (Future)

- [ ] Multi-client support (iOS, Android apps)
- [ ] Edge deployment options (Raspberry Pi, edge servers)
- [ ] Voice customization/cloning
- [ ] Multi-language support beyond Chinese
- [ ] Integration with home automation systems

## 🔍 Important Notes

### Dependencies on Dora Repo

The current setup **requires** the Dora repository during Docker build:

```dockerfile
# In Dockerfile
RUN git clone --branch cloud-model-mcp https://github.com/kippalbot/dora.git
```

**Why?**
- We need to compile Rust binaries (dora-openai-websocket, dora-maas-client)
- We need Dora node-hub components (dora-asr, dora-primespeech, etc.)

**Future improvement:**
- Pre-build binaries and publish to GitHub releases
- Fork required node-hub components into airos-voice-agent
- Remove dependency on Dora repo for production builds

### Node Components

Currently copied from Dora during Docker build:
- `dora-asr` - Speech recognition (FunASR/Whisper)
- `dora-primespeech` - Chinese TTS
- `dora-speechmonitor` - VAD and segmentation
- `dora-text-segmenter` - LLM output chunking

These should eventually be:
1. Forked into airos-voice-agent repo for independence
2. Modified/improved for specific use cases
3. Packaged as pip-installable modules

### Model Downloads

The current `downloader` service is a **placeholder**. You need to:

1. Manually run model downloads:
   ```bash
   # From Dora repo
   cd examples/model-manager
   python download_models.py --download funasr
   python download_models.py --download primespeech
   ```

2. Point `MODELS_DIR` to where you downloaded them

**TODO:** Create proper model download script in `scripts/download-models.sh`

## 🧪 Testing Checklist

Before considering migration complete:

- [ ] Docker image builds successfully
- [ ] Models download and populate correctly
- [ ] Server starts without errors
- [ ] WebSocket accepts connections
- [ ] Audio pipeline works (mic → ASR → LLM → TTS → speaker)
- [ ] MaaS client connects to OpenAI
- [ ] Browser automation (MCP) works
- [ ] Logs are readable and helpful
- [ ] Graceful shutdown works
- [ ] Can restart without issues

## 📚 Documentation Status

| Document | Status | Notes |
|----------|--------|-------|
| README.md | ✅ Complete | High-level overview |
| QUICKSTART.md | ✅ Complete | End-to-end setup |
| MIGRATION.md | ✅ Complete | This file |
| ARCHITECTURE.md | ❌ TODO | System design details |
| examples/openai-realtime/README.md | ✅ Complete | Example-specific guide |
| CONTRIBUTING.md | ❌ TODO | Contribution guidelines |
| docker/README.md | ❌ TODO | Docker-specific docs |

## 🔗 References

- Original Dora repo: https://github.com/kippalbot/dora
- Branch used: `cloud-model-mcp`
- Original example: `examples/chatbot-openai-0905`
- Docker setup: `docker/`

## 🤝 Acknowledgments

This migration is based on the excellent work from the Dora project:
- Dora framework and CLI
- Node implementations (ASR, TTS, speech monitor)
- WebSocket server architecture
- Docker setup and best practices

Thank you to the Dora community! 🙏
