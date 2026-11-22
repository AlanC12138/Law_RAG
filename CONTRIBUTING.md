# Contributing

Notes for working on Law RAG — including by future-me.

## Branches

- **`main`** — the released state. Tagged releases are cut from here.
- **`dev`** — integration branch. Work lands here first.
- Topic branches (`feat/…`, `fix/…`, `chore/…`) branch from `dev` and merge back into it.

CI runs on pushes and pull requests to both `main` and `dev`.

## Setup and commands

See [README.md](README.md) — it has the authoritative setup, the test command,
and the lint/build commands. They are deliberately documented in one place
only; duplicating them here is how they drift apart.

The one thing worth repeating, because it surprises people: the backend image
is built with `poetry install --without dev`, so **`pytest` is not inside the
container**. The suite runs on the host. The README spells out the exact
invocation.

## Verifying your change

State what you actually ran, not what ought to pass. Three ways this project
has produced false "passing" results — all of them real, all of them caught
late:

1. **`backend/.env` masking a missing variable.** It is gitignored, so it
   exists locally and never in CI. A check that passes locally because `.env`
   quietly supplied `SECRET_KEY` tells you nothing about CI. When verifying
   something CI will run, delete or bypass `.env` first.
2. **Verifying in the dev container instead of CI's environment.** The
   frontend dev image and the CI runner disagreed on libc for months; lint and
   build passed locally while CI's build failed every single run. Match the
   platform CI uses.
3. **A pipe swallowing the exit code.** `black --check . | tail -1` reports
   `tail`'s status, not black's — it looks green while the check fails.
   Capture `$?` from the command itself, not from the end of a pipeline.

If part of a change is unverified, say so in the PR. An acknowledged gap is
more useful to a reviewer than an implied guarantee.

## Commits

Conventional-commit prefixes, matching the existing history:

```
feat:   a user-visible capability
fix:    a defect fixed
docs:   documentation only
chore:  tooling, dependencies, repo plumbing
style:  formatting only, no behaviour change
ci:     workflow and pipeline changes
test:   tests only
```

Write the body to explain **why**, and say what you verified. Several commits
here carry the exact commands and their exit codes — that has repeatedly
turned out to be worth more than a tidy subject line.

## Changelog

User-visible changes get an entry under `[Unreleased]` in
[CHANGELOG.md](CHANGELOG.md), in Keep a Changelog format
(`Added` / `Changed` / `Fixed`). Docs-only and CI-only changes usually do not
need one.

Put features under `Added` and defects under `Fixed` — not whichever section
happens to be nearest.
