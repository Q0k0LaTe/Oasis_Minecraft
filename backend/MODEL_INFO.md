# AI Model Configuration

## Current Model: GPT-4o

The backend is configured to use **GPT-4o**, which is OpenAI's latest and most powerful model as of January 2025.

## Available Models

### GPT-4o (Current)
- **Best for**: Highest quality, most intelligent decisions
- **Cost**: ~$0.01-$0.03 per mod
- **Recommended**: Production use, best user experience

### GPT-4o-mini
- **Best for**: Cost efficiency while maintaining good quality
- **Cost**: ~$0.001-$0.003 per mod (10x cheaper!)
- **Recommended**: Development, high-volume use

### GPT-4-turbo
- **Best for**: Balance of speed and quality
- **Cost**: ~$0.01-$0.02 per mod
- **Recommended**: Alternative to GPT-4o

## How to Change Models

Edit `backend/config.py`:

```python
# For best quality (current setting)
AI_MODEL = "gpt-4o"

# For cost efficiency
AI_MODEL = "gpt-4o-mini"

# For legacy support
AI_MODEL = "gpt-4-turbo"
```

## Note About GPT-5

As of January 2025, **GPT-5 has not been released** by OpenAI. The latest available models are:
- GPT-4o (newest, released 2024)
- GPT-4-turbo
- GPT-4

If you see references to "GPT-5", they are speculative or unofficial. When GPT-5 is released, you can update this configuration file to use it.

## Performance Comparison

| Model | Quality | Speed | Cost/Mod | Best For |
|-------|---------|-------|----------|----------|
| GPT-4o | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | $0.01-0.03 | Production |
| GPT-4o-mini | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $0.001-0.003 | High volume |
| GPT-4-turbo | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | $0.01-0.02 | Alternative |

## Recommendation

**Use GPT-4o** (current setting) for:
- Best user experience
- Most intelligent property decisions
- Better understanding of complex prompts
- Production deployments

**Switch to GPT-4o-mini** if you need:
- Lower costs (10x cheaper)
- Higher throughput
- Still good quality for most use cases

## Testing Different Models

You can easily test different models:

```bash
# Edit config.py
nano backend/config.py

# Change AI_MODEL = "gpt-4o" to AI_MODEL = "gpt-4o-mini"

# Restart backend
cd backend
python main.py
```

Compare the results and choose what works best for your use case!
