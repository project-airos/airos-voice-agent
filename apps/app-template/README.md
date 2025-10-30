# {{APP_NAME}}

Description of this voice application.

## Quick Start

### Prerequisites

1. Install Docker and Docker Compose
2. Set up environment variables:

```bash
# Copy and edit environment file
cp .env.example .env
# Edit .env and add your API keys
```

### Running the Application

#### Option 1: Docker Compose (Recommended)

```bash
# Download models (one-time setup)
docker compose --profile setup up downloader

# Start the server
docker compose --profile {{APP_NAME}} up server

# View logs
docker compose logs -f server

# Stop
docker compose down
```

#### Option 2: Manual Docker

```bash
# Build image
cd ../../
docker build -t airos-voice-agent:latest -f core/docker/Dockerfile.template .

# Start container
cd apps/{{APP_NAME}}
docker run --rm -p 8123:8123 \
  -e OPENAI_API_KEY=your_key \
  -v $(pwd)/models:/root/.dora/models \
  airos-voice-agent:latest
```

## Configuration

### API Keys

Set your API keys in `.env`:

```bash
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
```

### Model Paths

The models are shared across all apps via a Docker volume. Default location:

- `/root/.dora/models` in container
- `./models` on host (configurable via `MODELS_DIR`)

### Ports

Default port: `8123`

Change via `APP_PORT` environment variable:

```bash
APP_PORT=9000 docker compose up server
```

## Dataflow

This application uses the following Dora dataflow:

```
WebSocket Client
    ↓ audio
Speech Monitor (VAD)
    ↓ audio_segment
ASR (Automatic Speech Recognition)
    ↓ transcription
MaaS Client (LLM + MCP)
    ↓ text (streaming)
Text Segmenter
    ↓ text_segment
TTS (Text-to-Speech)
    ↓ audio
    ↑ (back to client)
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

### Local Development (without Docker)

See main project README for local development setup.

## Troubleshooting

### Models not found

```bash
# Check model directory
docker compose exec server ls -la /root/.dora/models/

# Re-download models
docker compose --profile setup up downloader
```

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

## Next Steps

- Add more applications to the `apps/` directory
- Customize the dataflow for your use case
- Integrate with additional LLM providers
- Add new TTS voices or ASR languages

## Architecture

This app uses the shared infrastructure from `core/`:

- **Base Image**: `core/docker/Dockerfile.template`
- **Shared Nodes**: `nodes/` (common across all apps)
- **Compose Template**: `core/configs/compose-templates/docker-compose.app.template.yml`

All apps are isolated and can run independently while sharing:
- Docker base image
- Model volume
- Common nodes and dependencies
