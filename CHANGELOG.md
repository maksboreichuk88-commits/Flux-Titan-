# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-07

### Initial Release
This marks the first official open-source release of Flux-Titan.

### Added
- Standardized open-source repository structure (LICENSE, CONTRIBUTING, SECURITY)
- AI-Agent instructions (`AGENTS.md`)
- Centralized `pyproject.toml` configuration
- New CLI orchestrator (`flux_titan.cli.run_cli`)
- Core RSS-to-Telegram pipeline with Gemini Summarization
- Pytest integration and GitHub Actions CI workflow
- Self-hosting examples configuration (`tech_news.env`, `crypto_monitor.env`)

### Changed
- Re-architected project into a clear installable package inside `src/flux_titan/`
- Adapted Github Actions workflow to new architecture
- Made DB commit logic optional to keep git history clean

### Removed
- Legacy files, tests, and unrelated subdirectories (e.g., `opus-sync/`, `extensions/`)
- IDE/environment specific configurations (`argv.json`)
