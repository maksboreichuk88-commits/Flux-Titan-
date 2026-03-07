import os
import pytest
import yaml
from unittest.mock import patch
from flux_titan.config import Config, DEFAULT_RSS_FEEDS

@pytest.fixture
def temp_yaml_feeds(tmp_path):
    yaml_file = tmp_path / "test_feeds.yaml"
    content = {
        "feeds": [
            {"name": "YAML Feed", "url": "https://yaml.com/rss", "icon": "📝"}
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
    }):
        config = Config.from_env()
        # Should have DEFAULT_RSS_FEEDS + 1 from YAML
        assert len(config.rss_feeds) == len(DEFAULT_RSS_FEEDS) + 1
        assert any(f["name"] == "YAML Feed" for f in config.rss_feeds)

def test_config_load_env_only():
    with patch.dict(os.environ, {
        "TG_TOKEN": "test_token",
        "CHANNEL_ID": "test_channel",
        "GEMINI_API_KEY": "test_key",
        "FEEDS_CONFIG_PATH": "non_existent.yaml",
        "CUSTOM_RSS_FEEDS": "ENV Feed|https://env.com/rss|🌐"
    }):
        config = Config.from_env()
        # Should have DEFAULT_RSS_FEEDS + 1 from ENV
        assert len(config.rss_feeds) == len(DEFAULT_RSS_FEEDS) + 1
        assert any(f["name"] == "ENV Feed" for f in config.rss_feeds)

def test_config_merge_all(temp_yaml_feeds):
    with patch.dict(os.environ, {
        "TG_TOKEN": "test_token",
        "CHANNEL_ID": "test_channel",
        "GEMINI_API_KEY": "test_key",
        "FEEDS_CONFIG_PATH": temp_yaml_feeds,
        "CUSTOM_RSS_FEEDS": "ENV Feed|https://env.com/rss|🌐"
    }):
        config = Config.from_env()
        # Should have DEFAULT_RSS_FEEDS + 1 (YAML) + 1 (ENV)
        expected_len = len(DEFAULT_RSS_FEEDS) + 2
        assert len(config.rss_feeds) == expected_len
        assert any(f["name"] == "YAML Feed" for f in config.rss_feeds)
        assert any(f["name"] == "ENV Feed" for f in config.rss_feeds)
