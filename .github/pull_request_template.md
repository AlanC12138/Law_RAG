## What this changes

<!-- One or two sentences. What is different after this merges? -->

## Why

<!-- The problem being solved. Link an issue if there is one. -->

## How it was verified

<!--
Say what you actually ran, not what should pass. If something is unverified,
say so — an honest gap is more useful than an implied guarantee.

Backend:
  docker compose exec backend pytest -q
  docker compose exec backend ruff check . && docker compose exec backend black --check .
Frontend:
  docker compose exec frontend npm run lint
  docker compose exec frontend npm run build
-->

- [ ] Backend tests pass
- [ ] Lint/format clean (ruff, black, ESLint)
- [ ] Frontend builds (`tsc && vite build`)
- [ ] Ran it against a real stack (`docker compose up`), not just tests
- [ ] CHANGELOG updated under `[Unreleased]` (or N/A — docs/CI only)

## Notes for the reviewer

<!--
Anything worth knowing: trade-offs taken, things deliberately left out,
follow-up work, or parts you are unsure about.
-->
