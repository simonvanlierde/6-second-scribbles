# Contributing

This is a personal project, but issues and pull requests are welcome. Set up with
[Running locally](README.md#running-locally).

## Before You Open a PR

Run the same checks CI runs:

```bash
just check      # contracts, lint, types, and security checks
just test       # frontend + backend test suites
just format     # auto-format everything
```

If you change the shape of what the backend sends or accepts, run
`just generate-contracts` so the frontend stays in sync
([ADR 0001](docs/adr/0001-committed-generated-contracts.md)).

## Accessibility checks

- **Static linting:** Biome's a11y rules, run by `pnpm --dir frontend run lint`.
- **axe scans:** Playwright with [`@axe-core/playwright`](https://github.com/dequelabs/axe-core-npm)
  scans Home, the Settings panel, and the `/__ds` page against the WCAG 2.1 A/AA
  rule tags, in the light and the dark theme. They need only the frontend and run
  as the `a11y` CI job. Locally: `just frontend/test-a11y`.
- **Accessibility-tree assertions:** the e2e suite finds elements by ARIA role and
  accessible name, so those flows pass only when the roles and labels are there.
  They run as the `e2e` CI job. Locally: `just test-e2e`, which needs the backend stack.

These tools check specific WCAG A/AA rules. A passing axe run is not a full manual
audit, and it does **not** certify WCAG AA conformance.

## Commit Messages

Commits follow [Conventional Commits](https://www.conventionalcommits.org/), checked
by a `commitlint` git hook. For example: `fix(scoring): reject short-substring fuzzy matches`.
