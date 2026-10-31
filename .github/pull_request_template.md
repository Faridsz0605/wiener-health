## What

<!-- One or two sentences. -->

## Why

<!-- Problem solved / decision applied. Link ADR if any. -->

## Stack

- Base: `<parent branch>` (PR #)
- Depends on: #

## Verification

- [ ] `uv run ruff check && uv run ruff format --check`
- [ ] `uv run pytest`
- [ ] `uv run python tools/check_no_row_output.py`
- [ ] Only synthetic data; no secrets, tokens or personal data in the diff
- [ ] `docs/roadmap.md` updated

## Blockers

<!-- External credentials, pending spikes, etc. "None" if none. -->

## Open `REVIEW` items

<!-- Unverified facts or pending decisions introduced or touched here. -->
