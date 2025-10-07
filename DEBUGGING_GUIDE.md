# Dynamic Node Connection - Debugging Guide

**Issue**: WebSocket server cannot connect as dynamic node
**Error**: `failed to get node config from daemon: no node with ID 'wserver'`
**Date**: 2025-10-06
**Status**: Under investigation

---

## Quick Test Commands

### Test 1: Verify Node Registration
```bash
cd /Users/weishao/src/airos-voice-agent/docker

# Start server in background
docker compose --profile openai-realtime up -d server

# Wait for dataflow to start
sleep 10

# Exec into container
docker exec -it docker-server-1 bash

# Inside container - check Dora status
dora list
# Expected: Should show "voice-agent" dataflow

dora status voice-agent
# Expected: Should list all nodes including "wserver"
# Current: Likely missing "wserver" or marked as dynamic/not-spawned

# Try manual WebSocket connection
dora-openai-websocket -- --name wserver
# Expected: Should connect successfully
# Current: "no node with ID wserver"

exit

# Stop container
docker compose down
```

### Test 2: Compare with Original Dora
```bash
# Test if original Dora works
cd /Users/weishao/src/dora/docker

# Make sure .env is configured
cat .env  # Check MODELS_DIR and OPENAI_API_KEY

# Start original Dora's OpenAI 0905 example
docker compose --profile openai0905 up server

# Look for these success messages:
# ✅ "dataflow started"
# ✅ "WebSocket server ready, listening on 0.0.0.0:8123"
# ✅ NO "failed to get node config" error

# If successful, this confirms:
# 1. The Dora setup itself works
# 2. Something different in our airos-voice-agent config

# Stop
Ctrl+C
docker compose down
```

### Test 3: Check Dataflow Differences
```bash
# Compare dataflows
diff /Users/weishao/src/dora/examples/chatbot-openai-0905/chatbot-staticflow.yml \
     /Users/weishao/src/airos-voice-agent/examples/openai-realtime/dataflow.yml

# Key things to check:
# 1. wserver configuration
# 2. Node paths
# 3. Build commands
# 4. Environment variables
```

### Test 4: Increase Daemon Registration Time
```bash
# Edit entrypoint.sh
cd /Users/weishao/src/airos-voice-agent/docker

# Change sleep from 1 to 10
nano entrypoint.sh
# Find: sleep 1
# Change to: sleep 10

# Rebuild and test
cd ..
./scripts/build-docker.sh

cd docker
docker compose --profile openai-realtime up server

# Check if longer sleep helps node registration
```

### Test 5: Run Without Detach
```bash
# Edit entrypoint.sh to test foreground mode
cd /Users/weishao/src/airos-voice-agent/docker
nano entrypoint.sh

# Find:
#   dora start "${DATAFLOW_FILE}" --name "${DATAFLOW_NAME}" --detach
#   sleep 1
#   exec dora-openai-websocket -- --name "${WS_SERVER_NAME}"

# Change to:
#   dora start "${DATAFLOW_FILE}" --name "${DATAFLOW_NAME}" &
#   DORA_PID=$!
#   sleep 5
#   dora-openai-websocket -- --name "${WS_SERVER_NAME}" &
#   wait $DORA_PID

# Rebuild and test
cd ..
./scripts/build-docker.sh

cd docker
docker compose --profile openai-realtime up server
```

---

## Diagnostic Information to Collect

### 1. Dora Version
```bash
docker exec -it docker-server-1 dora --version
```

### 2. WebSocket Server Help
```bash
docker exec -it docker-server-1 dora-openai-websocket --help
# or
docker exec -it docker-server-1 dora-openai-websocket -- --help
```

### 3. Daemon Status
```bash
docker exec -it docker-server-1 bash
dora up
dora list -v  # Verbose output
```

### 4. Dataflow UUID
```bash
# From server logs, capture the UUID:
# "dataflow start triggered: 0199bd60-02ee-79d0-a033-d715e3d2437c"

# Try connecting with UUID:
dora-openai-websocket -- --name wserver --dataflow "0199bd60-02ee-79d0-a033-d715e3d2437c"
```

### 5. Full Container Logs
```bash
docker compose --profile openai-realtime up server 2>&1 | tee debug.log
# Save full log for analysis
```

---

## Known Working Configuration (Dora Original)

From `/Users/weishao/src/dora/examples/chatbot-openai-0905/`:

**dataflow.yml** (working):
```yaml
nodes:
  - id: wserver
    path: dynamic
    inputs:
      audio: primespeech/audio
      asr_transcription: asr/transcription
      # ... more inputs
    outputs:
      - audio
      - text
  # ... other nodes
```

**entrypoint.sh** (working):
```bash
dora up
dora build chatbot-staticflow.yml
dora start chatbot-staticflow.yml --name staticflow --detach
sleep 1
exec dora-openai-websocket -- --name wserver
```

**docker-compose.yml** (working):
```yaml
server_openai0905:
  profiles: [openai0905]
  image: dora-voicechat:latest
  entrypoint: ["/opt/dora/docker/entrypoint.sh"]
  environment:
    DATAFLOW_NAME: chatflow0905
    EXAMPLE_DIR: /opt/dora/examples/chatbot-openai-0905
    DATAFLOW_FILE: chatbot-staticflow.yml
    WS_SERVER_NAME: wserver
  volumes:
    - ${REPO_DIR:-..}:/opt/dora
```

---

## Current Configuration (Airos - Not Working)

From `/Users/weishao/src/airos-voice-agent/`:

**dataflow.yml** (not working):
```yaml
nodes:
  - id: wserver
    # Dynamic node - launched separately after dataflow starts
    path: dynamic
    inputs:
      audio: primespeech/audio
      # ... (identical to Dora)
    outputs:
      - audio
      - text
```

**entrypoint.sh** (not working):
```bash
dora up
dora build dataflow.yml
dora start dataflow.yml --name voice-agent --detach
sleep 1
exec dora-openai-websocket -- --name wserver
```

**docker-compose.yml** (not working):
```yaml
server:
  profiles: [openai-realtime]
  image: airos-voice-agent:latest
  entrypoint: ["/usr/local/bin/entrypoint.sh"]
  environment:
    DATAFLOW_NAME: voice-agent
    EXAMPLE_DIR: /opt/airos/examples/openai-realtime
    DATAFLOW_FILE: dataflow.yml
    WS_SERVER_NAME: wserver
  volumes:
    - ${REPO_DIR:-..}:/opt/airos
```

**Differences**:
1. ✅ Dataflow wserver config: IDENTICAL
2. ✅ Entrypoint launch sequence: IDENTICAL
3. ⚠️ Docker image: Different (airos-voice-agent vs dora-voicechat)
4. ⚠️ Mount path: Different (/opt/airos vs /opt/dora)
5. ⚠️ Dataflow name: Different (voice-agent vs chatflow0905)
6. ⚠️ Example directory: Different path

---

## Hypothesis Ranking

### Most Likely (Priority 1)
1. **Path Resolution Issue**: The mounted volume path `/opt/airos` might affect how Dora resolves node paths
   - **Test**: Check if `dataflow.yml` needs absolute paths
   - **Test**: Verify working directory in container

2. **Build Artifact Location**: Nodes might be built/registered in wrong location
   - **Test**: Check where Dora stores node metadata
   - **Test**: Compare Dora's internal state between working and non-working

### Possibly (Priority 2)
3. **Timing Issue**: 1 second might not be enough for daemon to register nodes
   - **Test**: Try 5-10 second sleep
   - **Test**: Poll `dora status` until wserver appears

4. **Docker Image Differences**: Our image might be missing something
   - **Test**: Compare installed binaries/libraries
   - **Test**: Check Dora runtime dependencies

### Less Likely (Priority 3)
5. **Environment Variables**: Some env var might affect node registration
   - **Test**: Copy all env vars from working Dora setup
   - **Test**: Enable RUST_LOG=debug for more logs

6. **Dataflow Name Conflict**: Maybe "voice-agent" conflicts with something
   - **Test**: Use exact same name as Dora: "chatflow0905"

---

## Success Criteria

The issue will be RESOLVED when:

```bash
docker compose --profile openai-realtime up server
```

Shows these logs:
```
[airos] ✅ Dora is ready.
[airos] Building dataflow: dataflow.yml
wserver: DEBUG    building node
[airos] Starting dataflow: dataflow.yml (name: voice-agent)
dataflow started: <UUID>
[airos] ✅ Dataflow started. Launching WebSocket server...
WebSocket server starting...
Connecting to dataflow as dynamic node: wserver
✅ Connected to dataflow as node: wserver       <-- THIS LINE
🚀 WebSocket server listening on 0.0.0.0:8123  <-- THIS LINE
```

**Current**: Fails at "Connecting to dataflow" with "no node with ID wserver"
**Target**: Successfully connect and start listening

---

## Files to Update After Fix

Once the issue is resolved, update these docs:
1. `DEPLOYMENT_STATUS.md` - Mark as ✅ RESOLVED
2. `CHECKPOINT.md` - Add solution to lessons learned
3. `QUICKSTART.md` - Confirm startup instructions work
4. `README.md` - Update status badge to "Working"
5. This file (`DEBUGGING_GUIDE.md`) - Document the solution

---

**Last Updated**: 2025-10-06 23:40 PST
**Next Session**: Start with Test 1 (Verify Node Registration)
