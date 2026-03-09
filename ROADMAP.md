# Roadmap

Flux-Titan is being developed as a self-hosted AI newsroom for Telegram channels.
The roadmap stays intentionally narrow: selected sources in, Telegram posts out.

## Reliability

- Keep processed state across scheduled newsroom runs
- Harden RSS ingestion against malformed or partial feeds
- Improve failure handling only where it protects newsroom continuity

## Newsroom Workflows

- Add source priority scoring for selected feeds
- Add image fallback chain for Telegram posts
- Add digest mode for grouped Telegram posting

## Provider Flexibility

- Add OpenAI-compatible base URL support
- Keep backend flexibility narrow and configuration-driven

## Human-in-the-Loop Improvements

- Add manual approval mode before publish
- Keep approval lightweight and Telegram-first
