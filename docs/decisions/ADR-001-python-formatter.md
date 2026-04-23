# ADR-001 — Python formatter + linter: ruff alone

- **Status**: Accepted
- **Date**: 2026-04-23
- **Decided by**: Andres + Claude (joint decision in session on 2026-04-23)

## Context

We need a formatting + linting tool for the FastAPI service under `api/`. The common options in 2026:

1. **ruff alone** — Ruff v0.6+ includes a Black-compatible `format` subcommand. One tool covers lint + format.
2. **ruff + black** — Ruff for lint, Black for format. Pre-2024 convention.
3. **black alone** — formatter only; no lint.
4. **pylint + black** — heavyweight lint + format split.

## Decision

Use **ruff alone** for both formatting and linting. Configuration lives in `api/pyproject.toml` under `[tool.ruff]`. Both `ruff check --fix` and `ruff format` will run in any pre-push git hook we add (reactively) and in GitHub Actions CI.

## Rationale

- **One tool, one config, one mental model** — removes the `[tool.black]` section and the Black dependency.
- **Speed** — Ruff is Rust-compiled; ~10–100× faster than Black on equivalent files. Matters in pre-commit + CI loops.
- **Astral's own positioning** — Ruff's formatter is "Black-compatible with minor differences" and is designed to replace Black in new projects.
- **Small codebase** — no meaningful downside for a 2-week project with one Python service.
- **Lint coverage** — Ruff's rule set covers pyflakes, pycodestyle, isort, pyupgrade, and more; we don't need pylint for our scale.

## Rejected alternatives

- **ruff + black** — extra dependency with no feature gain once Ruff formats.
- **black alone** — would need a separate linter (flake8/pyflakes) anyway; ruff collapses both.
- **pylint + black** — pylint is slower and more opinionated than we need for a take-home timeline.

## References

- https://docs.astral.sh/ruff/formatter/ — Ruff formatter documentation
- https://astral.sh/blog/the-ruff-formatter — announcement blog post ("Black-compatible")
- https://docs.astral.sh/ruff/rules/ — full rule catalog (lint side)

## Consequences

- Ruff version will be pinned in `pyproject.toml`. Minor Ruff versions occasionally ship formatting diffs; we bump intentionally and run `ruff format --check` in CI to catch drift.
- Every Python file in the repo must pass `ruff check` and `ruff format --check`.
- No `[tool.black]` config anywhere; no `.flake8`; no `pylintrc`.
- If a contributor's editor auto-formats with Black, output is close enough that CI won't flag — but they should switch to Ruff's formatter for zero friction.
