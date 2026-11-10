# Accessibility statement

This page covers 6-second-scribbles at [6ss.duinlab.nl](https://6ss.duinlab.nl).
Simon van Lierde builds 6-second-scribbles and is responsible for this page.

## Using 6-second-scribbles

You can:

- switch to a dark theme, which follows your device's setting;
- find the controls by their role and name, which the end-to-end tests rely on.

The drawing canvas needs a mouse, finger or stylus. The game is built for desktop screens for now.

## How accessible 6-second-scribbles is

6-second-scribbles aims to meet [WCAG 2.2](https://www.w3.org/TR/WCAG22/) at level AA.

Its conformance is **not assessed**: nobody has checked it against every WCAG 2.2 rule yet.
Simon van Lierde runs the checks below. No outside expert has tested it.

## Known problems

- Drawing is possible only with a pointing device, and there is no keyboard alternative. No fix planned.
  [2.1.1 Keyboard]
- The layout is built for desktop and is not tuned for small screens. No fix planned.
  [1.4.10 Reflow]

## Tell us about a problem

If any part of 6-second-scribbles is hard or impossible for you to use, email
[code@duinlab.nl](mailto:code@duinlab.nl). Tell us what you tried to do, what happened, and
which browser and assistive technology you use, if any. If you have a GitHub account, you can also
[open an issue](https://github.com/simonvanlierde/6-second-scribbles/issues/new).

We'll reply within 10 working days.

## How we check

These automatic checks run on every proposed change:

- [axe-core](https://github.com/dequelabs/axe-core) scans the home page, settings panel, design-system
  page, lobby, drawing, guessing and round results in both themes for WCAG 2.1 level A and AA problems.
- [Biome's accessibility rules](https://biomejs.dev/linter/javascript/rules/#a11y) check the code for
  mistakes such as missing alt text or invalid ARIA.

Automatic tools find only some problems, so passing them doesn't mean there are none.
Nobody has tested 6-second-scribbles by hand with only a keyboard or with a screen reader.
It needs HTML, CSS and JavaScript to work.

## About this statement

Prepared: 9 November 2026

Last reviewed: 10 November 2026

Next review: within 12 months of the last review.

Method: self-assessment, using the checks under How we check.
