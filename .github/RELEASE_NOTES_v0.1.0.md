# Release Notes - v0.1.0

Flux-Titan is an early-stage open-source release of a self-hosted AI newsroom for Telegram channels.

The project is designed for a narrow workflow:

1. collect news from selected sources
2. filter duplicates and lightweight weak items
3. rewrite items into Telegram-ready posts
4. attach images
5. publish automatically

## What is included in v0.1.0

- a lightweight one-shot pipeline for Telegram publishing
- AI summarization support
- image extraction from source pages
- local SQLite state for deduplication
- GitHub Actions and Docker entry points for self-hosted runs
- contributor documentation, issue templates, and a test suite

## Notes on scope

Flux-Titan is intentionally small.
It is not a hosted platform, not a multi-channel publisher, and not a dashboard product.

## Getting started

1. Fork or clone the repository
2. Set up your secrets and `.env` values (`TG_TOKEN`, `CHANNEL_ID`, and your AI backend credentials)
3. Run locally with `pip install -e . && flux-titan` or schedule the included GitHub Actions workflow
