# Analytics of India

A lightweight AI-assisted news summarization pipeline + static site.

## How I recommend approaching AI integration

If Gemini has been painful, the easiest path is to make the AI layer **provider-agnostic**:

1. Keep one shared prompt/output schema.
2. Add a provider switch using env vars.
3. Start with Gemini or OpenAI interchangeably.
4. Keep graceful fallback cards so the website still loads when the AI call fails.

This repo now supports that model directly.

## AI provider configuration

`update_news.py` supports two providers via `AI_PROVIDER`:

- `gemini` (default)
- `openai`

### Option A: Gemini (default)

```bash
export AI_PROVIDER=gemini
export GEMINI_API_KEY=your_key
python update_news.py
```

### Option B: OpenAI

```bash
export AI_PROVIDER=openai
export OPENAI_API_KEY=your_key
# optional
export OPENAI_MODEL=gpt-4.1-mini
python update_news.py
```

## Install dependencies

```bash
pip install -r requirements.txt
```

## Output

Running `python update_news.py` updates `data.json`, which is read by `index.html`.
