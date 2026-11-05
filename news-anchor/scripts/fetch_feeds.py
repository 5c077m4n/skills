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
  fetch_feeds.py --hours 6       # only items from the last 6 hours
"""

import asyncio
import sys
from collections import namedtuple
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from urllib.parse import urlencode, urlunparse

import feedparser
from pydantic import BaseModel, Field, ValidationError, ValidationInfo, model_validator
from pydantic_settings import BaseSettings, CliImplicitFlag, SettingsConfigDict

URLParts = namedtuple(
    typename="URLParts",
    field_names=["scheme", "netloc", "url", "path", "query", "fragment"],
    defaults=("", "", ""),
)

ALL_SOURCES: dict[str, str | bytes] = {
    "Israel Hayom": urlunparse(URLParts(scheme="https", netloc="www.israelhayom.co.il", url="/rss.xml")),
    "YNet": urlunparse(URLParts(scheme="https", netloc="www.ynet.co.il", url="/Integration/StoryRss2.xml")),
    "Walla": urlunparse(URLParts(scheme="https", netloc="rss.walla.co.il", url="/feed/1")),
    "Walla World": urlunparse(URLParts(scheme="https", netloc="rss.walla.co.il", url="/feed/2")),
    "Globes": urlunparse(
        URLParts(
            scheme="https",
            netloc="www.globes.co.il",
            url="/webservice/rss/rssfeeder.asmx/FeederNode?iID=2",
        )
    ),
    "Cyber Security News": urlunparse(
        URLParts(scheme="https", netloc="rss.app", url="/feeds/Ho4gIVhEXQwiIoOx.xml")
    ),
    "Reuters via Google": urlunparse(
        URLParts(
            scheme="https",
            netloc="news.google.com",
            url="/rss/search",
            query=urlencode({"q": "when:24h site:reuters.com", "ceid": "US:en", "hl": "en-US", "gl": "US"}),
        )
    ),
    "BeepingComputer": urlunparse(URLParts(scheme="https", netloc="www.bleepingcomputer.com", url="/feed/")),
    "Hacker News": urlunparse(URLParts(scheme="https", netloc="news.ycombinator.com", url="/rss")),
    "TechCrunch": urlunparse(URLParts(scheme="https", netloc="techcrunch.com", url="/feed/")),
    "Lobsters": urlunparse(URLParts(scheme="https", netloc="lobste.rs", url="/top/rss")),
    "Business Insider": urlunparse(URLParts(scheme="https", netloc="www.businessinsider.com", url="/rss")),
    "Abu Ali Express": urlunparse(URLParts(scheme="https", netloc="tg.i-c-a.su", url="/rss/abualiexpress")),
    "Amit Segal": urlunparse(URLParts(scheme="https", netloc="tg.i-c-a.su", url="/rss/amitsegal")),
}

USER_AGENT = "Mozilla/5.0 (compatible; HermesNewsAnchor/1.0)"


class FeedItem(BaseModel):
    title: Annotated[str, Field(default="")]
    link: Annotated[str, Field(default="")]

    @model_validator(mode="before")
    @classmethod
    def within_timeframe(cls, entry: Any, info: ValidationInfo) -> Any:
        ts = entry.get("published_parsed") or entry.get("updated_parsed")
        if ts is None:
            raise ValueError("no publish date")
        published = datetime(*tuple(ts)[:6], tzinfo=UTC)
        cutoff = info.context["cutoff"] if info.context else datetime.max.replace(tzinfo=UTC)
        if published < cutoff:
            raise ValueError("outside timeframe")
        return entry


class FeedPage(BaseModel):
    items: Annotated[list[FeedItem], Field(default_factory=list)]


class FeedResult(BaseModel):
    name: str
    url: str
    error: Annotated[str | None, Field(default=None)]
    items: Annotated[list[FeedItem], Field(default_factory=list)]

    def to_string(self) -> str:
        if self.error:
            return f"  [{self.error}]"
        lines = [f"  - {item.title}\n    {item.link}" for item in self.items]
        if not lines:
            return "  [no items found]"
        return "\n".join(lines)


async def fetch_source(name: str, url: str, limit: int, cutoff: datetime) -> FeedResult:
    """Fetch one source and return structured data. Never raises."""
    result = FeedResult(name=name, url=url, error=None, items=[])
    try:
        parsed = await asyncio.to_thread(feedparser.parse, url, agent=USER_AGENT)
    except OSError as exc:
        result.error = f"error fetching {url}: {exc}"
        return result

    for entry in parsed.entries:
        if len(result.items) >= limit:
            break
        try:
            result.items.append(FeedItem.model_validate(entry, context={"cutoff": cutoff}))
        except ValidationError:
            continue
    return result


class Args(BaseSettings):
    model_config = SettingsConfigDict(cli_parse_args=True)

    source: str | None = None
    limit: Annotated[int, Field(default=8)]
    hours: int = 24
    list: CliImplicitFlag[bool] = False


async def main() -> int:
    try:
        args = Args()
    except ValidationError as error:
        raise SystemExit(str(error)) from error

    if args.list:
        for name in ALL_SOURCES:
            print(name)
        return 0

    sources = ALL_SOURCES
    if args.source:
        if args.source not in sources:
            print(
                f"Unknown source {args.source!r}. Available: " + ", ".join(sources),
                file=sys.stderr,
            )
            return 1
        sources = {args.source: sources[args.source]}

    cutoff = datetime.now(tz=UTC) - timedelta(hours=args.hours)
    async with asyncio.TaskGroup() as tg:
        tasks = [
            tg.create_task(fetch_source(name, str(url), args.limit, cutoff))
            for name, url in sources.items()
        ]
    for result in (task.result() for task in tasks):
        print(f"\n[{result.name}]\n{result.to_string()}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
