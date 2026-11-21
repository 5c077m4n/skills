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

Hand large coding tasks to the pi coding agent, driven through the official
SDK (`@earendil-works/pi-coding-agent`) by the runner script in
`scripts/pi-run.mts`. pi never runs git and never reaches outside its work
directory: the permission policy denies every `git *` bash command and sets
`external_directory: deny`. pi works on a disposable copy of the workspace and
returns a unified diff, which hermes reviews, applies, and continues from.

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

2. The runner is a self-contained node project (`package.json` + `package-lock.json`,
   deps `@earendil-works/pi-coding-agent` + `tsx`). Install it once, then run pi
   via the SDK in the work copy. The OpenRouter key is fetched from AWS SSM
   per-run and never written to disk:

   ```bash
   RUNNER="<skill_dir>"   # e.g. /var/lib/hermes/home/skills/pi-delegate
   (cd "$RUNNER" && npm install --no-fund --no-audit >/dev/null)

   export OPENROUTER_API_KEY="$(aws ssm get-parameter --region il-central-1 \
     --name /hermes/openrouter_key --with-decryption --query Parameter.Value --output text)"
   (cd "$WORK" && "$RUNNER/node_modules/.bin/tsx" "$RUNNER/scripts/pi-run.mts" "<task description>")
   ```

   The runner imports `createAgentSession` / `ModelRuntime` from
   `@earendil-works/pi-coding-agent`, sets the OpenRouter key via
   `modelRuntime.setRuntimeApiKey("openrouter", …)`, streams text deltas to
   stdout, and disposes the session in a `finally` block.

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
- The OpenRouter key lives in AWS SSM (region il-central-1) at
  `/hermes/openrouter_key`; fetch it per-run as shown in step 2 and export it
  as `OPENROUTER_API_KEY`. Without it the auto-mode judge blocks every bash
  command.
- The pi-auto-mode bash-command gate lives in /root/pi-auto-mode (local checkout
  of github.com/5c077m4n/pi-auto-mode). The SDK's default resource loader picks
  it up automatically once installed via `pi install git:github.com/5c077m4n/pi-auto-mode`.
  Push from that repo needs the token embedded in the remote URL:
  `git remote set-url origin "https://5c077m4n:${GH_TOKEN}@github.com/5c077m4n/pi-auto-mode.git"`
  (source GH_TOKEN from SSM `/hermes/gh_token`), push, then reset the URL to
  the clean https form.
- Declare type-only imports (e.g. `@earendil-works/pi-coding-agent`) as real
  devDependencies, not ad-hoc node_modules installs: any later
  `npm update/install` prunes extraneous packages and typechecking breaks
  mysteriously. The runner script sidesteps this by installing into its own
  temp dir.
- Never run `npm install` in a project whose `node_modules` is (or was) a
  symlink into pi's managed install tree — npm follows the link and prunes pi's
  own packages, leaving the `pi` launcher unable to start. Repair with `npm ci`
  inside `/root/.pi/agent/install/releases/<version>`.
- A large diff still needs review before applying; show the user the summary.
- If pi exits non-zero, treat the diff as unreliable and do not apply it.
- Never run `npm install` in a project whose `node_modules` is (or was) a
  symlink into pi's managed install tree — npm follows the link and prunes pi's
  own packages, leaving the `pi` launcher unable to start. Repair with `npm ci`
  inside `/root/.pi/agent/install/releases/<version>`. Symlink `@earendil-works`
  into the project's `node_modules` only AFTER npm has finished, for
  typechecking.
- Writing a pi extension (tool-call gate, command, hook): follow
  `references/pi-extensions.md`.
- SDK reference examples live at
  https://github.com/earendil-works/pi/tree/main/packages/coding-agent/examples/sdk.
