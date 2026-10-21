"""Quality checks on the seed deck's translations.

Aliases score guesses: a wrong alias awards points for a wrong word, and a junk one is noise
in the answer list. These checks catch the leftovers of the machine translation.
"""

from __future__ import annotations

import string
from collections import defaultdict
from typing import TYPE_CHECKING

from app.scoring import guess_matcher, normalize_text
from scripts.seed_data import SEED_DATA

if TYPE_CHECKING:
    from typing import Any

ENGLISH = "en"
CJK_LOCALES = frozenset({"ja", "ko", "zh-CN", "zh-TW"})

# Text the translator produced from markup or web-page chrome (menus, footers), not from the
# source word. A lone "·" is caught as punctuation; inside a Chinese name it is the usual separator.
JUNK_TOKENS = (
    *("이름", "뚱 베어", "사이트맵", "스낵 바", "카테고리", "회사", "제품", "주 메뉴", "주요 특징", "한국어"),
    *("관련 기사", "인기", "공유하기", "안내", "소개", "여행 정보", "언어:", "ログイン"),
    *("»", "₢", "*", "#", "!"),
)

# Proper names read the same in every locale.
NAMES = frozenset(
    {
        "albert einstein",
        "charles darwin",
        "darwin",
        "mahatma gandhi",
        "gandhi",
        "pablo picasso",
        "picasso",
        "thomas edison",
        "edison",
        "william shakespeare",
        "shakespeare",
        "wolfgang amadeus mozart",
        "mozart",
        "napoleon bonaparte",
        "napoleon",
        "julius caesar",
        "newton",
        "giza",
        "cleopatra",
        "einstein",
    }
)

# Loanwords and words spelled like their English counterpart, each a real word in the locale.
# Without an entry, an alias equal to the English label or alias counts as untranslated.
# spell-checker: disable
SHARED_WORDS: dict[str, frozenset[str]] = {
    "es": frozenset(
        {
            "ananas",
            "auto",
            "banana",
            "basilica",
            "bistro",
            "bot",
            "bus",
            "doctor",
            "horror",
            "hot dog",
            "instructor",
            "jeans",
            "jet",
            "larva",
            "parka",
            "puzzle",
            "romance",
            "softball",
            "terminal",
            "terror",
            "titan",
            "tutor",
            "zoo",
        }
    ),
    "fr": frozenset(
        {
            "affection",
            "amusement",
            "auto",
            "baguette",
            "baseball",
            "bistro",
            "bonnet",
            "bot",
            "cheeseburger",
            "chef",
            "club sandwich",
            "cobra",
            "college",
            "cyclone",
            "express",
            "football",
            "graphite",
            "guppy",
            "jet",
            "jogging",
            "journal",
            "locomotive",
            "mage",
            "paprika",
            "parka",
            "piston",
            "plantain",
            "putter",
            "rage",
            "reptile",
            "resistance",
            "romance",
            "submersible",
            "t-shirt",
            "temple",
            "titan",
        }
    ),
    "it": frozenset(
        {
            "automobile",
            "baguette",
            "ballerina",
            "basilica",
            "bongo",
            "cheeseburger",
            "chewing gum",
            "club sandwich",
            "cobra",
            "guppy",
            "hot dog",
            "jeans",
            "jelly bean",
            "jet",
            "jogging",
            "larva",
            "pony",
            "putter",
            "softball",
            "t-shirt",
            "terminal",
            "timer",
            "toast",
            "villa",
            "yacht",
        }
    ),
    "nl": frozenset(
        {
            "ballerina",
            "biscuit",
            "bistro",
            "blouse",
            "bongo",
            "bot",
            "cafe",
            "cheeseburger",
            "cobra",
            "cumulus",
            "dessert",
            "disco",
            "driver",
            "gelato",
            "gremlin",
            "guppy",
            "hamburger",
            "horror",
            "jeans",
            "kitten",
            "menthol",
            "monster",
            "parka",
            "pen",
            "plant",
            "pony",
            "portal",
            "puppy",
            "putter",
            "ram",
            "sandwich",
            "ski",
            "sneakers",
            "spectrum",
            "t-shirt",
            "terminal",
            "toast",
            "viaduct",
            "villa",
            "zzz",
        }
    ),
    "de": frozenset(
        {
            "amusement",
            "baguette",
            "ballerina",
            "bistro",
            "blizzard",
            "bongo",
            "bot",
            "bubblegum",
            "cafe",
            "cheeseburger",
            "chlorophyll",
            "club sandwich",
            "cookie",
            "dessert",
            "disco",
            "driver",
            "fairness",
            "fedora",
            "frankfurter",
            "general",
            "goblin",
            "gremlin",
            "guppy",
            "hamburger",
            "horn",
            "hot dog",
            "jeans",
            "jelly bean",
            "jet",
            "lollipop",
            "menthol",
            "monster",
            "parka",
            "pony",
            "portal",
            "professor",
            "putter",
            "rage",
            "rose",
            "shop",
            "shuttle",
            "ski",
            "softball",
            "t-shirt",
            "terminal",
            "timer",
            "titan",
            "toast",
            "toffee",
            "truck",
            "villa",
            "viper",
            "yacht",
            "zzz",
        }
    ),
    "pl": frozenset(
        {
            "auto",
            "bistro",
            "bongo",
            "bot",
            "bus",
            "cheeseburger",
            "disco",
            "gelato",
            "gremlin",
            "hamburger",
            "horror",
            "jogging",
            "market",
            "parka",
            "softball",
            "t-shirt",
            "terminal",
            "timer",
            "zzz",
        }
    ),
    "pt": frozenset(
        {
            "ananas",
            "basilica",
            "bistro",
            "bot",
            "cheeseburger",
            "cone",
            "jeans",
            "larva",
            "medusa",
            "playground",
            "portal",
            "puzzle",
            "romance",
            "terminal",
            "terror",
            "tutor",
            "zzz",
        }
    ),
}
# spell-checker: enable

PROMPTS: list[dict[str, Any]] = SEED_DATA["prompts"]
CATEGORIES: list[dict[str, Any]] = SEED_DATA["system_categories"]


def _entries() -> list[tuple[str, str, str, str]]:
    """Return (prompt id, locale, field, text) for every label and alias."""
    rows = []
    for prompt in PROMPTS:
        for tr in prompt["translations"]:
            rows.append((prompt["id"], tr["locale"], "label", tr["label"]))
            rows.extend((prompt["id"], tr["locale"], "alias", alias) for alias in tr.get("aliases") or [])
    rows.extend(
        (f"category:{category['id']}", tr["locale"], "name", tr["name"])
        for category in CATEGORIES
        for tr in category["translations"]
    )
    return rows


def _is_punctuation(text: str) -> bool:
    return all(not ch.isalnum() for ch in text)


def test_no_junk_tokens_or_punctuation_only_text() -> None:
    """No label, alias or category name holds a junk token or only punctuation."""
    bad = [
        row
        for row in _entries()
        if not row[3].strip() or _is_punctuation(row[3]) or any(token in row[3] for token in JUNK_TOKENS)
    ]
    assert not bad, f"{len(bad)} junk entries: {bad}"


def test_no_ascii_only_text_in_cjk_locales() -> None:
    """Japanese, Korean and Chinese entries are written in their own script."""
    bad = [row for row in _entries() if row[1] in CJK_LOCALES and row[3].isascii() and not row[3].isdigit()]
    assert not bad, f"{len(bad)} ASCII-only entries: {bad}"


def test_no_untranslated_english_aliases() -> None:
    """An alias outside English is not the card's English label or alias, unless it is shared."""
    bad = []
    for prompt in PROMPTS:
        english = next(tr for tr in prompt["translations"] if tr["locale"] == ENGLISH)
        english_words = {normalize_text(word) for word in [english["label"], *(english.get("aliases") or [])]}
        for tr in prompt["translations"]:
            if tr["locale"] == ENGLISH:
                continue
            shared = {normalize_text(word) for word in NAMES | SHARED_WORDS.get(tr["locale"], frozenset())}
            bad.extend(
                (prompt["id"], tr["locale"], alias)
                for alias in tr.get("aliases") or []
                if normalize_text(alias) in english_words and normalize_text(alias) not in shared
            )
    assert not bad, f"{len(bad)} untranslated aliases: {bad}"


def test_no_alias_matches_another_card_in_the_same_category() -> None:
    """A guess must not score for two cards of one category, so their words must not collide."""
    prompts = {prompt["id"]: prompt for prompt in PROMPTS}
    bad = []
    for category in CATEGORIES:
        words: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for item in category["items"]:
            for tr in prompts[item]["translations"]:
                for word in [tr["label"], *(tr.get("aliases") or [])]:
                    words[tr["locale"]].append((item, word))
        for locale, pairs in words.items():
            bad.extend(
                (category["id"], locale, item_a, word_a, item_b, word_b)
                for i, (item_a, word_a) in enumerate(pairs)
                for item_b, word_b in pairs[i + 1 :]
                if item_a != item_b and guess_matcher.exact_match(word_a, word_b)
            )
    assert not bad, f"{len(bad)} collisions: {bad}"


def test_aliases_are_unique_and_differ_from_the_label() -> None:
    """An alias that repeats the label or another alias adds nothing."""
    bad = []
    for prompt in PROMPTS:
        for tr in prompt["translations"]:
            seen = {normalize_text(tr["label"])}
            for alias in tr.get("aliases") or []:
                if normalize_text(alias) in seen:
                    bad.append((prompt["id"], tr["locale"], alias))
                seen.add(normalize_text(alias))
    assert not bad, f"{len(bad)} repeated aliases: {bad}"


def test_text_has_no_stray_whitespace_or_markup() -> None:
    """Entries are trimmed and hold no characters a player could not type as an answer."""
    stray = set(string.punctuation) - set("-'.&")
    bad = [row for row in _entries() if row[3] != row[3].strip() or " " * 2 in row[3] or set(row[3]) & stray]
    assert not bad, f"{len(bad)} entries with stray whitespace or symbols: {bad}"
