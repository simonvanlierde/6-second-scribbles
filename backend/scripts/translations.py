"""Review the word deck with a language model, one category at a time.

    uv run python -m scripts.translations request <locale> [--category ID ...]
    uv run python -m scripts.translations apply <file.csv> [--dry-run]

`request` writes translation-review/<locale>.md at the repository root (gitignored): every
category with all its cards, labels and aliases in English and in <locale>, so the reviewer
judges each word in the sense its category and English card give it. Paste it into the model.

`apply` reads the model's CSV block (columns: language, category, card, field, proposed,
reason), sets each label or alias list in seed_data.yaml, and runs the deck's quality tests.
Rows that name an unknown language, category, card or field are listed and skipped.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

import yaml

BACKEND = Path(__file__).resolve().parents[1]
SEED = BACKEND / "scripts" / "seed_data.yaml"
OUT = BACKEND.parent / "translation-review"

LANGUAGES = {
    "de": "German",
    "es": "Spanish",
    "fr": "French",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "nl": "Dutch",
    "pl": "Polish",
    "pt": "Portuguese",
    "zh-CN": "Chinese (Simplified)",
    "zh-TW": "Chinese (Traditional)",
}

INSTRUCTIONS = """\
# Word deck review: Six Second Scribbles, {language}

Six Second Scribbles is a party game: a player gets a category and draws its cards one after
another, a few seconds each, while the others type guesses. Each card has a **label**, the word
the drawer is asked to draw, and **aliases**, other answers the game accepts as correct.
Players never see the aliases. Live at <https://6ss.duinlab.nl>.

Below is every category with all its cards, in English and in {language}. Review the {language}.

- Read each word in the sense its **category and English card** give it. In Vehicles, "plane"
  is an aircraft, never a flat surface or a steppe.
- A label should be the everyday word a {language} speaker would use while playing, not a
  literal translation.
- Aliases are words people would really type for this card: synonyms, the common short form,
  a common spelling variant. Remove anything that names something else, is a rare or formal
  word, or is in another language (a loanword {language} speakers actually use is fine).
- No answer may be accepted by two cards in the same category: if two cards share an alias,
  keep it on the card it names best, or on neither.
- An alias must differ from its card's label.

## How to answer

Go through the categories in order. For each one, write a few lines of notes on what you would
change and why, then "checked". After the last category, give one CSV block with only the
cards you change, in this format:

```csv
language,category,card,field,proposed,reason
{locale},vehicles,airplane,aliases,avion; jet,"dropped X: means a steppe"
```

- `field` is `label` or `aliases`.
- For `aliases`, `proposed` is the **complete new list**, separated by "; ". Leave it empty to
  remove every alias.
- One row per field you change. Keep the reason short.

There are {categories} categories and {cards} cards.
"""


def load() -> dict:
    return yaml.safe_load(SEED.read_text(encoding="utf-8"))


def save(data: dict) -> None:
    # Empty alias lists as [], not null, so every card has the same shape.
    for prompt in data["prompts"]:
        for translation in prompt["translations"]:
            if translation.get("aliases") is None:
                translation["aliases"] = []
    SEED.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _entry(translations: list[dict], locale: str) -> dict | None:
    return next((t for t in translations if t["locale"] == locale), None)


def _words(entry: dict | None, key: str) -> str:
    if entry is None:
        return "(missing)"
    aliases = "; ".join(entry.get("aliases") or [])
    return f"{entry[key]}" + (f" (also: {aliases})" if aliases else "")


def request(locale: str, categories: list[str]) -> Path:
    """Write the review request for one locale and return its path."""
    data = load()
    prompts = {p["id"]: p for p in data["prompts"]}
    picked = [c for c in data["system_categories"] if not categories or c["id"] in categories]
    lines = [
        INSTRUCTIONS.format(
            language=LANGUAGES[locale],
            locale=locale,
            categories=len(picked),
            cards=sum(len(c["items"]) for c in picked),
        )
    ]
    for category in picked:
        en = _entry(category["translations"], "en")
        target = _entry(category["translations"], locale)
        lines += [
            f"## {category['id']}: {en['name'] if en else category['id']} / "
            f"{target['name'] if target else '(missing)'} ({category['difficulty']})",
            "",
            "| card | English | " + LANGUAGES[locale] + " |",
            "| --- | --- | --- |",
        ]
        for card in category["items"]:
            translations = prompts[card]["translations"]
            english = _words(_entry(translations, "en"), "label")
            current = _words(_entry(translations, locale), "label")
            lines.append(f"| {card} | {english} | {current} |".replace("\n", " "))
        lines.append("")
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{locale}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def apply(path: Path, *, dry_run: bool) -> int:
    """Apply a returned CSV to seed_data.yaml, then run the deck tests; return the exit code."""
    data = load()
    prompts = {p["id"]: p for p in data["prompts"]}
    members = {c["id"]: set(c["items"]) for c in data["system_categories"]}
    applied: list[str] = []
    skipped: list[str] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            locale, category, card = row["language"].strip(), row["category"].strip(), row["card"].strip()
            field, proposed = row["field"].strip(), row["proposed"].strip()
            where = f"{locale} {category}/{card} {field}"
            if locale not in LANGUAGES or card not in members.get(category, set()):
                skipped.append(f"{where}: unknown language, category or card")
                continue
            entry = _entry(prompts[card]["translations"], locale)
            if entry is None or field not in {"label", "aliases"}:
                skipped.append(f"{where}: no {locale} entry, or field is not label or aliases")
                continue
            if field == "label":
                if not proposed:
                    skipped.append(f"{where}: empty label")
                    continue
                entry["label"] = proposed
            else:
                aliases = [a.strip() for a in proposed.split(";") if a.strip()]
                entry["aliases"] = list(dict.fromkeys(aliases))
            applied.append(f"{where} -> {proposed or '(none)'}: {row.get('reason', '').strip()}")
    for name, rows in (("Applied", applied), ("Skipped", skipped)):
        print(f"{name} ({len(rows)}):", *(f"  {r}" for r in rows), sep="\n")
    if dry_run:
        return 0
    save(data)
    tests = ["uv", "run", "pytest", "-q", "tests/unit/test_seed_data_quality.py"]
    return subprocess.run(tests, cwd=BACKEND, check=False).returncode  # noqa: S603


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    req = sub.add_parser("request", help="write a review request for one language")
    req.add_argument("locale", choices=sorted(LANGUAGES))
    req.add_argument("--category", action="append", default=[], help="only this category (repeatable)")
    app = sub.add_parser("apply", help="apply a returned CSV to seed_data.yaml")
    app.add_argument("csv", type=Path)
    app.add_argument("--dry-run", action="store_true", help="list the changes without writing")
    args = parser.parse_args()
    if args.command == "request":
        print(request(args.locale, args.category))
        return 0
    return apply(args.csv, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
