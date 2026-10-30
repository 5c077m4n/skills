---
name: weather-skill
description: Fetch weather data from the open-meteo API and format a compact report
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [weather, api, script]
    category: utils
    requires_toolsets: [terminal]
---

# Weather Skill

Pulls daily weather forecasts from the free open-meteo.com API (no API key
required) and prints a compact, human-readable report.

## When to Use

When the user asks about current or upcoming weather, temperature, rain chance,
or wind for a location.

## Choosing the Forecast Horizon

The skill decides how many days to fetch based on the user's question:

| User phrasing                          | `--days` value |
| -------------------------------------- | -------------- |
| "now", "today", "current"              | 1              |
| "tomorrow"                             | 2              |
| "this week", "rest of the week"        | 7              |
| "this weekend"                          | through Sunday |
| "next week"                            | 14             |
| unqualified ("what's the weather in X") | 3              |

## Procedure

Run the script with uv (deps are declared in `pyproject.toml`, first run syncs
the venv):

```bash
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/fetch_weather.py" \
  --lat 32.0263 --lon 34.8881 --days 7 --label "Kiryat Ono"
```

- Look up the latitude and longitude for the requested location first (or use
  known coordinates for common places).
- `--label` is optional and replaces the raw lat/lon heading in the report.
- The output is plain text, one line per day:
  `Www DD/MM: high°C / low°C, rain N%, wind N km/h, humidity N%, condition`
  (weekday short name comes from the script itself).

## Pitfalls

- Always pass `--days` explicitly; the default of 3 is a fallback, not a hint.
- Coordinates must be decimal degrees (e.g. 32.0263, not 32°1'35").
- Expand abbreviated place names before geocoding — the user says "k Ono" for
  Kiryat Ono; a raw abbreviation fails coordinate lookup, so map it to the
  full name first.
- open-meteo supports up to 16 forecast days on the free tier.
