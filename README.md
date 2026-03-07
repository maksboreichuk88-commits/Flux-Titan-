# Flux-Titan

> **A self-hosted RSS-to-Telegram automation toolkit with AI summarization.**

Flux-Titan is a lightweight, customizable pipeline designed to monitor RSS feeds, summarize articles using AI (Google Gemini by default), extract header images, and publish the curated content directly to a Telegram channel.

It is designed for simplicity, built to be run as a cron job (via GitHub Actions or locally), and avoids heavy infrastructure dependencies by using a local SQLite database for state management.

---

## 🌟 Features

*   **Multi-Source RSS Aggregation:** Monitor multiple RSS feeds simultaneously asynchronously.
*   **AI Summarization:** Built-in support for Google Gemini to rewrite long articles into concise, engaging Telegram posts. Extensible interface (`BaseSummarizer`) to add OpenAI or Claude.
*   **Smart Image Extraction:** Automatically parses HTML metadata (`og:image`, `twitter:image`) to attach cover photos to Telegram posts.
*   **Deduplication:** Prevents duplicate posts using a lightweight SQLite database to track processed articles.
*   **Serverless Deployment:** Fully compatible with GitHub Actions for hands-free, scheduled execution without hosting costs.
*   **CLI Interface:** Packaged as a standard Python tool with a robust command-line interface.

---

## 🏗️ Architecture

Flux-Titan follows a pipeline architecture, coordinating data through specific, decoupled modules:

1.  **Feeds (`flux_titan.feeds`):** Asynchronously fetches and parses RSS feeds.
2.  **Storage (`flux_titan.storage`):** Checks a local SQLite database (`processed.db`) to ensure the article hasn't been posted before.
3.  **Image Extractor (`flux_titan.image_extractor`):** Scrapes the destination URL for OpenGraph and Twitter image meta-tags.
4.  **Summarizers (`flux_titan.summarizers`):** Passes the raw article HTML/text to an AI provider (e.g., Gemini) with a specific prompt to generate a Telegram-friendly summary.
5.  **Publishers (`flux_titan.publishers`):** Posts the final text and image to the configured Telegram channel/chat.

---

## Installation

Ensure you have Python 3.11+ installed.

### Clone the Repository
```bash
git clone https://github.com/maksboreichuk88-commits/Flux-Titan-.git
cd Flux-Titan-
```

### Install the Package
Flux-Titan is packaged with `pyproject.toml`. Install it (preferably in a virtual environment) using `pip`:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -e .
```

---

## ⚙️ Configuration

Flux-Titan relies on environment variables for configuration. Copy the example file and fill in your details:

```bash
cp .env.example .env
```

### Required Variables
*   `TG_TOKEN`: Your Telegram Bot API Token (from [@BotFather](https://t.me/botfather)).
*   `CHANNEL_ID`: The target Telegram channel.
*   `AI_PROVIDER`: Choose your summarizer provider: `gemini` (default) or `openai`.
*   `GEMINI_API_KEY`: Required if `AI_PROVIDER=gemini`.
*   `OPENAI_API_KEY`: Required if `AI_PROVIDER=openai`.

### Optional Variables
*   `GEMINI_MODEL`: The Gemini model to use (default: `gemini-1.5-flash`).
*   `OPENAI_MODEL`: The OpenAI model to use (default: `gpt-4o-mini`).
*   `MAX_ARTICLES_PER_RUN`: Number of new articles to process in a single execution (default: `5`).
### RSS Feeds Configuration

You can manage your sources in two ways:

#### 1. YAML File (Recommended)
Create a `feeds.yaml` in the project root. Flux-Titan will automatically detect it:
```yaml
feeds:
  - name: "Flux-Titan Dev"
    url: "https://github.com/maksboreichuk88-commits/Flux-Titan-/commits/main.atom"
    icon: "🚀"
```
*Specify a custom path via `FEEDS_CONFIG_PATH` if needed.*

#### 2. Environment Variable
Use `CUSTOM_RSS_FEEDS` for quick setups:
```bash
CUSTOM_RSS_FEEDS="Name1|URL1|Icon1,Name2|URL2|Icon2"
```

*Note: Sources from YAML and ENV are merged with the default feeds.*

---

## 💻 Local Usage

Once installed and configured, you can run the bot locally via the command-line interface:

```bash
flux-titan
```

The bot will execute a single run, process any new articles up to the limit defined by `MAX_ARTICLES_PER_RUN`, update the local SQLite database, and exit. To run it continuously, set up a cron job or a scheduled task on your local machine to execute `flux-titan` at your preferred interval.

---

## 🐳 Docker Deployment

For self-hosted environments, you can run Flux-Titan using Docker.

### Using Docker Compose (Recommended)

1.  Make sure you have [Docker](https://docs.docker.com/get-docker/) installed.
2.  Prepare your `.env` file from the template.
3.  Run the bot:
    ```bash
    docker-compose up --build
    ```

### Using Docker Directly

```bash
docker build -t flux-titan .
docker run --env-file .env -v $(pwd)/processed.db:/app/processed.db flux-titan
```

*Note: Since the bot is a one-shot execution tool, the container will exit after processing articles. Use a scheduler (like `cron` on the host) to run the container periodically.*

---

## ☁️ GitHub Actions Usage

Flux-Titan is perfectly suited to run on GitHub Actions automatically on a schedule, saving you the need for a 24/7 server.

1.  Fork or clone this repository to your GitHub account.
2.  Go to your repository **Settings > Secrets and variables > Actions**.
3.  Add the following **Repository Secrets**:
    *   `TG_TOKEN`
    *   `CHANNEL_ID`
    *   `GEMINI_API_KEY`
4.  The provided workflow in `.github/workflows/news_bot.yml` is configured to run automatically at the top of every hour (`cron: '0 * * * *'`).
5.  *(Optional)* You can manually trigger a run via the **Actions** tab on GitHub by clicking **Run workflow**.

*Note: Since the GitHub Actions runner provides a fresh environment every time, the SQLite database state will not persist between automated runs unless you configure an external storage/cache strategy in the workflow. Alternatively, limit `MAX_ARTICLES_PER_RUN` and accept that older articles might not be historically tracked across runs.*

---

## 📊 Example Use Cases

*   **Niche Tech News:** Aggregate feeds from your favorite tech blogs, let Gemini translate and summarize them into a consistent format, and publish to your personal tech channel.
*   **Crypto Monitoring:** Track crypto news sites and quickly broadcast summarized breaking news to a trading community.
*   **Internal Company Updates:** Parse industry news and summarize it for an internal Slack/Telegram group.

---

## 📁 Project Structure

```text
Flux-Titan-/
├── .github/workflows/  # GitHub Actions CI/CD pipelines
├── src/flux_titan/     # Main package directory
│   ├── cli.py          # Unified CLI entry point & Orchestrator
│   ├── config.py       # Environment configuration loading
│   ├── feeds.py        # Async RSS parsing
│   ├── image_extractor.py # HTML meta-tag image extraction
│   ├── publishers/     # Output destinations (Telegram)
│   ├── storage/        # State persistence (SQLite)
│   └── summarizers/    # AI processing routines (Gemini & Abstract Base)
├── main.py             # Legacy entry point (wraps flux_titan.cli)
├── pyproject.toml      # Project packaging and dependencies
├── .env.example        # Template for configuration
└── requirements.txt    # Forwarding pip requirements for legacy compatibility
```

---

## 🤝 Contributing

Contributions are welcome! If you'd like to add a new Summarizer (e.g., OpenAI, Anthropic), a new Publisher (e.g., Discord, Slack), or improve the core logic:

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/amazing-feature`).
3.  Commit your changes (`git commit -m 'Add amazing feature'`).
4.  Push to the branch (`git push origin feature/amazing-feature`).
5.  Open a Pull Request.

Please ensure your code follows standard Python conventions (PEP 8) and type hints are used.

---

## 🛠️ Development & Testing

Flux-Titan includes a comprehensive test suite covering RSS parsing, AI summarization providers, and Telegram publishing.

### Running Tests
To run all tests locally, make sure you have dev dependencies installed:
```bash
pip install -e .[dev]
python -m pytest
```

The test suite includes:
*   `tests/test_summarizer_integration.py`: Integration tests for Gemini and OpenAI providers.
*   `tests/test_telegram_integration.py`: Tests for message formatting and Telegram API interaction.
*   `tests/test_bot_e2e.py`: End-to-end execution path for the entire bot flow.
*   `tests/test_config_yaml.py`: Configuration and feed merging logic.

*Note: All external API calls are mocked during tests. No credits or API quotas are consumed.*

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
