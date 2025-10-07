# Airos Voice Agent – Deployment Status

**Date:** 2025-10-07 01:05 PST  
**Status:** 90 % complete – audio pipeline up, conversational turns still unreliable  
**Session:** Dockerised realtime server validation & voice round-trip debugging

---

## ✅ Confirmed Working

- **Docker image** rebuilds cleanly with the pinned Dora stack (`dora-rs==0.3.12`) and all PrimeSpeech/MoYoYo dependencies (`ffmpeg-python`, `torchmetrics`, `LangSegment`, `pytorch-lightning`, etc.).
- **Dynamic `wserver` node** now connects after the dataflow starts; container logs show `✅ Successfully connected to dataflow as 'wserver'`, and the WebSocket server listens on `ws://0.0.0.0:8123`.
- **PrimeSpeech TTS** initialises successfully and emits audio buffers; metadata sanitisation removes `None` values, preventing Arrow conversion errors.
- **Port mapping** verified (`docker compose ps` shows `0.0.0.0:8123->8123/tcp`); the Moly client can open a session.
- **All static nodes** (`speech-monitor`, `asr`, `maas-client`, `text-segmenter`, `primespeech`) spawn without version-mismatch issues since the dependency pins were applied.

---

## ⚠️ Outstanding Issues

1. **Greeting sometimes inaudible in client**  
   Server logs confirm audio segments are generated (resampled 32 kHz → 24 kHz, ~48 KB PCM payload), yet the Moly client occasionally plays silence. Need to verify whether the PCM samples are near-zero or if the client discards the chunk for another reason.

2. **Follow-up user turns produce no ASR transcript**  
   Recent `log_asr.txt` files contain only model initialisation entries—no `transcription` outputs reach MaaS. Possible causes: incoming audio format mismatch, ASR language locked to Chinese (`LANGUAGE: zh` in `examples/openai-realtime/dataflow.yml:84`) while the user speaks English, or speech monitor thresholds cutting segments before ASR runs.

3. **Speech monitor floods debug logs**  
   Continuous `[DEBUG] Received audio chunk #…` messages show microphone audio arriving, but we still need to confirm that `question_ended` fires and segments propagate downstream.

4. **OpenBLAS warnings**  
   PrimeSpeech prints `OpenBLAS Warning: Detect OpenMP Loop…` repeatedly. Benign for now, yet we may want to set `OPENBLAS_NUM_THREADS=1` to avoid performance cliffs.

---

## ✅ Recent Fixes & Notes

- Pinned `dora-rs` to `0.3.12` in the Docker image and in each node package to match the daemon’s v0.5 message format.
- Added the full PrimeSpeech dependency bundle to `docker/requirements.txt` and installed it in the running container for this debugging session.
- Sanitised TTS metadata payloads so Arrow arrays no longer include `None` values.
- Documented in `README.md` that the `nodes/` directory is part of the repo and must stay under version control.

---

## 🔍 Next Investigation Steps

1. **Inspect outbound audio samples**  
   Dump the raw PCM array from the first greeting to confirm amplitude. If samples look healthy, examine the WebSocket encoding/Base64 path or the Moly client playback.

2. **Relax ASR configuration for English testing**  
   Change `LANGUAGE` to `auto` (or `en`) in `examples/openai-realtime/dataflow.yml` and restart. Watch `log_asr.txt` for new transcripts when speaking English.

3. **Capture client-side `response.audio.delta` payloads**  
   Run Moly with verbose logging or test with a simple WebSocket client to ensure audio deltas arrive with expected sizes and metadata.

4. **Tune speech monitor thresholds**  
   If segments never complete, increase `USER_SILENCE_THRESHOLD_MS` / `SILENCE_THRESHOLD_MS` or temporarily disable VAD gating to guarantee ASR receives full utterances.

5. **Quieten OpenBLAS warnings**  
   Export `OPENBLAS_NUM_THREADS=1` in the Docker image to eliminate warning spam and reduce risk of hangs.

---

**Summary:** Infrastructure and node orchestration are in place, models load, the WebSocket server exchanges events with the Moly client, and TTS emits audio frames. Remaining work focuses on ensuring the audio heard by the client is audible/complete and that user speech reliably flows through ASR → MaaS → TTS for follow-up turns.
