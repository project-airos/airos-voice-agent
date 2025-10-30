# Podcast Generator Enhancement - AI-Powered Content Generation

## Summary

Enhanced the podcast generator to include **AI-powered script generation** using OpenAI and Anthropic LLMs. Users can now generate complete podcasts from just a topic prompt!

## New Features

### 🚀 AI Script Generation

**What it does:**
- Takes a user topic/prompt as input
- Calls OpenAI or Anthropic API to generate high-quality podcast script
- Automatically formats script for TTS processing
- Outputs final WAV file with natural dual-voice audio

**Benefits:**
- ⚡ Instant podcast generation from topic
- 🎯 High-quality, engaging content
- 🔄 Fully automated workflow
- 💰 Cost-effective (~$0.01-0.05 per podcast)

## Files Created/Modified

### Core Scripts

1. **script_generator.py**
   - Standalone script generator
   - Supports OpenAI and Anthropic
   - Can output to file or stdout
   - Usage: `python script_generator.py --topic "AI" --provider openai`

2. **script_generator_node.py**
   - Dora node version
   - Integrates with dataflow
   - Accepts topic via dataflow input
   - Outputs script to downstream nodes

3. **generate_podcast.sh**
   - **Main workflow automation script**
   - Complete pipeline: topic → script → TTS → WAV
   - Usage: `./generate_podcast.sh "话题" 5 openai output.wav`
   - No manual orchestration needed!

### Dataflow Configurations

4. **dataflow-ai.yml**
   - AI-integrated dataflow (beta)
   - Includes script generator node
   - WebSocket input for topics
   - End-to-end automation

5. **dataflow-minimax.yml**
   - MiniMax T2A variant
   - Cloud-based TTS
   - No local models needed

### Documentation

6. **README.md** (updated)
   - Added AI workflow section
   - Quick start examples
   - Provider comparison
   - Usage guide

7. **.env.example** (updated)
   - Added API key variables
   - OPENAI_API_KEY
   - ANTHROPIC_API_KEY
   - MINIMAX_API_KEY

## Workflow Comparison

### Before (Manual Script)
```
User writes markdown → script_segmenter → TTS → WAV
⏱️ Time: 30 min - 2 hours
🎯 Control: Full
💰 Cost: Free (TTS models)
```

### After (AI-Generated)
```
User provides topic → LLM generates script → TTS → WAV
⚡ Time: 1-3 minutes
⚙️ Control: Minimal
💰 Cost: ~$0.01-0.05 (LLM + TTS)
```

## Quick Start

### Easiest Method (Recommended)

```bash
# Set your API key
export OPENAI_API_KEY="sk-your-key"

# Generate podcast
./generate_podcast.sh "人工智能的未来" 5 openai output/demo.wav

# That's it! Your podcast is ready.
```

### Using Docker

```bash
# Download models (one-time)
docker compose --profile setup up downloader

# Generate podcast (interactive)
docker compose run --rm podcast-generator bash -c "
  cd /opt/airos/apps/podcast-generator &&
  export OPENAI_API_KEY=your-key &&
  ./generate_podcast.sh '区块链技术' 5 openai output/blockchain.wav
"
```

### Manual Step-by-Step

```bash
# Step 1: Generate script
python script_generator.py \
    --topic '可再生能源' \
    --provider openai \
    --duration 5 \
    --output-file output/script.md

# Step 2: Start dataflow
dora up
dora build dataflow.yml
dora start dataflow.yml --name podcast-generator --detach

# Step 3: Run TTS
python voice_output.py --output-file output/energy.wav &
python script_segmenter.py --input-file output/script.md
```

## Architecture Diagram

### AI-Powered Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                     User Input                               │
│                   Topic: "AI的发展"                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              script_generator.py                             │
│              (OpenAI/Anthropic API)                          │
│  → Generates: 【大牛】...【一帆】...                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              script_segmenter.py                             │
│              (Parse & segment)                               │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌──────────────┐         ┌──────────────┐
│   大牛 TTS   │         │   一帆 TTS   │
│ (Luo Xiang)  │         │ (Doubao)     │
└──────┬───────┘         └──────┬───────┘
       │                        │
       └──────────┬─────────────┘
                  ▼
        ┌──────────────────┐
        │  voice_output.py │
        │  (Add silence)   │
        └────────┬─────────┘
                 ▼
        ┌──────────────────┐
        │   Final WAV      │
        │   (5 minutes)    │
        └──────────────────┘
```

## LLM Provider Comparison

| Provider | Model | Speed | Cost | Quality | Chinese Support |
|----------|-------|-------|------|---------|-----------------|
| OpenAI | gpt-4o-mini | ⚡⚡⚡ | 💰 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Anthropic | Claude 3.5 Sonnet | ⚡⚡ | 💰💰 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

**Recommendation:** Start with OpenAI (faster, cheaper), use Anthropic for complex topics.

## Cost Estimation

### Per 5-Minute Podcast

| Component | OpenAI | Anthropic |
|-----------|--------|-----------|
| Script Generation | ~$0.01 | ~$0.03 |
| TTS (PrimeSpeech) | Free | Free |
| **Total** | **~$0.01** | **~$0.03** |

*Prices are approximate and may vary based on content length and API updates.*

## Example Outputs

### Input
```
Topic: "ChatGPT和大型语言模型的发展"
Duration: 5 minutes
Provider: OpenAI
```

### Generated Script
```markdown
# ChatGPT和大型语言模型的发展

【大牛】大家好，欢迎来到今天的技术分享。我是大牛。今天我们要聊聊最近备受瞩目的ChatGPT和大型语言模型的发展历程。

【一帆】大家好，我是一帆。大牛，我想很多听众都对ChatGPT感到非常好奇，能先给我们介绍一下什么是大型语言模型吗？

【大牛】当然！大型语言模型是一种基于深度学习的人工智能系统...
```

### Output
- **File:** `output/chatgpt_podcast.wav`
- **Duration:** ~5 minutes
- **Format:** 16-bit PCM WAV, 32kHz
- **Voices:** Luo Xiang (大牛), Doubao (一帆)
- **Features:** Natural conversation, silence padding

## Use Cases

### Educational Content
- Create teaching materials on any topic
- Explain complex concepts in simple terms
- Multiple languages supported

### Content Creation
- Generate podcast episodes quickly
- A/B test different topics
-批量生产内容

### Prototyping
- Test podcast ideas before recording
- Rapid iteration on content
- Low-cost content validation

### Entertainment
- Generate stories with multiple characters
- Create fictional conversations
- Interactive storytelling

## Next Steps

### Planned Enhancements
- [ ] Voice cloning integration
- [ ] Multi-language support
- [ ] Custom voice personalities
- [ ] Background music integration
- [ ] Automatic transcription
- [ ] Content filtering/moderation
- [ ] Batch generation mode
- [ ] Web UI for easy access

### Integration Ideas
- [ ] Connect to news APIs for daily podcasts
- [ ] Integrate with knowledge bases
- [ ] Add citation support
- [ ] Implement fact-checking
- [ ] Add emotion/sentiment control
- [ ] Customizable speaking styles

## Troubleshooting

### API Key Issues
```bash
# Check if key is set
echo $OPENAI_API_KEY

# Should output: sk-...
```

### Rate Limiting
- OpenAI: ~3,500 requests/minute (tier 1)
- Anthropic: ~1,000 requests/minute
- Script generation: ~1 request per podcast

### Content Quality
If generated script is poor:
- Try different topic phrasing
- Adjust duration (longer = better content)
- Try different LLM provider
- Add more specific details in topic

## Resources

- [OpenAI API Docs](https://platform.openai.com/docs)
- [Anthropic API Docs](https://docs.anthropic.com)
- [PrimeSpeech Documentation](https://github.com/dora-rs/dora)
- [Dora Framework](https://dora-rs.ai)

## Credits

- Base implementation: Dora Framework
- AI Integration: OpenAI GPT-4o-mini, Anthropic Claude 3.5 Sonnet
- TTS: PrimeSpeech (Dora)
- Enhancement: Airos Voice Agent Team

---

**Enjoy creating AI-powered podcasts!** 🎙️✨
