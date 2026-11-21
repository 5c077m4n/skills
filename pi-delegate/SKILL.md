---
name: pi-delegate
description: Use when delegating large coding tasks to the pi coding agent.
version: 1.2.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [coding, delegation, pi, diff]
    category: coding
    requires_toolsets: [terminal]
---

# Pi Delegate

Hand large coding tasks to the pi coding agent, driven through the official
SDK (`@earendil-works/pi-coding-agent`) by the runner script in
`scripts/pi-run.ts`. pi never runs git and never reaches outside its work
directory: the permission policy denies every `git *` bash command and sets
`external_directory: deny`. pi works on a disposable copy of the workspace and
must print ONLY a unified diff of its changes — never apply anything to the
live workspace. hermes reviews, applies, and continues from that diff.

No Docker is involved — pi runs directly on the machine; the permission plugin
is the policy layer.

## When to Use

When the user asks for a coding task (feature, refactor, migration, big fix)
that looks **large**: multiple files, architectural changes, or a full rewrite.
If the task is small (a single file, roughly a few dozen lines), just do it
directly with the terminal toolset instead of delegating.

## Rules

- pi is **never** allowed to run git — no
  `git add/commit/diff/checkout/stash/push` or any other git subcommand. The
  `git *` deny rule is the enforcement; the prompt ban is a second line of
  defense.
- pi works on a **copy** of the workspace, never the live one.
- pi must **print only a unified diff** of its changes — no prose, no summaries.
  hermes applies it to the real workspace with `patch` and continues the work
  from there.

## Procedure

1. Give pi a **clone** of the workspace, never the original. Make two local
   clones (pristine + work); pi edits only the work clone:

   ```bash
   SRC="$(pwd)"
   EXCLUDES="--exclude .git --exclude node_modules --exclude .terraform --exclude *.tfstate --exclude pi-task.patch"
   PRISTINE="$(mktemp -d)" ; WORK="$(mktemp -d)"
   git clone --no-hardlinks "$SRC" "$PRISTINE" && git clone --no-hardlinks "$SRC" "$WORK"
   ```

2. The runner is a self-contained node project (`package.json` + `package-lock.json`,
   deps `@earendil-works/pi-coding-agent` + `tsx`). Install it once, then run pi
   via the SDK in the work copy (provider auth comes from pi's own auth store):

   ```bash
   RUNNER="<skill_dir>"   # e.g. /var/lib/hermes/home/skills/pi-delegate
   (cd "$RUNNER" && npm ci --no-fund --no-audit >/dev/null)
   (cd "$WORK" && "$RUNNER/node_modules/.bin/tsx" "$RUNNER/scripts/pi-run.ts" --task "<task description>" --cwd "$WORK")
   ```

   The runner imports `createAgentSession`, `DefaultResourceLoader`,
   `getAgentDir` and `SessionManager` from `@earendil-works/pi-coding-agent`,
   builds a resource loader over pi's agent dir so the installed extensions
   load — `pi-permission-system` (the policy layer) and `pi-auto-mode` (the
   bash-command judge) — streams text deltas to stdout, and disposes the
   session in a `finally` block.

   The plugin gates every tool call: `git *` is denied, unparseable or
   indirection-wrapped bash (`bash -c`, `sudo`, `eval`, `xargs`) fails closed to
   a prompt that times out to deny, and anything outside the work dir is
   blocked.

3. Capture pi's printed diff and cross-check it against the filesystem with a
   `diff -ruN` between pristine and pi's edited copy (pi's own diff can be
   incomplete or noisy; the filesystem diff is the ground truth):

   ```bash
   diff -ruN $EXCLUDES "$PRISTINE" "$WORK" > "$SRC/pi-task.patch" || true
   ```

4. Inspect `pi-task.patch`. If it is empty or looks wrong, do not apply it —
   rerun with a more precise task description.

5. Apply the diff to the live workspace:

   ```bash
   patch -p1 -d "$SRC" < "$SRC/pi-task.patch"
   ```

6. Continue the task in the workspace (build, test, fix-ups), report the result
   to the user, and delete `pi-task.patch` once applied.

## Pitfalls

- Never loosen the global policy: `git *` stays `deny` and `external_directory`
  stays `deny`, even if pi asks for more access. Project configs can only
  tighten, and untrusted dirs (like the work copy) load none at all.
- No `ask` rules in this policy on purpose: SDK runs are unattended and an
  unanswered prompt only times out to deny after 60s. Keep it that way.
- The pi-auto-mode bash-command gate lives in /root/pi-auto-mode (local checkout
  of github.com/5c077m4n/pi-auto-mode). The SDK's default resource loader picks
  it up automatically once installed via `pi install git:github.com/5c077m4n/pi-auto-mode`.
  Push from that repo needs the token embedded in the remote URL:
  `git remote set-url origin "https://5c077m4n:${GH_TOKEN}@github.com/5c077m4n/pi-auto-mode.git"`
  (source GH_TOKEN from SSM `/hermes/gh_token`), push, then reset the URL to
  the clean https form.
- Declare type-only imports (e.g. `@earendil-works/pi-coding-agent`) as real
  devDependencies in a package.json with a committed lockfile — not ad-hoc
  node_modules installs: any later `npm update/install` prunes extraneous
  packages and typechecking breaks mysteriously. The runner is its own node
  project in the skill dir for exactly this reason.
- Never run `npm install` in a project whose `node_modules` is (or was) a
  symlink into pi's managed install tree — npm follows the link and prunes pi's
  own packages, leaving the `pi` launcher unable to start. Repair with `npm ci`
  inside `/root/.pi/agent/install/releases/<version>`.
- A large diff still needs review before applying; show the user the summary.
- If pi exits non-zero, treat the diff as unreliable and do not apply it.
- Writing a pi extension (tool-call gate, command, hook): follow
  `references/pi-extensions.md`.
- SDK reference examples live at
  https://github.com/earendil-works/pi/tree/main/packages/coding-agent/examples/sdk.
