---
name: pi-delegate
description: Use when delegating large coding tasks to the pi coding agent.
version: 1.1.1
platforms: [linux, macos]
metadata:
  hermes:
    tags: [coding, delegation, pi, diff]
    category: coding
    requires_toolsets: [terminal]
---

# Pi Delegate

Hand large coding tasks to the pi coding agent, running non-interactively
(`pi -p`) under the `@gotgenes/pi-permission-system` plugin. pi never runs git
and never reaches outside its work directory: the permission policy denies every
`git *` bash command and sets `external_directory: deny`. pi works on a
disposable copy of the workspace and returns a unified diff, which hermes
reviews, applies, and continues from.

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
- The result pi returns is a **unified diff**. hermes applies it to the real
  workspace and continues the work from there.

## Procedure

1. Snapshot the workspace into two temp dirs (pristine + work). Exclude `.git`
   so the work copy has no repo history at all:

   ```bash
   SRC="$(pwd)"
   EXCLUDES="--exclude .git --exclude node_modules --exclude .terraform --exclude *.tfstate --exclude pi-task.patch"
   PRISTINE="$(mktemp -d)" ; WORK="$(mktemp -d)"
   rsync -a $EXCLUDES "$SRC/" "$PRISTINE/" ; rsync -a $EXCLUDES "$SRC/" "$WORK/"
   ```

2. Run pi non-interactively in the work copy:

   ```bash
   (cd "$WORK" && pi -p "<task description>. Strict rule: do NOT run any git
   command. Work only inside this directory.")
   ```

   The plugin gates every tool call: `git *` is denied, unparseable or
   indirection-wrapped bash (`bash -c`, `sudo`, `eval`, `xargs`) fails closed to
   a prompt that times out to deny, and anything outside the work dir is
   blocked.

3. Generate the unified diff between pristine and pi's edited copy:

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
- No `ask` rules in this policy on purpose: `pi -p` runs are unattended and an
  unanswered prompt only times out to deny after 60s. Keep it that way.
- pi's binary lives at `/root/.pi/agent/bin/pi` (not on the default PATH). Never invoke it as `npx pi` — npm's `pi` package is a different program that exits 0 printing a bare "3" for every invocation, including `--version`, so failures look like successes. `export PATH=/root/.pi/agent/bin:$PATH` instead.
- The pi-auto-mode bash-command gate lives in /root/pi-auto-mode (local checkout
  of github.com/5c077m4n/pi-auto-mode). Run it with
  `pi -e /root/pi-auto-mode` and OPENROUTER_API_KEY in env (it lives in
  /var/lib/hermes/home/.env); without the key it blocks every bash command.
  Push from that repo needs the token embedded in the remote URL:
  `git remote set-url origin "https://5c077m4n:${GH_TOKEN}@github.com/5c077m4n/pi-auto-mode.git"`
  (source GH_TOKEN from /var/lib/hermes/home/.env), push, then reset the URL to
  the clean https form.
- Declare type-only imports (e.g. `@earendil-works/pi-coding-agent`) as real
  devDependencies, not ad-hoc node_modules installs: any later `npm
  update/install` prunes extraneous packages and typechecking breaks
  mysteriously. Symlinking into node_modules is only for projects that must
  not take the dependency.
- A large diff still needs review before applying; show the user the summary.
- If pi exits non-zero, treat the diff as unreliable and do not apply it.
- Never run `npm install` in a project whose `node_modules` is (or was) a
  symlink into pi's managed install tree — npm follows the link and prunes
  pi's own packages, leaving the `pi` launcher unable to start. Repair with
  `npm ci` inside `/root/.pi/agent/install/releases/<version>`. Symlink
  `@earendil-works` into the project's `node_modules` only AFTER npm has
  finished, for typechecking.
- Writing a pi extension (tool-call gate, command, hook): follow
  `references/pi-extensions.md`.
