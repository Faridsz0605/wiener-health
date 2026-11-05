# Contributing to Wiener-Data

## Workflow

- `main` is protected: no direct pushes, no force-pushes, no deletions. Every change lands through a pull request.
- Merging to `main` deploys the Databricks bundle (`lakehouse/`) from CI. Review lakehouse changes with that in mind.
- One branch per change, named `<type>/<slug>`:
  - `feat/` new capability
  - `fix/` bug fix
  - `docs/` documentation only
  - `chore/` tooling, CI, repo hygiene
  - `spike/` throwaway experiment that validates a decision (results go to `docs/spikes.md`)
- Stacked PRs are welcome: branch off the previous PR's branch and set it as the PR base. Review and merge bottom-up; GitHub retargets children automatically.
- Keep PRs small and reviewable. Fill in the PR template (what, why, verification, blockers, open `REVIEW` items).

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `feat: ...`, `fix: ...`, `docs: ...`, `chore: ...`, `test: ...`, `refactor: ...`. Imperative mood, subject <= 72 chars.

## Decisions

- Any change of an architectural decision requires a new ADR in `docs/adr/` and, when it refutes a prior assumption, a row in `docs/adr/0000-supuestos-falsados.md`.
- Mark unverified facts or pending decisions with `REVIEW` (in docs and code comments). Verify before depending on them.

## Data and secrets

- This repository is public. Never commit real personal data, Takeout archives, OAuth tokens, PATs, `.env` or Terraform state.
- Tests use synthetic fixtures only (`tests/fixtures/`, `example.*` domains).
- Server-side secrets live in `.env` -> SSM (`scripts/deploy_box.sh`). Local client credentials live in the OS keyring.

## Code

- Code, identifiers and code comments in English. `README.md` (EN) and `README.es.md` (ES); other docs in Spanish.
- `wiener` is project branding for docs and process names. It is not used in code identifiers or catalog/schema names beyond the existing bundle.
- `snake_case` naming. `uv` for dependencies.
- Polars for extraction/landing and single-node utilities; PySpark for distributed processing inside the medallion layers.
- Smallest change that fully solves the problem. No speculative abstractions. No emojis in code or docs.
- Jobs under `lakehouse/` must not print rows: `display(`, `.show(` and `print(` are rejected by `tools/check_no_row_output.py`.

## Local checks

```sh
uv sync --group client
uv run ruff check .
uv run ruff format --check .
uv run pytest                  # Spark tests need Java 17 (JAVA_HOME); skipped otherwise
uv run python tools/check_no_row_output.py
terraform -chdir=infra fmt -check
```
