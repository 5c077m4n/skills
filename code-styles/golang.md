# Go Code Style

Conventions for Go code in this repo (e.g. 1run, hermes-aws-setup). Go
formatting is enforced by tools, so most of this is about structure and
taste.

## Tooling

- Always run `gofmt` (or `go fmt ./...`) before committing — no
  hand-formatted code.
- Run `go vet ./...` and fix everything it reports.
- Build with `CGO_ENABLED=1 go build ./...` when the project uses cgo
  (e.g. microsandbox); a plain `go build` can pass while the real build
  fails.

## Style

- No comments unless they explain something the code cannot. No
  doc-comment filler on obvious functions.
- Prefer explicit `any` over `interface{}` in new code.
- Error handling: return wrapped errors with context (`fmt.Errorf` with
  `%w`); don't log-and-continue where the caller can decide.
- Logging: pass the reason (include the error) at the point where it's
  known — don't make callers re-log a nil/missing case.
- Keep one concern per change; avoid drive-by refactors in feature PRs.
- Options/config: prefer plain struct fields with defaults over builder
  chains unless the library demands it.

## Multi-module workspaces

- Split by deployment boundary (e.g. `api/` user-facing service, `vm/`
  sandbox lifecycle) via `go.work` when components should build and
  deploy independently.
- Keep each module's `go.mod` self-contained; shared types go in a
  dedicated package, generated protobuf code in `pb/`.
