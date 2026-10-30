# Writing pi extensions

pi extensions are TypeScript modules loaded via jiti (no build step). Authoritative docs ship inside the install:
`/root/.pi/agent/install/releases/<version>/node_modules/@earendil-works/pi-coding-agent/docs/extensions.md` (and `packages.md`).

## Anatomy

- A file in `~/.pi/agent/extensions/` (auto-loaded) or a package with `"pi": {"extensions": [...]}` in package.json.
- Export a default function receiving `ExtensionAPI`.
- Gate a tool call: `pi.on("tool_call", async (event) => ...)`; narrow with `event.toolName === "bash"`, read `event.input.command`.
- Block by returning `{ block: true, reason: "..." }`; return `undefined` to allow. `reason` is shown to the agent as the tool error.
- `pi.on("input", (event) => { state = event.text })` captures the current task/prompt for context-aware gates.
- Pi supplies `@earendil-works/pi-coding-agent` (types import) and runs extensions with its bundled jiti; runtime npm deps go in the package's `dependencies`.

## Package layout (git-installable)

```
repo/
  package.json        # keywords include "pi-package"; "pi": {"extensions": [...]}
  extensions/<name>.ts
```
Install with `pi install git:github.com/<user>/<repo>`; one-off with `pi -e <path-or-git>`.

## Verification workflow

1. `tsc -p .` with strict tsconfig; symlink `@earendil-works` from the install's node_modules for types.
2. Live-run both directions with `pi -e <ext> -p "..."` — one task-appropriate command (expect it to run) and one dangerous/off-task command (expect a block message naming the gate). Phrase the prompt as an explicit tool call ("use the bash tool to run: echo hello") — a plain `run: ...` task may be answered without ever calling bash, so the gate is never exercised and the run looks verified when it isn't.
3. When the gate's judge prompt or response schema changes, verify the raw contract with a direct `curl` to the model endpoint using the exact system prompt before running pi — one cheap call confirms the model returns parseable, schema-valid output instead of debugging through the extension.
4. Event-diff cache keys on task+command, not command alone — verdicts depend on task context.

## Pitfalls

- Gate fail-closed on API error/timeout, but the missing-API-key case should also block — otherwise an unconfigured env silently disables the gate.
- Extension defaults that resolve paths via `os.tmpdir()` follow pi's inherited
  `TMPDIR`, not `/tmp` — when a default path matters, expose an env override and
  document it; don't assume `/tmp`.
- Log writes from a gate must be synchronous (`appendFileSync`) — async
  fire-and-forget appends with a swallowed catch fail invisibly and the gate
  looks verified when nothing was ever written.
- Strict-mode gotchas: `choices[0]` is `T | undefined` under noUncheckedIndexedAccess; `response.json()`/`JSON.parse` are `unknown` — validate with zod, no casts.
- npm in a repo whose node_modules symlinked into pi's install corrupts the install (see SKILL.md).
