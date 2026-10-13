# Contributing

This is a personal project, but issues and pull requests are welcome.

## Getting Set Up

Requires Node 26+, Python 3.14+, `pnpm`, `uv`, `just`, and Docker. See
[Running locally](README.md#running-locally) for the full quickstart.

```bash
just install    # install frontend + backend dependencies
just dev        # Docker services + dev servers
```

## Before You Open a PR

Run the same checks CI runs:

```bash
just check      # contracts, lint, types, and security checks
just test       # frontend + backend test suites
just format     # auto-format everything
```

If you change the shape of what the backend sends or accepts, regenerate the
contracts so the frontend stays in sync. [ADR 0001](docs/adr/0001-committed-generated-contracts.md)
explains why:

```bash
just generate-contracts
```

## Commit Messages

Commits follow [Conventional Commits](https://www.conventionalcommits.org/). A git
hook checks each message with `commitlint`. For example:

```text
feat(rooms): add spectator reconnect
fix(scoring): reject short-substring fuzzy matches
```

## Project Layout

See [docs/architecture.md](docs/architecture.md) for how the frontend, backend,
and contracts fit together.
