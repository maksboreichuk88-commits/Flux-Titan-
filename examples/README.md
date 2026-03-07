# Flux-Titan Examples

This directory contains practical, reusable examples for configuring and hosting your own instance of the Flux-Titan bot.

## Available Examples

*   **[`tech_news.env`](tech_news.env)**: A configuration tailored for aggregating popular technology news feeds (TechCrunch, The Verge, Wired).
*   **[`crypto_monitor.env`](crypto_monitor.env)**: A configuration tailored for tracking cryptocurrency news and market updates.

## How to use an example

1. Choose the example that best fits your use-case.
2. Copy its contents into the `.env` file at the root of the project:
   ```bash
   cp examples/tech_news.env ./.env
   ```
3. Open your new `.env` file and replace the placeholder API keys (`your_telegram_bot_token_here`, `your_channel_id_here`, `your_gemini_api_key_here`) with your actual real credentials.
4. Run the bot!
   ```bash
   flux-titan
   ```

5. (Optional, recommended) Start from the YAML feeds template:
   ```bash
   cp examples/feeds.yaml ./feeds.yaml
   ```

This keeps feed sources in a versionable file (`FEEDS_CONFIG_PATH=feeds.yaml`) and works the same locally, in Docker, and in GitHub Actions.

*(If you are deploying on GitHub Actions, just copy the `CUSTOM_RSS_FEEDS` string from the example and paste it directly into your GitHub Actions Repository Variables).*
