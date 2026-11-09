# Security

## Report a vulnerability

Report it privately, through
[a GitHub security advisory](https://github.com/simonvanlierde/6-second-scribbles/security/advisories/new)
or by email to <code@duinlab.nl>. Don't open a public issue or pull request for it:
anyone can read those before there is a fix.

Please include:

- What the problem is and where it is: a file, a function or a dependency.
- Steps to reproduce it, or a proof of concept.
- The impact you expect, and the version you saw it in.

I acknowledge a report within 14 days, then tell you whether I can reproduce it and when I
expect a fix.

## Fixes and disclosure

A fix ships in a new release. When it is out, I publish the GitHub security advisory for
it, with a CVE where one applies, and credit you unless you'd rather not be named. The
CHANGELOG entry for that release links the advisory.

## Scope

6-second-scribbles is a game server and web app. It keeps no accounts.

In scope:

- The code in this repository and what it builds, including the live site at 6ss.duinlab.nl.
- The CI and release workflows in `.github/workflows`.
- The dependencies in the lockfiles, when the problem affects this project.

Out of scope:

- A problem in a dependency that doesn't affect this project. Report it upstream.
