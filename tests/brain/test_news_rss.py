from __future__ import annotations

from datetime import UTC, datetime

from trading.brain.news_rss import RSSNewsFeed

SAMPLE_RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
<item>
  <title>Market update: Nifty closes higher</title>
  <description>Some body text</description>
  <pubDate>Mon, 02 Jun 2026 10:00:00 GMT</pubDate>
</item>
<item>
  <title>Old news item</title>
  <description>stale</description>
  <pubDate>Mon, 02 Jun 2025 10:00:00 GMT</pubDate>
</item>
</channel></rss>
"""

BROKEN_RSS = b"not even xml"


def test_parses_items_newer_than_since():
    feed = RSSNewsFeed(("fake://feed",), fetch=lambda url: SAMPLE_RSS)
    since = datetime(2026, 1, 1, tzinfo=UTC)
    items = feed.fetch_since(since)
    assert len(items) == 1
    assert items[0].headline == "Market update: Nifty closes higher"
    assert items[0].body == "Some body text"


def test_items_older_than_since_are_excluded():
    feed = RSSNewsFeed(("fake://feed",), fetch=lambda url: SAMPLE_RSS)
    since = datetime(2026, 6, 1, tzinfo=UTC)
    items = feed.fetch_since(since)
    assert all(item.ts_utc > since for item in items)


def test_broken_feed_is_skipped_not_raised():
    feed = RSSNewsFeed(("fake://feed",), fetch=lambda url: BROKEN_RSS)
    items = feed.fetch_since(datetime(2020, 1, 1, tzinfo=UTC))
    assert items == []


def test_one_broken_feed_does_not_block_a_good_one():
    def fetch(url: str) -> bytes:
        if url == "good":
            return SAMPLE_RSS
        raise ConnectionError("down")

    feed = RSSNewsFeed(("bad", "good"), fetch=fetch)
    items = feed.fetch_since(datetime(2026, 1, 1, tzinfo=UTC))
    assert len(items) == 1


def test_headline_text_is_opaque_data_not_interpreted():
    """A news item is just a NewsItem with plain-string fields -- nothing in
    this adapter evaluates or templates the text (AGENTS.md §4.6). RSS
    escapes markup as entities, which XML parsing decodes back to literal
    text -- it never becomes live HTML/script content here."""
    injected = SAMPLE_RSS.replace(
        b"Market update: Nifty closes higher", b"&lt;script&gt;alert(1)&lt;/script&gt;"
    )
    feed = RSSNewsFeed(("fake://feed",), fetch=lambda url: injected)
    items = feed.fetch_since(datetime(2026, 1, 1, tzinfo=UTC))
    assert items[0].headline == "<script>alert(1)</script>"
