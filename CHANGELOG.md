# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Repositioned Flux-Titan as a self-hosted AI newsroom for Telegram channels
- Reworked README and package metadata around the collect -> filter -> rewrite -> attach image -> publish workflow
- Aligned AI backend wording around Gemini and OpenAI-compatible backends
- Added a public roadmap and newsroom-aligned issue drafts for the next stage of development

## [0.1.0] - 2026-03-07

### Initial Public OSS Release
Flux-Titan was packaged as an early open-source self-hosted Telegram newsroom pipeline.

This is an early-stage public release focused on maintainability, reuse, and simple self-hosted deployment.

### What's Included
- reusable Python package structure
- CLI entry point
- GitHub Actions automation workflow
- CI test workflow
- contributor documentation
- security policy
- AGENTS.md instructions for coding agents
- improved repository hygiene for OSS maintenance
- support for Gemini and OpenAI-style summarization backends
- YAML-based feed configuration
- Docker support

### Added
- Standardized open-source repository structure (LICENSE, CONTRIBUTING, SECURITY)
- AI-Agent instructions (`AGENTS.md`)
- Centralized `pyproject.toml` configuration
- New CLI orchestrator (`flux_titan.cli.run_cli`)
- Core Telegram newsroom pipeline with AI summarization
- Pytest integration and GitHub Actions CI workflow
- Self-hosting examples configuration (`tech_news.env`, `crypto_monitor.env`)

### Changed
- Re-architected project into a clear installable package inside `src/flux_titan/`
- Adapted Github Actions workflow to new architecture
- Made DB commit logic optional to keep git history clean

### Removed
- Legacy files, tests, and unrelated subdirectories (e.g., `opus-sync/`, `extensions/`)
- IDE/environment specific configurations (`argv.json`)
