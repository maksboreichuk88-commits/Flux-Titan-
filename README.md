# Flux-Titan

> Self-hosted AI newsroom for Telegram channels.
>
> Turn selected news sources into ready-to-publish Telegram posts with AI summarization.

Flux-Titan is a focused, early-stage open-source tool for running a small Telegram newsroom from selected sources.
It collects news, filters duplicates and lightweight weak items, rewrites stronger items into Telegram-ready posts, attaches images, and publishes automatically.

It is intentionally narrow:
- Telegram is the only output channel.
- The runtime is a one-shot pipeline you can schedule with cron or GitHub Actions.
- Ranking and filtering are practical but still lightweight today.

## How It Works

1. Collect from selected sources
2. Filter duplicates and weak items
3. Rewrite into Telegram-ready posts
4. Attach images
5. Publish automatically

## Quick Start

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
flux-titan
```

What you need before the first run:
- a Telegram bot token
- a Telegram channel or chat ID
- one AI backend credential set

## Preview

Screenshot placeholder: no real screenshot is committed yet.

GIF/demo placeholder: no demo asset is committed yet.

## Who Is This For?

Flux-Titan is for:

- a small Telegram channel operator who wants selected sources turned into publishable posts
- a niche community digest operator who needs a lightweight scheduled editorial flow
- a solo operator or small team running a self-hosted newsroom pipeline

It is not trying to be:

- a SaaS product
- a media platform
- a dashboard-heavy editorial suite
- a multi-channel publisher
- a general-purpose AI agent framework

## Example Output

Illustrative example only. This is not a screenshot, benchmark, or claim about a specific live channel.

```html
<b>AI coding tools move closer to team workflows</b>

Several developer tool vendors are shifting from standalone chat interfaces toward source-aware workflows tied to real repositories. For Telegram channels, that matters because it turns product updates into clearer operational news instead of abstract AI hype.

#AI #DevTools
<a href="https://example.com/story">Source</a>
```

## What It Is

Flux-Titan is a self-hosted newsroom workflow for Telegram channels.
It is built for operators who want a small, controllable pipeline instead of a hosted product, web dashboard, or multi-platform publishing system.

The current workflow is:

1. Collect news from selected sources
2. Filter duplicates and weak items
3. Rewrite news into Telegram-ready posts
4. Attach images
5. Publish automatically

## Core Workflow

### 1. Collect

Flux-Titan pulls news from selected RSS feeds and small curated source lists.
Today, sources from `feeds.yaml` and `CUSTOM_RSS_FEEDS` are merged with the built-in defaults.

### 2. Filter

The project already removes duplicates through SQLite state tracking.
Weak-item filtering is still lightweight for now and mostly comes from source choice, feed ordering, and per-run limits.

### 3. Rewrite

Articles are rewritten into Telegram-ready posts through:

- `gemini`
- `openai_compatible`

Compatibility aliases remain available for existing setups:

- `openai`
- `kimi`

### 4. Attach Image

Flux-Titan attempts to attach a usable image before publishing.
The current strategy is practical rather than exhaustive and fits lightweight self-hosted runs.

### 5. Publish

The final post is sent directly to a Telegram channel or chat using a bot token.

## Image Strategy

Flux-Titan now uses a small image fallback chain.

The current active step is to prefer the original article image from page metadata such as:

- `og:image`
- `twitter:image`

If a usable image is found, it is attached to the Telegram post.
If not, Flux-Titan falls back to a text-only post so the newsroom run can still complete.

The next intended fallback is a public image source, but that is not wired in yet.
Generated images are explicitly future fallback behavior, not the default path.

## OpenAI-Compatible Backends

Flux-Titan supports two main backend paths:

- `gemini`
- `openai_compatible`

`openai_compatible` is the main path for OpenAI-style APIs.
Use it with:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- optional `OPENAI_BASE_URL`

Compatibility notes:

- `AI_PROVIDER=openai` still works as an alias
- `AI_PROVIDER=kimi` still works as an alias for existing setups
- `KIMI_API_KEY` and `KIMI_MODEL` are kept for compatibility, but new setups should prefer `openai_compatible`

## Why Self-Hosted?

Self-hosting keeps the newsroom small and controllable:

- you choose the sources
- you choose the prompts and AI backend
- you control secrets and state locally
- you can run it from a VM, local machine, container, or GitHub Actions
- you do not need a separate dashboard to operate it

## Minimal Production Setup

The smallest practical setup is:

1. Fill in `.env` with Telegram and AI backend credentials
2. Configure selected sources through `feeds.yaml` or `CUSTOM_RSS_FEEDS`
3. Persist `processed.db` between scheduled runs
4. Run `flux-titan` from one scheduler such as cron, Task Scheduler, or GitHub Actions

## Installation

Flux-Titan requires Python 3.11 or newer.

```bash
git clone https://github.com/maksboreichuk88-commits/Flux-Titan-.git
cd Flux-Titan-
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

## Configuration

Copy `.env.example` to `.env` and fill in the values you need.

### Required

- `TG_TOKEN`: Telegram bot token from [@BotFather](https://t.me/botfather)
- `CHANNEL_ID`: target Telegram channel username or numeric chat ID
- `AI_PROVIDER`: `gemini` or `openai_compatible`

### Backend Credentials

- `GEMINI_API_KEY`: required when `AI_PROVIDER=gemini`
- `OPENAI_API_KEY`: required when `AI_PROVIDER=openai_compatible`

### Optional Backend Settings

- `GEMINI_MODEL`
- `OPENAI_MODEL`
- `OPENAI_BASE_URL`: set this when using a self-hosted or third-party OpenAI-compatible backend

### Optional Runtime Settings

- `MAX_ARTICLES_PER_RUN`: cap the number of new articles per run
- `DATABASE_PATH`: path to the SQLite state file
- `FEEDS_CONFIG_PATH`: custom path to `feeds.yaml`

## Selected Sources

You can add sources in two ways.

### Option 1: `feeds.yaml`

```yaml
feeds:
  - name: "Example Source"
    url: "https://example.com/feed.xml"
    icon: "EX"
```

### Option 2: `CUSTOM_RSS_FEEDS`

```bash
CUSTOM_RSS_FEEDS="Source One|https://example.com/feed.xml|EX,Source Two|https://example.org/rss|S2"
```

## Running Flux-Titan

Run one newsroom pass:

```bash
flux-titan
```

The command will:

- load sources
- fetch recent items
- skip already processed links
- rewrite new items
- attach images where available
- publish to Telegram
- update local state in `processed.db`

Flux-Titan exits after one run. To keep it operating, schedule it with cron, Task Scheduler, or GitHub Actions.

## Docker

```bash
docker-compose up --build
```

Or run directly:

```bash
docker build -t flux-titan .
docker run --env-file .env -v $(pwd)/processed.db:/app/processed.db flux-titan
```

## GitHub Actions

The repository includes a scheduled workflow in [news_bot.yml](.github/workflows/news_bot.yml).
Use repository secrets for:

- `TG_TOKEN`
- `CHANNEL_ID`
- `AI_PROVIDER`
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` when needed

This is a good fit for lightweight scheduled newsroom runs, but it is still a one-shot job and not a persistent service.

## Example Use Cases

- small Telegram channel: turn selected tech or local industry sources into short channel posts
- niche community digest: publish grouped updates for a focused community around one topic
- self-hosted newsroom pipeline: run a controllable editorial workflow without a hosted dashboard

## Examples

See [examples/README.md](examples/README.md) for reusable environment examples.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the current product direction and newsroom backlog themes.

## Development and Testing

Install development dependencies and run the test suite:

```bash
pip install -e .[dev]
python -m pytest
```

The current test suite covers:

- configuration loading
- RSS parsing
- summarizer integrations
- Telegram publishing behavior
- end-to-end pipeline flow

## License

Flux-Titan is licensed under the MIT License. See [LICENSE](LICENSE).
