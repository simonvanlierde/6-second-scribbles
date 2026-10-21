# Contributing

This is a personal project, but issues and pull requests are welcome. To set up,
follow [Running locally](README.md#running-locally).

## Before you open a PR

Install the git hooks once per clone with [prek](https://prek.j178.dev):
`uv tool install prek`, then `prek install`. They format and lint what you commit,
check the commit message, and spell-check what you push. CI runs them too. In a
clone that still has the old lefthook hooks, `prek install -f` replaces them.

Run these first. `just check` and `just test` cover most of what CI runs. The
accessibility and e2e jobs are below.

```bash
just check      # contracts, lint, types, and security checks
just test       # frontend + backend test suites
just format     # auto-format everything
just hooks      # every git hook over the whole repo
```

If you change what the backend sends or accepts, run `just generate-contracts` so
the frontend stays in sync ([ADR 0001](docs/adr/0001-committed-generated-contracts.md)).

## Accessibility checks

- **Static linting:** Biome's a11y rules, run by `pnpm --dir frontend run lint`.
- **axe scans:** Playwright with [`@axe-core/playwright`](https://github.com/dequelabs/axe-core-npm)
  scans Home, the Settings panel, and the `/__ds` page against the WCAG 2.1 A/AA
  rule tags, in the light and the dark theme. They need only the frontend. CI runs
  them as the `a11y` job. Locally: `just frontend/test-a11y`.
- **Accessibility-tree assertions:** the e2e suite finds elements by ARIA role and
  accessible name, so those flows pass only when the roles and labels are there.
  CI runs them as the `e2e` job. Locally: `just test-e2e`. It starts the database,
  the cache, and the backend itself, so Docker must be running.

These tools check specific WCAG A/AA rules. A passing axe run is not a manual audit,
and it does **not** certify WCAG AA conformance.

## Commit messages

Commits follow [Conventional Commits](https://www.conventionalcommits.org/), checked
by a `commitlint` git hook. For example: `fix(scoring): reject short-substring fuzzy matches`.
