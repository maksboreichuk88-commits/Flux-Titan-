import logging
import os
from unittest.mock import patch

import pytest
import yaml

from flux_titan.config import (
    Config,
    DEFAULT_RSS_FEEDS,
    KIMI_COMPATIBLE_BASE_URL,
    OPENAI_COMPATIBLE_PROVIDER,
)


@pytest.fixture
def temp_yaml_feeds(tmp_path):
    yaml_file = tmp_path / "test_feeds.yaml"
    content = {
        "feeds": [
            {"name": "YAML Feed", "url": "https://yaml.com/rss", "icon": "memo"}
        ]
    }
    with open(yaml_file, "w", encoding="utf-8") as f:
        yaml.dump(content, f)
    return str(yaml_file)


def test_config_load_yaml_only(temp_yaml_feeds):
    with patch.dict(os.environ, {
        "TG_TOKEN": "test_token",
        "CHANNEL_ID": "test_channel",
        "GEMINI_API_KEY": "test_key",
        "FEEDS_CONFIG_PATH": temp_yaml_feeds,
        "CUSTOM_RSS_FEEDS": ""
    }, clear=True):
        config = Config.from_env()
        assert len(config.rss_feeds) == len(DEFAULT_RSS_FEEDS) + 1
        assert any(f["name"] == "YAML Feed" for f in config.rss_feeds)


def test_config_load_env_only():
    with patch.dict(os.environ, {
        "TG_TOKEN": "test_token",
        "CHANNEL_ID": "test_channel",
        "GEMINI_API_KEY": "test_key",
        "FEEDS_CONFIG_PATH": "non_existent.yaml",
        "CUSTOM_RSS_FEEDS": "ENV Feed|https://env.com/rss|globe"
    }, clear=True):
        config = Config.from_env()
        assert len(config.rss_feeds) == len(DEFAULT_RSS_FEEDS) + 1
        assert any(f["name"] == "ENV Feed" for f in config.rss_feeds)


def test_config_merge_all(temp_yaml_feeds):
    with patch.dict(os.environ, {
        "TG_TOKEN": "test_token",
        "CHANNEL_ID": "test_channel",
        "GEMINI_API_KEY": "test_key",
        "FEEDS_CONFIG_PATH": temp_yaml_feeds,
        "CUSTOM_RSS_FEEDS": "ENV Feed|https://env.com/rss|globe"
    }, clear=True):
        config = Config.from_env()
        expected_len = len(DEFAULT_RSS_FEEDS) + 2
        assert len(config.rss_feeds) == expected_len
        assert any(f["name"] == "YAML Feed" for f in config.rss_feeds)
        assert any(f["name"] == "ENV Feed" for f in config.rss_feeds)


def test_openai_compatible_base_url_config():
    with patch.dict(os.environ, {
        "TG_TOKEN": "test_token",
        "CHANNEL_ID": "test_channel",
        "AI_PROVIDER": OPENAI_COMPATIBLE_PROVIDER,
        "OPENAI_API_KEY": "openai_key",
        "OPENAI_MODEL": "gpt-test",
        "OPENAI_BASE_URL": "https://example.com/v1",
    }, clear=True):
        config = Config.from_env()

    assert config.ai_provider == OPENAI_COMPATIBLE_PROVIDER
    assert config.ai_provider_input == OPENAI_COMPATIBLE_PROVIDER
    assert config.openai_api_key == "openai_key"
    assert config.openai_model == "gpt-test"
    assert config.openai_base_url == "https://example.com/v1"


def test_openai_alias_normalization():
    with patch.dict(os.environ, {
        "TG_TOKEN": "test_token",
        "CHANNEL_ID": "test_channel",
        "AI_PROVIDER": "openai",
        "OPENAI_API_KEY": "openai_key",
    }, clear=True):
        config = Config.from_env()

    assert config.ai_provider == OPENAI_COMPATIBLE_PROVIDER
    assert config.ai_provider_input == "openai"
    assert config.openai_api_key == "openai_key"
    assert config.openai_base_url == ""


def test_kimi_alias_uses_compat_fallbacks(caplog):
    with patch.dict(os.environ, {
        "TG_TOKEN": "test_token",
        "CHANNEL_ID": "test_channel",
        "AI_PROVIDER": "kimi",
        "KIMI_API_KEY": "kimi_key",
        "KIMI_MODEL": "kimi-k2.5",
    }, clear=True):
        with caplog.at_level(logging.WARNING, logger="NewsBot.Config"):
            config = Config.from_env()

    assert config.ai_provider == OPENAI_COMPATIBLE_PROVIDER
    assert config.ai_provider_input == "kimi"
    assert config.openai_api_key == "kimi_key"
    assert config.openai_model == "kimi-k2.5"
    assert config.openai_base_url == KIMI_COMPATIBLE_BASE_URL
    assert "Prefer AI_PROVIDER=openai_compatible" in caplog.text


def test_kimi_alias_prefers_explicit_openai_values():
    with patch.dict(os.environ, {
        "TG_TOKEN": "test_token",
        "CHANNEL_ID": "test_channel",
        "AI_PROVIDER": "kimi",
        "OPENAI_API_KEY": "openai_key",
        "OPENAI_MODEL": "custom-model",
        "OPENAI_BASE_URL": "https://custom.example/v1",
        "KIMI_API_KEY": "kimi_key",
        "KIMI_MODEL": "kimi-k2.5",
    }, clear=True):
        config = Config.from_env()

    assert config.ai_provider == OPENAI_COMPATIBLE_PROVIDER
    assert config.openai_api_key == "openai_key"
    assert config.openai_model == "custom-model"
    assert config.openai_base_url == "https://custom.example/v1"
