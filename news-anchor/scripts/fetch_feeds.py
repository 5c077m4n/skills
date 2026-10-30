#!/usr/bin/env python3
"""Fetch headlines from the configured RSS sources.

feedparser fetches and parses each feed (gzip/Atom/RSS handled internally);
entries are validated with pydantic. Runs via uv (deps declared in
pyproject.toml). Prints a plain-text digest grouped by source that the agent
summarizes for the user.

Usage:
  fetch_feeds.py                 # all sources, N items each
  fetch_feeds.py --source YNet   # a single source
  fetch_feeds.py --limit 5       # items per source
"""

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated

import feedparser
from pydantic import BaseModel, Field

ALL_SOURCES = {
    "Israel Hayom": "https://www.israelhayom.co.il/rss.xml",
    "YNet": "https://www.ynet.co.il/Integration/StoryRss2.xml",
    "Walla": "https://rss.walla.co.il/feed/1",
    "Walla World": "https://rss.walla.co.il/feed/2",
    "Cyber Security News": "https://rss.app/feeds/Ho4gIVhEXQwiIoOx.xml",
    "Reuters via Google": (
        "https://news.google.com/rss/search?q=when:24h+site:reuters.com" + "&ceid=US:en&hl=en-US&gl=US"
    ),
    "BeepingComputer": "https://www.bleepingcomputer.com/feed/",
    "Hacker News": "https://news.ycombinator.com/rss",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Lobsters": "https://lobste.rs/top/rss",
}

USER_AGENT = "Mozilla/5.0 (compatible; HermesNewsAnchor/1.0)"


class FeedItem(BaseModel):
    title: Annotated[str, Field(default="")]
    link: Annotated[str, Field(default="")]


class FeedPage(BaseModel):
    items: Annotated[list[FeedItem], Field(default_factory=list)]


def fetch_source(name: str, url: str, limit: int) -> tuple[str, str]:
    """Return (source_name, formatted_items). Never raises."""
    try:
        parsed = feedparser.parse(url, agent=USER_AGENT)
    except OSError as exc:
        return name, f"  [error fetching {url}: {exc}]"

    page = FeedPage.model_validate(
        {"items": [{"title": e.get("title", ""), "link": e.get("link", "")} for e in parsed.entries[:limit]]}
    )

    lines = [f"  - {item.title}\n    {item.link}" for item in page.items]
    if not lines:
        return name, "  [no items found]"
    return name, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch RSS headlines")
    parser.add_argument("--source", help="fetch only this source (exact name)")
    parser.add_argument("--limit", type=int, default=8, help="items per source")
    parser.add_argument("--list", action="store_true", help="list source names")
    args = parser.parse_args()

    if args.list:
        for name in ALL_SOURCES:
            print(name)
        return 0

    sources = ALL_SOURCES
    if args.source:
        if args.source not in ALL_SOURCES:
            print(
                f"Unknown source {args.source!r}. Available: " + ", ".join(ALL_SOURCES),
                file=sys.stderr,
            )
            return 1
        sources = {args.source: ALL_SOURCES[args.source]}

    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        futures = [pool.submit(fetch_source, n, u, args.limit) for n, u in sources.items()]
        for name, body in (f.result() for f in futures):
            print(f"\n[{name}]\n{body}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
