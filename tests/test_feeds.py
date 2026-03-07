import pytest
from datetime import datetime
from flux_titan.feeds import RSSParser

def test_clean_html_removes_tags_and_entities():
    raw_html = "<p>Hello <b>world</b>! This is a &quot;test&quot; with &amp; entities.</p>\n<br>"
    cleaned = RSSParser._clean_html(raw_html)
    
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert "Hello world ! This is a \"test\" with & entities." == cleaned

def test_clean_html_handles_empty_input():
    assert RSSParser._clean_html(None) == ""
    assert RSSParser._clean_html("") == ""

def test_clean_text_normalizes_whitespace():
    raw_text = "   Title   \nwith\t\t tabs and \nnewlines   "
    cleaned = RSSParser._clean_text(raw_text)
    
    assert cleaned == "Title with tabs and newlines"

def test_parse_date_fallback():
    # If the date string is completely garbage or missing, it should return roughly 'now'
    date_now = datetime.now()
    parsed_none = RSSParser._parse_date(None)
    parsed_garbage = RSSParser._parse_date("not a real date string")
    
    # They should evaluate to a datetime closely matching the current time
    assert isinstance(parsed_none, datetime)
    assert isinstance(parsed_garbage, datetime)
    
    # The gap should be virtually 0 seconds
    assert (parsed_none - date_now).total_seconds() < 5
    assert (parsed_garbage - date_now).total_seconds() < 5

