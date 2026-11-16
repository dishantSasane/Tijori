"""Real `NewsFeed` implementation: polls RSS 2.0 feeds (free, no API key).
Stdlib only (`urllib` + `xml.etree`) -- no new dependency for what a few
lines of parsing does (ponytail rung 3/5). Default feed list is a reputable
financial RSS plus NSE's own announcements page; both are configurable
since the owner may swap sources later without touching code.

Fetched text is untrusted (AGENTS.md §4.6) -- this module only parses XML
into plain-string fields of `NewsItem`; it never evaluates, templates, or
executes anything from the feed, and the Brain prompt layer (`brain/prompt.py`)
is responsible for delimiting it before it reaches an LLM.
"""

from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import datetime
from email.utils import parsedate_to_datetime

from trading.adapters.news_feed import NewsItem

DEFAULT_FEEDS = (
    "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml",
    "https://www.moneycontrol.com/rss/marketreports.xml",
)

Fetcher = Callable[[str], bytes]


def _urllib_fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "tijori-trading-bot/0.1"})
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 - fixed http(s) feed URLs
        return bytes(resp.read())


class RSSNewsFeed:
    """Polls each feed URL and returns items newer than `since`. A feed that
    fails to fetch or parse is skipped (logged by the caller, not raised) --
    a dead news source must never block the trading loop (AGENTS.md §4.2,
    fail closed means "stop opening new positions", not "crash").
    """

    def __init__(
        self, feed_urls: tuple[str, ...] = DEFAULT_FEEDS, *, fetch: Fetcher = _urllib_fetch
    ) -> None:
        self._feed_urls = feed_urls
        self._fetch = fetch

    def fetch_since(self, since: datetime) -> list[NewsItem]:
        items: list[NewsItem] = []
        for url in self._feed_urls:
            try:
                items.extend(self._parse_feed(url, since))
            except Exception:  # noqa: BLE001 - one bad feed must not take down news polling
                continue
        return items

    def _parse_feed(self, url: str, since: datetime) -> list[NewsItem]:
        raw = self._fetch(url)
        root = ET.fromstring(raw)  # noqa: S314 - RSS from a fixed, operator-chosen URL list
        out: list[NewsItem] = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            if not title:
                continue
            description = (item.findtext("description") or "").strip()
            pub_date_raw = item.findtext("pubDate")
            ts = _parse_pubdate(pub_date_raw)
            if ts is None or ts <= since:
                continue
            out.append(NewsItem(ts_utc=ts, source=url, headline=title, body=description))
        return out


def _parse_pubdate(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
