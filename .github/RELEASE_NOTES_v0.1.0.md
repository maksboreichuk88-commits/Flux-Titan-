# Release Notes - v0.1.0 🚀

Welcome to the first official open-source release of **Flux-Titan**!

Flux-Titan is a self-hosted RSS-to-Telegram automation toolkit designed to help you build your own AI-powered news channels with ease.

### ✨ Key Features
- **Smart Summarization:** Uses Google Gemini to turn long articles into concise, engaging Telegram posts.
- **Image Extraction:** Automatically finds and attaches cover images to your posts.
- **Deduplication:** Integrated SQLite database ensures no duplicate posts.
- **Serverless Ready:** Built-in support for running via GitHub Actions (no server required!).
- **Standardized Python Package:** Easy installation via `pip`.

### 🛠️ Changes in this release
- Initial public release of the core pipeline.
- Added GitHub Actions workflow for automated hourly runs.
- Added contributor templates (Bug Reports, Feature Requests).
- Included comprehensive documentation and usage examples.

### 🚀 Getting Started
1. Fork the repository.
2. Set up your secrets (`TG_TOKEN`, `CHANNEL_ID`, `GEMINI_API_KEY`).
3. Enable GitHub Actions or run locally with `pip install . && flux-titan`.

---
*Built with ❤️ for the open-source community.*
