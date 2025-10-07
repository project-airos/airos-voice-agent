# Airos Voice Agent — Agent Notes

## Context Recap
- Core vision (see `README.md`): local-first, Dora-based voice agent with configurable ASR (FunASR/Whisper), MaaS-powered LLM, and PrimeSpeech TTS.
- Detailed architecture (see `CLAUDE.md`): tiered routing strategy, Dora dataflow with dynamic WebSocket node → speech monitor → ASR → MaaS → text segmenter → TTS → client audio loopback.
- Example in scope: `examples/openai-realtime` packaged through Docker (`docker/Dockerfile`, `docker/docker-compose.yml`) to expose an OpenAI Realtime-compatible WebSocket server at `ws://localhost:8123`.

## Current Docker Focus
- `docker/Dockerfile` builds Dora binaries (`dora-openai-websocket`, `dora-maas-client`, `dora`) and pre-installs Python nodes (`dora-asr`, `dora-speechmonitor`, `dora-text-segmenter`, `dora-primespeech`).
- `docker/docker-compose.yml` defines:
  - `downloader`: warms `MODELS_DIR` with FunASR + PrimeSpeech assets.
  - `server` (profile `openai-realtime`): launches Dora daemon, builds `examples/openai-realtime/dataflow.yml`, starts dynamic WebSocket node.
- Required host prep:
  1. Copy `docker/.env.example` → `docker/.env`, set `MODELS_DIR`, API keys.
  2. `./scripts/build-docker.sh`
  3. `cd docker && docker compose run downloader`
  4. `docker compose --profile openai-realtime up server`

## Bug We Found
- Symptom: Docker dataflow nodes crash immediately with `version mismatch: message format v0.6.0 is not compatible with expected message format v0.5.0`.
- Root cause: `dora-rs` Python package auto-upgraded to `>=0.6`, while bundled Dora daemon (from `kippalbot/dora` `cloud-model-mcp`) still speaks v0.5 message format.
- Fix implemented:
  - Pin `dora-rs` to `0.3.12` in `docker/requirements.txt`.
  - Constrain each node’s `pyproject.toml` (`dora-*-` packages) to `<0.3.13`.
  - Remove `build: pip install -e …` directives from `examples/openai-realtime/dataflow.yml` so runtime builds don’t reinstall nodes with newer deps.
  - Ensure runtime deps include `silero-vad` (needed by speech monitor).

## How To Validate After Rebuild
- `./scripts/build-docker.sh` to bake the new dependency pins.
- `docker compose run downloader` (only if models missing).
- `docker compose --profile openai-realtime up server` should now show all static nodes registering without version-mismatch errors; watch for `[airos] ✅ Dataflow started.` followed by PrimeSpeech log activity.
- If an older image is cached, force rebuild: `docker build --no-cache -t airos-voice-agent:latest -f docker/Dockerfile .`

## Next Checks / Follow-ups
- Confirm WebSocket server stays connected to dataflow (`dora-openai-websocket --name wserver`) and that Moly client can stream audio round-trip.
- Consider upgrading Dora daemon + CLI once upstream message format v0.6 is fully supported; when doing so, relax the `<0.6.0` pin.
- Tail node logs via `docker compose logs -f server` (entrypoint already tails `wserver`; add others via `TAIL_NODE_LOGS` env if needed).
- Keep `MODELS_DIR` mounted read-only for server to avoid accidental writes; downloader remains sole writer.
