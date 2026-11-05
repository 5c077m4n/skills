# Python Code Style

Conventions for Python scripts. Ruff is the linter of record; pyright
for types.

## Tooling

- `ruff check` must pass with zero findings before pushing.
- `pyright` must show no new errors vs the base branch; when a quirk
  forces a workaround, match the convention already used in the file
  rather than adding a new one.
- Scripts are run via `uv run` with the project directory as the root.

## Style

- No comments and no docstrings unless they state something the code
  cannot; usage docs belong in the skill/reference docs, not the script.
- No magic numbers: name the constant (declare module globals with
  `typing.Final`).
- Declare module-level constants with `Final[...]`.
- Put output/formatting logic as an instance method on the data class
  (`stringify()`-style), not a free function that reaches into fields.
- Validation belongs in pydantic: use `model_validator(mode="before")`
  with context (`model_validate(data, context=...)`) for cross-field or
  source-data checks; skip invalid records via `ValidationError` at the
  call site.
- Guard optional values explicitly before subscripting — pyright can't
  narrow `dict.get()` results, so restructure instead of casting.
- Never mutate a function parameter; build a new structure.
- Prefer stdlib `datetime` (timezone-aware, `datetime.now(tz=UTC)`) over
  local-time `mktime` arithmetic; treat third-party UTC structs (e.g.
  feed-like `*_parsed` tuples) as UTC explicitly.
- Tests only when they add real value; skips are fine to remove.

## PR hygiene

- Keep PRs small and single-purpose; never touch files unrelated to the
  PR's purpose.
- Verify changes live (run the script against the real API/feed) before
  pushing; include verification output in the PR body.
- No personal or private data (identifiers, hostnames, credentials) in
  commits or PR bodies.
