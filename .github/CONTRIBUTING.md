# Contributing

Thank you for taking the time to contribute!

## Getting started

```bash
git clone https://github.com/ElectroAttacks/lametric-hass-local.git
cd lametric-hass-local
uv sync --dev
pre-commit install
```

See [docs/development.md](docs/development.md) for a full overview of the project layout and quality gates.

## Reporting issues

Before opening an issue, please search the [existing issues](https://github.com/ElectroAttacks/lametric-hass-local/issues) to avoid duplicates.

Use the appropriate issue template:

- **Bug report** — something is not working as documented
- **Feature request** — propose a new capability or improvement

For security vulnerabilities, see [SECURITY.md](.github/SECURITY.md).


## Submitting a pull request

1. Fork the repository and create a branch from `main`.
2. Make your changes and ensure all quality gates pass locally:

   ```bash
   uv run ruff check . && uv run ruff format --check .
   uv run mypy .
   uv run pytest --cov=src --cov-report=term-missing
   ```

3. Commit using [Conventional Commits](https://www.conventionalcommits.org/):

   | Prefix | When to use | Version bump |
   |--------|-------------|--------------|
   | `feat:` | New public API or capability | minor |
   | `fix:` | Bug fix | patch |
   | `perf:` | Performance improvement | patch |
   | `refactor:` | Internal restructuring, no behaviour change | patch |
   | `docs:` | Documentation only | — |
   | `ci:` | Workflow or tooling changes | — |
   | `chore:` | Maintenance, dependency bumps | — |

   Breaking changes must include `BREAKING CHANGE:` in the commit footer, which triggers a major bump.

## Translations

If you add new strings, update `custom_components/lametric_hass_local/translations/en.json`. Additional language files are welcome.
4. Open a pull request against `main` and fill in the pull request template.

## Code style

- **Ruff** enforces linting and formatting — run `uv run ruff format .` to auto-format.
- **Mypy** enforces strict typing — all public functions must be fully annotated.
- Keep changes focused; unrelated fixes belong in separate PRs.
