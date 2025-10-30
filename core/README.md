# Airos Voice Agent - Core Infrastructure

This directory contains the shared infrastructure used by all voice applications in the `apps/` directory.

## Architecture Overview

The project uses a **multi-application architecture** with shared infrastructure:

```
airos-voice-agent/
├── apps/                          # Individual voice applications
│   ├── openai-chat/              # OpenAI Realtime API compatible
│   ├── app-template/             # Template for new apps
│   └── [future apps]             # alicloud-chat, browser-multiclient, etc.
│
├── core/                          # Shared infrastructure
│   ├── docker/                   # Base images and templates
│   ├── configs/                  # Configuration templates
│   └── scripts/                  # Build and utility scripts
│
└── nodes/                         # Shared Dora nodes
    ├── dora-asr/
    ├── dora-primespeech/
    ├── dora-speechmonitor/
    └── dora-text-segmenter/
```

## Design Principles

### 1. **Isolation by Design**
Each application in `apps/`:
- Has its own `docker-compose.yml`
- Uses a dedicated port
- Runs independently
- Can be started/stopped without affecting other apps

### 2. **Shared Resources**
All apps share:
- **Docker Base Image** - Built once, used by all apps
- **Model Volume** - Read-only mount of ASR/TTS models
- **Common Nodes** - Dora nodes in `/opt/airos/nodes/`
- **Dependencies** - Python packages, Rust binaries, system libraries

### 3. **Multi-Stage Docker Build**
```
┌─────────────────────┐
│  Builder Stage      │  ← Builds Rust binaries
│  (rust:1.85-slim)   │    from Dora repo
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│  Runtime Stage      │  ← Installs Python deps,
│  (python:3.12-slim) │    copies nodes, sets up
│                     │    application environment
└─────────────────────┘
```

### 4. **Per-App Dora Daemon**
Each app starts its own Dora daemon for isolation:
- Prevents node ID conflicts
- Allows different dataflow configurations
- Enables independent debugging and monitoring

## Directory Structure

### `/core/docker/`
Contains Docker-related templates and the main Dockerfile:

- `Dockerfile.template` - Base image template for all apps
- `Dockerfile` - Main build file (identical to template)
- Other Docker files and configs

**Usage:**
```bash
# Build the base image
docker build -t airos-voice-agent:latest -f core/docker/Dockerfile.template .

# Or use the main Dockerfile (does the same thing)
docker build -t airos-voice-agent:latest .
```

### `/core/configs/`
Configuration templates for apps:

- `compose-templates/docker-compose.app.template.yml` - Template for app docker-compose files
- Templates use variable substitution for app-specific settings

**Usage:**
```bash
# Copy template to new app
cp core/configs/compose-templates/docker-compose.app.template.yml apps/my-new-app/docker-compose.yml

# Customize with environment variables:
# - APP_NAME: my-new-app
# - APP_PORT: 9000
# - EXAMPLE_DIR: /opt/airos/apps/my-new-app
```

### `/core/scripts/`
Build and utility scripts (future):

- Build scripts
- Model download utilities
- Testing utilities
- Deployment helpers

### `/apps/`
Individual voice applications. Each app is self-contained:

```
apps/openai-chat/
├── docker-compose.yml      # App-specific services
├── dataflow.yml            # Dora pipeline definition
├── maas_config.toml        # LLM and MCP configuration
├── .env.example            # Environment variables template
└── README.md               # App-specific documentation
```

### `/nodes/`
Shared Dora nodes across all apps:

- `dora-asr/` - Automatic Speech Recognition (FunASR, Whisper)
- `dora-primespeech/` - Text-to-Speech (Chinese voices)
- `dora-speechmonitor/` - Voice Activity Detection
- `dora-text-segmenter/` - LLM output chunking

## Application Lifecycle

### Creating a New App

1. **Use the template:**
   ```bash
   cd apps/
   cp -r app-template my-new-app
   cd my-new-app
   ```

2. **Customize:**
   - Edit `docker-compose.yml` - Set `APP_NAME`, `APP_PORT`, etc.
   - Edit `dataflow.yml` - Configure Dora pipeline
   - Edit `maas_config.toml` - Set LLM providers
   - Edit `README.md` - Document your app

3. **Run:**
   ```bash
   # Download models (one-time)
   docker compose --profile setup up downloader

   # Start app
   docker compose --profile my-new-app up server
   ```

### Running an App

Each app uses Docker Compose profiles for different services:

```bash
# Setup: Download models
docker compose --profile setup up downloader

# Run: Start the application
docker compose --profile openai-chat up server

# Tests: Run smoke tests
docker compose --profile tests up tests

# Dev: Start Jupyter notebook
docker compose --profile dev up notebook

# Stop
docker compose down
```

### Multiple Apps

Run multiple apps on different ports:

```bash
# Terminal 1: OpenAI Chat on port 8123
cd apps/openai-chat
docker compose --profile openai-chat up server

# Terminal 2: Another app on port 9000
cd apps/my-other-app
APP_PORT=9000 docker compose --profile my-other-app up server
```

## Configuration

### Environment Variables

Apps use these common environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | `voice-agent` |
| `APP_PORT` | WebSocket port | `8123` |
| `EXAMPLE_DIR` | App directory path | `/opt/airos/apps/{APP_NAME}` |
| `DATAFLOW_FILE` | Dora dataflow file | `dataflow.yml` |
| `DATAFLOW_NAME` | Dora dataflow name | `{APP_NAME}` |
| `MODELS_DIR` | Model volume mount | `./models` |
| `OPENAI_API_KEY` | OpenAI API key | - |

Set in `.env` file or environment:

```bash
# .env file
APP_NAME=my-app
APP_PORT=9000
OPENAI_API_KEY=sk-your-key

# Or environment
APP_PORT=9000 docker compose up server
```

### Model Volume

Models are stored in a shared Docker volume:

```
Host                    Container
./models        →       /root/.dora/models (read-only)
```

**Structure:**
```
/root/.dora/models/
├── asr/
│   └── funasr/        # FunASR models (~2GB)
└── primespeech/
    ├── G2PWModel/     # Base TTS models (~8GB)
    ├── hifigan/
    ├── fastspeech2/
    └── voices/        # Voice models (Doubao, Luo Xiang, etc.)
```

Download models once, use across all apps:

```bash
# Download for any app
cd apps/openai-chat
docker compose --profile setup up downloader

# Now available to all apps
cd apps/my-other-app
docker compose up server  # Uses same models
```

## Shared Components

### Dora Nodes

Installed in base image, available to all apps:

```python
# Installed as editable packages:
/opt/airos/nodes/dora-asr/
/opt/airos/nodes/dora-primespeech/
/opt/airos/nodes/dora-speechmonitor/
/opt/airos/nodes/dora-text-segmenter/
```

Apps reference them in `dataflow.yml`:

```yaml
- id: asr
  path: dora-asr
  build: pip install -e ../../nodes/dora-asr
```

### Rust Binaries

Built in builder stage, copied to runtime:

- `dora-openai-websocket` - WebSocket server
- `dora-maas-client` - Cloud LLM client
- `dora` - Dora CLI

### Python Dependencies

Installed in base image:

- **ML/AI**: PyTorch, FunASR, ONNX Runtime, Transformers
- **Audio**: PyAudio, SoundDevice
- **MCP**: Playwright, filesystem server
- **Dev**: JupyterLab

## Migration from Old Structure

The original structure had all apps in `examples/`:

```
Old:  examples/openai-realtime/
New:  apps/openai-chat/
```

**Changes:**
- ✅ Migrated to `apps/` directory
- ✅ Added per-app `docker-compose.yml`
- ✅ Created app template
- ✅ Base image template in `core/docker/`
- ✅ Shared configuration templates
- ✅ Better documentation

## Benefits

### For Users
- **Clear Separation**: Each app is self-contained
- **Easy Discovery**: Find apps in `/apps/`
- **Flexible Ports**: Run multiple apps simultaneously
- **Shared Models**: Download once, use everywhere

### For Developers
- **Template-Based**: Quick start for new apps
- **Consistent Structure**: All apps follow same pattern
- **Isolated Testing**: Test apps independently
- **Reusable Components**: Share nodes, images, models

### For DevOps
- **Single Base Image**: Build once, deploy many
- **Volume Management**: Shared models across containers
- **Profile-Based Compose**: Granular service control
- **Environment Variables**: Configurable per app

## Best Practices

### Adding a New App

1. **Use the template** - Don't start from scratch
2. **Choose a unique port** - Avoid conflicts
3. **Document dependencies** - What models, APIs, configs?
4. **Test isolation** - Can it run alongside other apps?
5. **Update README** - Include setup and troubleshooting

### Configuring Ports

Use environment variables, not hardcoded:

```bash
# Good: Uses environment variable
ports:
  - "${APP_PORT:-8123}:${APP_PORT:-8123}"

# Bad: Hardcoded port
ports:
  - "8123:8123"
```

### Managing Models

- Download once via any app's setup profile
- Mount as read-only in app containers
- Don't copy models per app (wastes disk space)

### Environment Variables

Provide sensible defaults:

```yaml
environment:
  APP_NAME: ${APP_NAME:-my-app}
  APP_PORT: ${APP_PORT:-8123}
  EXAMPLE_DIR: ${EXAMPLE_DIR:-/opt/airos/apps/my-app}
```

## Troubleshooting

### Image not found

```bash
# Build the base image first
docker build -t airos-voice-agent:latest .
```

### Port already in use

```bash
# Check what's using the port
netstat -an | grep 8123

# Use a different port
echo "APP_PORT=9000" >> .env
```

### Models not found

```bash
# Download models
docker compose --profile setup up downloader

# Verify models directory
ls -la ./models/
```

### Multiple dataflow error

```bash
# Stop all Dora daemons
dora destroy

# Start fresh
docker compose up server
```

## Future Enhancements

Planned improvements to the core infrastructure:

- [ ] GPU-accelerated base image variant
- [ ] Model caching strategies (S3, local registry)
- [ ] CI/CD templates for apps
- [ ] Multi-architecture support (ARM64)
- [ ] Kubernetes deployment templates
- [ ] Monitoring and observability tools

## References

- [Dora Framework](https://dora-rs.ai)
- [Docker Compose Profiles](https://docs.docker.com/compose/profiles/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime)
