# Podcast Generator

Generate two-person podcast audio from markdown scripts using Dora's PrimeSpeech TTS.

## Overview

This application demonstrates:
- Sequential TTS generation with two different voices (大牛 with Luo Xiang voice, 一帆 with Doubao voice)
- Intelligent text segmentation for long passages (maintains sentence completeness)
- Automatic random 1-3 second silence padding between speaker changes
- Markdown-based script format for easy editing
- **AI-powered script generation using OpenAI or Anthropic**
- Dynamic node orchestration with Dora

## 🚀 Quick Start: AI-Generated Podcast

**New!** Generate a complete podcast from just a topic:

### Option 1: Local TTS (PrimeSpeech)
Requires model download but offline-capable:
```bash
# Generate podcast about AI (5 minutes, OpenAI + local TTS)
OPENAI_API_KEY=sk-your-key ./generate_podcast.sh "人工智能的未来" 5 openai output/ai_podcast.wav primespeech
```

### Option 2: Cloud TTS (MiniMax) ✨ NEW
No model download, fastest setup:
```bash
# Generate podcast about blockchain (10 minutes, Anthropic + cloud TTS)
ANTHROPIC_API_KEY=sk-ant-key MINIMAX_API_KEY=minimax-key \
  ./generate_podcast.sh "区块链技术详解" 10 anthropic output/blockchain.wav minimax
```

When MiniMax is selected you'll see a `🔐 Debug` line confirming the API key was detected (the value stays hidden so secrets never leak).

### Option 3: Prompt File Demo (MiniMax)
Want a ready-made prompt? Use the bundled `sample_prompt.txt` that lives beside the script:
```bash
OPENAI_API_KEY=sk-your-key MINIMAX_API_KEY=minimax-key \
  ./generate_podcast.sh --topic-file sample_prompt.txt 8
```

This runs the fully automated pipeline with OpenAI for script generation, MiniMax for speech, and saves audio to the default `output/ai_generated_podcast.wav`.

This single command will:
1. ✅ Generate a high-quality script using LLM
2. ✅ Convert to speech with dual voices (local or cloud)
3. ✅ Add natural silence between speakers
4. ✅ Output final WAV file

**Quick demo with defaults (uses local TTS):**
```bash
OPENAI_API_KEY=sk-your-key ./generate_podcast.sh "ChatGPT的发展" 5 openai output/demo.wav
```

## Architecture

```
┌─────────────────────┐
│ script_segmenter.py │ (dynamic node)
│  - Parse markdown   │
│  - Split long text  │
│  - Send segments    │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌─────────┐  ┌─────────┐
│ daniu   │  │ yifan   │ (PrimeSpeech TTS)
│ TTS     │  │ TTS     │ (static nodes)
└────┬────┘  └────┬────┘
     │            │
     │   audio +  │
     │  segment_  │
     │  complete  │
     └─────┬──────┘
           ▼
  ┌─────────────────┐
  │ voice_output.py │ (dynamic node)
  │  - Concatenate  │
  │  - Random 1-3s  │
  │    silence      │
  │  - Write WAV    │
  └─────────────────┘
```

## Dataflow Options

This app supports multiple dataflow configurations:

### 1. **Manual Script + Local TTS** - `dataflow.yml`
Pre-written markdown scripts with PrimeSpeech TTS:
- Use `script_segmenter.py` with existing markdown files
- Requires script files in `scripts/` directory
- Local TTS (PrimeSpeech)
- Requires ~10GB model download

### 2. **Manual Script + Cloud TTS** - `dataflow-minimax.yml`
Pre-written scripts with MiniMax cloud TTS:
- Same as above but uses MiniMax T2A API
- Requires `MINIMAX_API_KEY`
- No local models needed
- Pay-per-use pricing

### 3. **AI Script + Local TTS** - `dataflow-ai.yml`
Fully automated from topic to audio:
- LLM generates script automatically
- Uses PrimeSpeech for local TTS
- Requires LLM API key (OpenAI/Anthropic)
- Requires ~10GB model download

### 4. **AI Script + Cloud TTS** - `dataflow-ai-minimax.yml` ✨ NEW
Fully cloud-based pipeline:
- LLM generates script automatically
- Uses MiniMax for cloud TTS
- Requires LLM + MiniMax API keys
- No local models needed
- Fastest setup, pay-per-use

### Quick Workflow Comparison

| Workflow | Script Source | TTS Backend | Setup | Models Required | Use Case |
|----------|--------------|-------------|-------|----------------|----------|
| `dataflow.yml` | Manual | PrimeSpeech (local) | Medium | ~10GB | Full control, offline capable |
| `dataflow-minimax.yml` | Manual | MiniMax (cloud) | Fast | None | Pre-written scripts, cloud TTS |
| `dataflow-ai.yml` | AI-generated | PrimeSpeech (local) | Medium | ~10GB | Automated, offline TTS |
| `dataflow-ai-minimax.yml` ✨ | AI-generated | MiniMax (cloud) | **Fastest** | None | **Fully automated, cloud-only** |

## Prerequisites

1. Install Docker and Docker Compose
2. Set up environment variables:

```bash
# Copy and edit environment file
cp .env.example .env
# Edit .env if needed
```

## Running the Application

### Option 1: Docker Compose (Recommended)

#### Step 1: Download models (one-time setup)

```bash
# Download all required models (~10GB total)
docker compose --profile setup up downloader
```

This will download:
- FunASR models (Chinese ASR, ~2GB)
- PrimeSpeech base models (~8GB)
- Voice models (Doubao, Luo Xiang)

#### Step 2: Start the dataflow (Terminal 1)

```bash
# Start static TTS nodes
docker compose --profile podcast-generator up server
```

Wait for the message: "✅ Static nodes started. Dataflow is ready!"

#### Step 3: Start dynamic nodes (Separate terminals)

**Terminal 2 - Voice Output:**
```bash
docker compose run --rm podcast-generator bash -c "cd /opt/airos/apps/podcast-generator && python voice_output.py --output-file output/podcast.wav"
```

**Terminal 3 - Script Segmenter:**
```bash
docker compose run --rm podcast-generator bash -c "cd /opt/airos/apps/podcast-generator && python script_segmenter.py --input-file scripts/example_podcast.md"
```

**Terminal 4 (Optional) - Viewer:**
```bash
docker compose run --rm podcast-generator bash -c "cd /opt/airos/apps/podcast-generator && python viewer.py"
```

#### Step 4: Check the output

```bash
# Check generated podcast
ls -lh output/
```

### Option 2: Interactive Container

Access the container shell for development:

```bash
# Start dataflow
docker compose --profile podcast-generator up server

# In another terminal, access container
docker compose run --rm podcast-generator bash

# Inside container:
cd /opt/airos/apps/podcast-generator
python voice_output.py --output-file output/podcast.wav &
python script_segmenter.py --input-file scripts/example_podcast.md
python viewer.py
```

## Script Format

Create markdown files with speaker tags:

```markdown
# Your Podcast Title

【大牛】Text spoken by Daniu using Luo Xiang voice.

【一帆】Text spoken by Yifan using Doubao voice.

【大牛】More text from Daniu...

【一帆】More text from Yifan...
```

### Rules
- Speaker tags must be `【大牛】` or `【一帆】`
- Text accumulates from a speaker tag until the next speaker tag appears
- All lines between speaker tags are combined into one segment
- Empty lines and lines without tags (headers, etc.) are ignored
- Long segments are automatically split at punctuation marks (see Text Segmentation)
- Segments are processed sequentially in order
- Supports both plain `【大牛】` and markdown bold `**【大牛】**` formats

## Configuration

### Text Segmentation for Long Passages

Long text segments are automatically split into smaller chunks to prevent overly long TTS generation. The segmentation preserves sentence completeness by splitting at punctuation marks.

**Environment Variables:**

```bash
# Maximum segment duration (default: 10 seconds)
export MAX_SEGMENT_DURATION=10.0

# TTS speaking speed estimation (default: 4.5 chars/second for Chinese)
export TTS_CHARS_PER_SECOND=4.5

# Punctuation marks for intelligent splitting (default includes Chinese and English)
export PUNCTUATION_MARKS="。！？.!?，,、；;:"
```

**How it works:**
- Converts `MAX_SEGMENT_DURATION` to character count using `TTS_CHARS_PER_SECOND`
- Default: 10 seconds × 4.5 chars/sec = 45 characters max per segment
- Splits at punctuation boundaries to maintain sentence completeness
- Falls back to whitespace if no punctuation found
- Logs splitting activity for monitoring

**Example:**
```bash
# Allow longer segments (20 seconds max)
MAX_SEGMENT_DURATION=20.0 docker compose run --rm podcast-generator bash -c "cd /opt/airos/apps/podcast-generator && python script_segmenter.py --input-file scripts/example_podcast.md"

# Adjust for faster speech (6 chars/second)
TTS_CHARS_PER_SECOND=6.0 docker compose run --rm podcast-generator bash -c "cd /opt/airos/apps/podcast-generator && python script_segmenter.py --input-file scripts/example_podcast.md"
```

### Change Voices

Edit `dataflow.yml` to modify voice selection:

```yaml
env:
  VOICE_NAME: "Luo Xiang"  # Options: Doubao, Luo Xiang, Yang Mi, Zhou Jielun, Ma Yun, Maple, Cove
```

Restart the dataflow after making changes:

```bash
docker compose down
docker compose --profile podcast-generator up server
```

### Change Silence Duration

The silence between speaker changes is randomized between 1-3 seconds by default. To customize, edit `voice_output.py`:

```python
silence_min = 1.0  # minimum silence in seconds
silence_max = 3.0  # maximum silence in seconds
```

For fixed silence duration, set both to the same value:

```python
silence_min = 2.0  # fixed 2 seconds
silence_max = 2.0  # fixed 2 seconds
```

### Custom Script

Create your own markdown script and pass it to the segmenter:

```bash
docker compose run --rm podcast-generator bash -c "cd /opt/airos/apps/podcast-generator && python script_segmenter.py --input-file scripts/my_custom_script.md"
```

### Custom Output File

Specify a different output file:

```bash
docker compose run --rm podcast-generator bash -c "cd /opt/airos/apps/podcast-generator && python voice_output.py --output-file output/my_podcast.wav"
```

## AI-Powered Script Generation

### Using the Quick Script (Recommended)

The easiest way to generate a podcast:

```bash
./generate_podcast.sh "你的话题" [时长分钟数] [llm提供商] [输出文件]
```

**Examples:**

```bash
# 5-minute podcast about AI using OpenAI
OPENAI_API_KEY=sk-your-key ./generate_podcast.sh "人工智能的发展历程" 5 openai output/ai.wav

# 10-minute podcast about blockchain using Anthropic
ANTHROPIC_API_KEY=sk-ant-your-key ./generate_podcast.sh "区块链技术深度解析" 10 anthropic output/blockchain.wav

# Quick demo
OPENAI_API_KEY=sk-your-key ./generate_podcast.sh "机器学习入门" 3 openai output/demo.wav
```

This script automates the entire workflow:
1. Generates a high-quality script using LLM
2. Starts the TTS dataflow
3. Converts script to speech
4. Outputs final WAV file

### Manual Script Generation

You can also use the script generator directly:

```bash
# Generate script to file
python3 script_generator.py \
    --topic "可再生能源的未来" \
    --provider openai \
    --duration 5 \
    --output-file output/script.md

# Then use the script for TTS
python3 script_segmenter.py --input-file output/script.md
```

### Supported LLM Providers

**OpenAI (gpt-4o-mini):**
- Set `OPENAI_API_KEY` environment variable
- Fast and cost-effective
- Excellent Chinese language support

**Anthropic (claude-3-5-sonnet):**
- Set `ANTHROPIC_API_KEY` environment variable
- High-quality content generation
- Good for complex topics

### Supported TTS Backends

**PrimeSpeech (Local):**
- Runs locally, no API key needed
- Requires ~10GB model download
- Offline-capable
- Voices: Doubao, Luo Xiang, Yang Mi, Zhou Jielun, Ma Yun, etc.
- Configure in `dataflow.yml` or `dataflow-ai.yml`

**MiniMax T2A (Cloud):**
- Cloud API, requires `MINIMAX_API_KEY`
- No model download needed
- High-quality voices with speed/pitch/volume control
- Pay-per-use pricing
- Custom voice IDs supported
- Configure in `dataflow-minimax.yml` or `dataflow-ai-minimax.yml`

**MiniMax Configuration:**
```bash
# Required
export MINIMAX_API_KEY=your-api-key

# Optional tuning (defaults work well)
export MINIMAX_SPEED=1.0      # 0.5 - 2.0
export MINIMAX_VOL=1.0        # 0.0 - 2.0
export MINIMAX_PITCH=0        # -12 to +12
export SAMPLE_RATE=32000      # 8000, 16000, 24000, or 32000
```

Get your MiniMax API key from: https://platform.minimax.io/user-center/basic-information/interface-key

### Script Format

The AI generates scripts in this format:

```markdown
# Topic

【大牛】大家好，欢迎来到今天的技术分享。我是大牛。今天我们要聊聊...

【一帆】大家好，我是一帆。大牛，我想问问...

【大牛】好问题！让我来详细解释一下...
```

The format is automatically compatible with the script segmenter!

## Output

Generated audio: `output/podcast.wav`
- **Format:** 16-bit PCM WAV
- **Sample rate:** 32kHz (PrimeSpeech default)
- **Channels:** Mono
- **Silence:** Random 1-3 seconds between speaker changes (大牛 ↔ 一帆) for natural pacing

## How It Works

### 1. Text Segmentation
- `script_segmenter` parses markdown and extracts character segments
- Long segments are automatically split into smaller chunks (default: 10 seconds / ~45 characters)
- Splitting respects sentence boundaries using punctuation marks
- Each chunk is processed sequentially through TTS

### 2. Sequential Processing
- `script_segmenter` sends one text segment at a time
- Waits for `segment_complete` signal before sending next segment
- This ensures audio arrives at `voice_output` in correct order

### 3. Silence Padding
- `voice_output` tracks the last speaker
- When speaker changes (大牛 → 一帆 or 一帆 → 大牛):
  - Receives `segment_complete` from previous speaker
  - Adds random 1-3 seconds of silence
  - Receives audio from new speaker
- No silence is added:
  - Before the first speaker
  - Between consecutive segments from the same speaker

### 4. Completion Signal
- After sending all segments, `script_segmenter` sends `script_complete`
- `voice_output` receives this signal, writes final WAV file, and exits
- All nodes then stop gracefully

## Viewer Output

The optional viewer displays:
- **Color-coded logs:**
  - 🔴 RED for ERROR
  - 🟡 YELLOW for WARNING
  - 🔵 CYAN for INFO
- **Node-specific icons:**
  - 📝 Script Segmenter
  - 🎤 大牛 TTS (Luo Xiang)
  - 🎙️ 一帆 TTS (Doubao)
  - 🔊 Voice Output
- **Real-time events:**
  - Text segments being sent to each TTS
  - Audio segments being received
  - Silence padding being added
  - Final completion status

## Troubleshooting

### Dynamic nodes must stay running
If a dynamic node exits early, the dataflow will stall. Keep all terminals open until you see "✅ PODCAST GENERATION COMPLETE!" in the viewer.

### Audio segments out of order
This shouldn't happen due to sequential processing. If it does, check that:
- Only one `script_segmenter` instance is running
- The segmenter is receiving `segment_complete` signals correctly

### No audio output
Check:
1. PrimeSpeech models are installed: `docker compose exec server ls -la /root/.dora/models/primespeech`
2. Both TTS nodes started successfully
3. No errors in viewer logs

### Stop a running dataflow
```bash
docker compose down
```

This stops the static nodes. You'll need to manually stop the dynamic nodes (Ctrl+C in each terminal).

### View logs
```bash
# View static node logs
docker compose logs server

# View all dataflow logs (inside container)
dora logs podcast-generator
```

## Development

### Access Container Shell
```bash
docker compose run --rm podcast-generator bash
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

**Prerequisites:**
1. Install Dora CLI: `pip install dora-rs`
2. Install PrimeSpeech models
3. Install Python dependencies

**Run locally:**
```bash
# Start Dora
dora up

# Build dataflow
dora build dataflow.yml

# Start static nodes
dora start dataflow.yml --name podcast-generator --detach

# Start dynamic nodes (in separate terminals)
python voice_output.py --output-file output/podcast.wav
python script_segmenter.py --input-file scripts/example_podcast.md
python viewer.py
```

## Example Use Cases

1. **Educational podcasts:** Create teaching content with two voices
2. **Story narration:** Different voices for different characters
3. **Interview simulation:** Question-and-answer format
4. **Language learning:** Dialogue practice with native-sounding voices
5. **Audio book production:** Multiple narrator voices

## Advanced Usage

### Batch Processing
Process multiple scripts in sequence:

```bash
for script in scripts/*.md; do
    output="output/$(basename "$script" .md).wav"
    # Start dynamic nodes with custom args
    python script_segmenter.py --input-file "$script" &
    python voice_output.py --output-file "$output" &
    wait
done
```

### Custom Markdown Parser
Extend `parse_markdown()` in `script_segmenter.py` to support:
- More than two speakers
- Emotion tags: `【大牛:excited】`
- Pause controls: `【pause:2s】`
- Background music markers

## References

- [Dora Framework](https://dora-rs.ai)
- [PrimeSpeech TTS](https://github.com/dora-rs/dora)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime)

## License

Part of the Airos Voice Agent framework. See main repository for license information.
