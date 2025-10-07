# Airos Voice Agent - Deployment Status

**Date**: 2025-10-06
**Status**: Partially Working - WebSocket Integration Issue

## ✅ What's Working

### 1. Docker Infrastructure
- ✅ Multi-stage Docker build (Rust + Python) compiles successfully
- ✅ All dependencies install correctly
- ✅ Environment configuration via `.env` file
- ✅ Model directory mounting works correctly

### 2. Node Build System
- ✅ All nodes build without errors:
  - `dora-asr` (Chinese ASR with FunASR)
  - `dora-primespeech` (Chinese TTS)
  - `dora-speechmonitor` (VAD/speech detection)
  - `dora-text-segmenter` (LLM output chunking)
  - `dora-maas-client` (Cloud LLM integration)
  - `dora-openai-websocket` (WebSocket server)

### 3. Dataflow Execution
- ✅ Dora daemon starts successfully
- ✅ Dataflow builds and validates correctly
- ✅ All static nodes spawn successfully
- ✅ WebSocket server listens on port 8123

### 4. Fixes Applied
- ✅ Fixed `primespeech-tts` not found error (removed from requirements.txt)
- ✅ Fixed node build errors (removed `build:` commands from dataflow.yml)
- ✅ Fixed model path mounting (created proper `.env` file)
- ✅ Confirmed models already downloaded (~20GB)

## ⚠️ Current Issue

### WebSocket Server Crash Loop

**Problem**: The `dora-openai-websocket` node is in a crash loop because it's not properly integrating with the Dora dataflow.

**Symptoms**:
```
wserver: stdout    Running in standalone mode (no --name argument provided)
wserver: stdout    WebSocket server ready, listening on 0.0.0.0:8123
[airos] Log stream ended for wserver, retrying...
```

The server starts, but immediately exits because it's in standalone mode instead of connecting to the dataflow.

**Root Cause**:
When `path: dora-openai-websocket` is used in dataflow.yml, Dora spawns the binary but doesn't pass the `--name wserver` argument needed to connect it as a Dora node.

## 🔧 Attempted Solutions

### Attempt 1: Use `args` field
```yaml
- id: wserver
  path: dora-openai-websocket
  args: --node  # Didn't work - Dora doesn't pass this to binary
```
**Result**: Failed - `args` field is for Python operator paths, not binary arguments

### Attempt 2: Dynamic node with manual launch
```yaml
- id: wserver
  path: dynamic
```
Then launch via entrypoint.sh:
```bash
exec dora-openai-websocket -- --name wserver
```
**Result**: Failed with error "no node with ID `wserver`"

## 💡 Possible Solutions

### Option A: Fix Dynamic Node Connection
1. Revert wserver to `path: dynamic` in dataflow.yml
2. Debug why `dora-openai-websocket --name wserver` can't find the node config
3. Possible causes:
   - Need to specify dataflow UUID/name when connecting?
   - Timing issue (node tries to connect before dataflow fully initialized)?
   - Dynamic node registration not working for `path: dynamic`?

### Option B: Modify WebSocket Server Binary
1. Create wrapper script that launches the binary with correct arguments
2. Modify entrypoint.sh to properly connect the dynamic node
3. Add additional parameters (e.g., `--dataflow voice-agent`)

### Option C: Use Operator Instead of Path
1. Create a custom operator wrapper for the WebSocket server
2. Use `operator: rust: <path>` instead of `path: dora-openai-websocket`
3. Build the operator as part of the dataflow

## 📋 Next Steps

**Priority 1**: Fix WebSocket integration
- [ ] Investigate `dora-openai-websocket` CLI parameters
- [ ] Check if binary needs dataflow UUID to connect
- [ ] Test manual connection outside Docker
- [ ] Debug why dynamic node registration fails

**Priority 2**: Test end-to-end pipeline
- [ ] Fix WebSocket crash loop
- [ ] Test connection with Moly client
- [ ] Verify audio flows through pipeline
- [ ] Test ASR → LLM → TTS chain

**Priority 3**: Documentation updates
- [ ] Document the dynamic node connection pattern
- [ ] Update QUICKSTART.md with correct startup sequence
- [ ] Add troubleshooting guide for WebSocket issues

## 🎯 Current State Summary

**Can run**: ✅ `docker compose --profile openai-realtime up server`
**Dora starts**: ✅ Yes
**Nodes spawn**: ✅ Yes (all 6 nodes)
**WebSocket accessible**: ✅ Yes (port 8123 listening)
**WebSocket stable**: ❌ No (crash loop)
**Ready for Moly**: ❌ No (WebSocket not integrated with dataflow)

The good news: **95% of the infrastructure is working!** Only the WebSocket ↔ Dora integration needs to be fixed.

## 📦 Working Docker Commands

```bash
# Build image (works perfectly)
./scripts/build-docker.sh

# Start server (starts but WebSocket crashes)
cd docker
docker compose --profile openai-realtime up server

# View logs
docker compose logs -f server

# Stop server
docker compose down
```

## 🔍 Debug Commands

```bash
# Check if WebSocket port is accessible
curl -v http://localhost:8123

# List running Dora dataflows (from inside container)
docker exec -it docker-server-1 dora list

# Check Dora node status
docker exec -it docker-server-1 dora status voice-agent

# View specific node logs
docker exec -it docker-server-1 dora logs voice-agent wserver
```

## 📄 Files Modified

### Fixed
- `docker/requirements.txt` - Removed primespeech-tts
- `docker/.env` - Created with actual paths
- `examples/openai-realtime/dataflow.yml` - Removed build commands, tried args field

### To Review
- `docker/entrypoint.sh` - May need WebSocket connection logic
- `examples/openai-realtime/dataflow.yml` - May need different wserver config

---

**Last Updated**: 2025-10-06 22:10 PST
**Next Session**: Focus on fixing dynamic node connection for WebSocket server
