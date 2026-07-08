# Contributing to Bourse

Thanks for your interest in Bourse — *the exchange for strategy intelligence*.
This guide covers how to set up the project, the quality bar, and how to
submit changes.

## Code of Conduct

This project is governed by our [Code of Conduct](./CODE_OF_CONDUCT.md). By
participating, you are expected to uphold it.

## Getting Started

Bourse runs **fully offline** with deterministic fixtures — no accounts,
keys, or wallets required for development.

```bash
git clone https://github.com/edycutjong/bourse.git
cd bourse
pip install -r requirements.txt
pip install -e .
cp .env.example .env          # dummy values are fine for offline work
make seed                     # write deterministic demo fixtures
```

Verify your setup:

```bash
make signal          # ranked divergence board (offline)
make test            # full test suite
```

## Development Workflow

1. **Fork** the repo and create a topic branch off `main`:
   ```bash
   git checkout -b feat/short-description
   ```
2. Make your change with tests.
3. Run the full local gate before pushing:
   ```bash
   make ci            # ruff + mypy + pytest(coverage) + pip-audit + readiness
   ```
4. Open a Pull Request against `main` and fill in the PR template.

### Branch & Commit Conventions

- Branch prefixes: `feat/`, `fix/`, `chore/`, `docs/`, `test/`, `refactor/`.
- Commits follow [Conventional Commits](https://www.conventionalcommits.org/):
  `type(scope): summary` — e.g. `fix(engine): clamp divergence z-score`.

## Quality Bar

Every PR must pass the CI pipeline:

| Stage | Tool | Requirement |
| ----- | ---- | ----------- |
| Lint & format | Ruff | no violations |
| Type safety | mypy | clean |
| Tests | pytest + coverage | all pass; keep core coverage high |
| Dependency audit | pip-audit | no known CVEs |
| Secret scan | TruffleHog | no committed secrets |
| SAST | CodeQL | no new High+ alerts |
| Submission readiness | `scripts/check_submission_readiness.py` | pass |

- **Do not commit secrets.** Keep private keys, keystores, and API keys out of
  the repo — `.env` is git-ignored; use it for local config.
- New behavior needs tests. Prefer deterministic fixtures over live network
  calls in tests.

## Reporting Bugs & Requesting Features

Use the [issue templates](https://github.com/edycutjong/bourse/issues/new/choose).
For security vulnerabilities, follow the [Security Policy](./SECURITY.md)
instead of opening a public issue.

## License

By contributing, you agree that your contributions are licensed under the
project's [MIT License](./LICENSE).
