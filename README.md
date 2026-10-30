# Skills

Hermes agent skills — procedural knowledge loaded on demand via `skill_view`.

## Layout

Each top-level directory is a skill containing a `SKILL.md` (name, description,
usage procedure) plus optional `scripts/`, `references/`, and `templates/`.

## Usage

Skills live in `/var/lib/hermes/home/skills` and are loaded with
`skill_view(name)`. Browse `SKILL.md` frontmatter to see what each skill does.
