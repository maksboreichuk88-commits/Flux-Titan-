# Flux-Titan Examples

This directory contains reusable environment examples for running a small Telegram newsroom with Flux-Titan.

## Available examples

- [`tech_news.env`](tech_news.env): a technology newsroom example using an OpenAI-compatible backend
- [`crypto_monitor.env`](crypto_monitor.env): a crypto newsroom example using Gemini

## How to use an example

1. Choose the example that is closest to your newsroom setup.
2. Copy it into the project root as `.env`.
3. Replace the placeholder Telegram and AI backend credentials.
4. Adjust sources and article limits if needed.
5. Run one newsroom pass with `flux-titan`.

```bash
cp examples/tech_news.env .env
flux-titan
```

If you run Flux-Titan through GitHub Actions, copy the relevant environment values into repository secrets instead of committing them to the repository.
