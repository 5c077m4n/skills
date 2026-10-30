---
name: news-anchor
description: Summarize headlines from the configured RSS news sources as a news anchor
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [rss, news, summarization]
    category: news
    requires_toolsets: [terminal]
---

# News Anchor

Act as a news anchor: pull the latest headlines from the configured RSS sources
and deliver a concise spoken-style briefing.

## Sources

| Source              | Focus                       |
| ------------------- | --------------------------- |
| Israel Hayom        | Israeli news (Hebrew)       |
| YNet                | Israeli news (Hebrew)       |
| Walla               | Israeli news (Hebrew)       |
| Walla World         | World news (Hebrew)         |
| Cyber Security News | InfoSec headlines           |
| Reuters via Google  | Global wire news (last 24h) |
| BeepingComputer     | InfoSec incidents/malware   |
| Hacker News         | Tech/developer community    |
| TechCrunch          | Startups & tech business    |
| Lobsters            | Developer/tech community    |

## When to Use

When the user asks for a news briefing, digest, "what's in the news", "catch me
up", or invokes `/news-anchor`.

## Procedure

1. Run the fetch script from this skill's directory:

   ```
   uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/fetch_feeds.py" --limit 8
   ```

   - `--source <name>` fetches a single source (run `--list` to see names).
   - `--limit N` controls items per source.
   - Feeds run in parallel; a failing feed reports `[error fetching ...]`
     instead of aborting the whole run.

2. Read the titles and links. If a title is in Hebrew, translate it to English
   before summarizing.

3. Deliver the briefing as a news anchor would:
   - Open with a one-line intro naming the hour/topics.
   - Group stories: top global wire news first, then regional, then
     tech/security. Skip near-duplicates across sources (e.g. the same story on
     two feeds) and mention it once with both attributions.
   - For each story: one or two sentences — what happened and why it matters —
     with the source name in parentheses.
   - Close with a short sign-off.

4. Always pair each story with its original article link: the summary and the
   link must appear together, one immediately after the other, for every story
   in the briefing — never summarize a story without its link.

5. Keep the whole briefing scannable: use bold for each story's headline and
   include the article link inline so the user can tap through.

6. Always render links as full URLs in markdown format —
   `[source name](full article URL)` — never as bare domain names or shortened
   references. Use the complete link exactly as it appears in the script output,
   including `http(s)://`. The link must be clickable in the chat output and
   point to the original article.

## Pitfalls

- Never drop the article link: every story must be returned with its original
  article URL next to the summary, even when trimming for brevity.
- Never truncate or paraphrase URLs; never output only the source name without
  the full clickable link.
- Do not re-run the script per source; one run fetches everything in parallel.
- Google News links are wrapped/redirect URLs; report them as-is, they resolve
  correctly.
- If every feed fails, say so plainly (likely network issue on the host) instead
  of inventing headlines.

## Verification

The script output starts with `##` source headers like `[Reuters via
Google]` —
if you see empty sections or errors, retry once before reporting partial
results.
