---
name: ollama-query
description: Run a query on a local Ollama model that best fits the host hardware.
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [ollama, llm, local, hardware]
    category: utils
    requires_toolsets: [terminal]
---

# Ollama Query

Send a prompt to a locally running Ollama server using the official `ollama`
TypeScript SDK. The script inspects the host hardware (total GPU VRAM via
`nvidia-smi`, falling back to system RAM) and picks the largest installed
model whose on-disk size fits within 70% of that budget, so the query always
runs on the biggest model the machine can hold.

## When to Use

When the user wants a quick answer from a local model (privacy, offline, no
API key) or asks to "ask the local model".

## Procedure

1. Install the project's dependencies once, then run a query:

   ```bash
   SKILL_DIR=/var/lib/hermes/home/skills/ollama-query
   (cd "$SKILL_DIR" && npm ci --no-fund --no-audit >/dev/null)
   (cd "$SKILL_DIR" && npm run query -- --prompt "<text>" [--host <url>])
   ```

2. The script prints the chosen model to stderr (`using <model>`) and streams
   the answer to stdout.

## Notes

- If no Ollama server is running (default `http://localhost:11434`), the script
  starts one itself (`ollama serve`) and kills it after the query. Pass
  `--host` to use an existing server instead — a custom host is never started
  or stopped, only probed.
- The 70% budget leaves room for the OS and the model's KV cache. On a GPU
  host the budget is total VRAM; otherwise it is system RAM.
- If no installed model fits the budget the script exits with an error
  suggesting `ollama pull <smaller-model>`.
- Pinned dependencies: `ollama` SDK and `tsx` (exact versions in
  `package.json` with a committed `package-lock.json`).
- Import `{ Ollama }` (named export) from "ollama" — the default export is
  not a constructor, so `new Ollama()` fails with "Ollama is not a
  constructor".
- Wrap the whole run in try/catch: without a reachable Ollama server the SDK
  throws `fetch failed`/`ECONNREFUSED`; log to stderr and exit 1 instead of
  crashing with a stack trace.
