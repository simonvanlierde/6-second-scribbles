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
            "burger",
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
            "soccer",
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
            "burger",
            "cheeseburger",
            "chef",
            "club sandwich",
            "cobra",
            "college",
            "cookie",
            "cyclone",
            "express",
            "football",
            "force",
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
            "chopper",
            "club sandwich",
            "cobra",
            "dessert",
            "flipper",
            "guppy",
            "hot dog",
            "jeans",
            "jelly bean",
            "jet",
            "jogging",
            "larva",
            "pickup",
            "pony",
            "putter",
            "sneakers",
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
            "butterscotch",
            "cafe",
            "cake",
            "cheeseburger",
            "chopper",
            "cobra",
            "cookie",
            "cumulus",
            "dessert",
            "disco",
            "driver",
            "flipper",
            "gelato",
            "gremlin",
            "guppy",
            "hamburger",
            "horror",
            "hype",
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
            "chopper",
            "club sandwich",
            "cookie",
            "dessert",
            "disco",
            "driver",
            "fairness",
            "fedora",
            "Flipper",
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
            "Patty",
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
            "Twister",
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
            "chopper",
            "disco",
            "gelato",
            "gremlin",
            "hamburger",
            "horror",
            "jogging",
            "market",
            "parka",
            "portal",
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
            "bongô",
            "bot",
            "bowling",
            "cheeseburger",
            "chopper",
            "cone",
            "cookie",
            "harmónica",
            "jeans",
            "larva",
            "lunar",
            "medusa",
            "playground",
            "portal",
            "puzzle",
            "romance",
            "solar",
            "t-shirt",
            "terminal",
            "terror",
            "tutor",
            "zzz",
        }
    ),
}

# Answers that two or more cards of one category share on purpose, because the word truly
# names each of those cards. Any other shared answer fails the collision check below.
SHARED_ANSWERS: tuple[tuple[str, str, str, frozenset[str]], ...] = (
    # a chopper is also a style of motorcycle
    (
        "en",
        "vehicles",
        "chopper",
        frozenset(
            {
                "helicopter",
                "motorcycle",
            }
        ),
    ),
    # a ladybug is a beetle
    (
        "de",
        "insects",
        "Käfer",
        frozenset(
            {
                "beetle",
                "ladybug",
            }
        ),
    ),
    (
        "en",
        "insects",
        "beetle",
        frozenset(
            {
                "beetle",
                "ladybug",
            }
        ),
    ),
    (
        "nl",
        "insects",
        "kever",
        frozenset(
            {
                "beetle",
                "ladybug",
            }
        ),
    ),
    (
        "pl",
        "insects",
        "żuk",
        frozenset(
            {
                "beetle",
                "ladybug",
            }
        ),
    ),
    (
        "pt",
        "insects",
        "besouro",
        frozenset(
            {
                "beetle",
                "ladybug",
            }
        ),
    ),
    (
        "zh-CN",
        "insects",
        "甲虫",
        frozenset(
            {
                "beetle",
                "ladybug",
            }
        ),
    ),
    (
        "zh-TW",
        "insects",
        "甲蟲",
        frozenset(
            {
                "beetle",
                "ladybug",
            }
        ),
    ),
    # a smiling face fits happy and laughing
    (
        "ja",
        "emotions",
        "笑顔",
        frozenset(
            {
                "happy",
                "laughing",
            }
        ),
    ),
    # arm and leg are both limbs
    (
        "en",
        "body-parts",
        "limb",
        frozenset(
            {
                "arm",
                "leg",
            }
        ),
    ),
    (
        "es",
        "body-parts",
        "extremidad",
        frozenset(
            {
                "arm",
                "leg",
            }
        ),
    ),
    (
        "fr",
        "body-parts",
        "membre",
        frozenset(
            {
                "arm",
                "leg",
            }
        ),
    ),
    (
        "it",
        "body-parts",
        "arto",
        frozenset(
            {
                "arm",
                "leg",
            }
        ),
    ),
    (
        "nl",
        "body-parts",
        "ledematen",
        frozenset(
            {
                "arm",
                "leg",
            }
        ),
    ),
    (
        "pl",
        "body-parts",
        "kończyna",
        frozenset(
            {
                "arm",
                "leg",
            }
        ),
    ),
    (
        "pt",
        "body-parts",
        "membro",
        frozenset(
            {
                "arm",
                "leg",
            }
        ),
    ),
    # bagno is used for the toilet and for a bath
    (
        "it",
        "bathroom-items",
        "bagno",
        frozenset(
            {
                "bathtub",
                "toilet",
            }
        ),
    ),
    # bike names a bicycle and a motorbike
    (
        "en",
        "vehicles",
        "bike",
        frozenset(
            {
                "bicycle",
                "motorcycle",
            }
        ),
    ),
    # bombón is a chocolate, and a marshmallow in Mexico
    (
        "es",
        "candy",
        "bombón",
        frozenset(
            {
                "chocolate",
                "marshmallow",
            }
        ),
    ),
    # boterham is a slice of bread and an open sandwich
    (
        "nl",
        "food",
        "boterham",
        frozenset(
            {
                "bread",
                "sandwich",
            }
        ),
    ),
    # both are berries in everyday speech
    (
        "de",
        "fruits",
        "beeren",
        frozenset(
            {
                "blueberry",
                "strawberry",
            }
        ),
    ),
    (
        "es",
        "fruits",
        "bayas",
        frozenset(
            {
                "blueberry",
                "strawberry",
            }
        ),
    ),
    (
        "fr",
        "fruits",
        "baies",
        frozenset(
            {
                "blueberry",
                "strawberry",
            }
        ),
    ),
    (
        "ko",
        "fruits",
        "베리",
        frozenset(
            {
                "blueberry",
                "strawberry",
            }
        ),
    ),
    (
        "pt",
        "fruits",
        "bagas",
        frozenset(
            {
                "blueberry",
                "strawberry",
            }
        ),
    ),
    (
        "zh-CN",
        "fruits",
        "浆果",
        frozenset(
            {
                "blueberry",
                "strawberry",
            }
        ),
    ),
    # camión is a bus in Mexico and a truck elsewhere
    (
        "es",
        "vehicles",
        "camión",
        frozenset(
            {
                "bus",
                "truck",
            }
        ),
    ),
    # crab and lobster are both shellfish
    (
        "es",
        "sea-creatures",
        "marisco",
        frozenset(
            {
                "crab",
                "lobster",
            }
        ),
    ),
    # drum and maracas are both percussion
    (
        "en",
        "musical-instruments",
        "percussion",
        frozenset(
            {
                "drum",
                "maracas",
            }
        ),
    ),
    (
        "it",
        "musical-instruments",
        "percussioni",
        frozenset(
            {
                "drum",
                "maracas",
            }
        ),
    ),
    (
        "ko",
        "musical-instruments",
        "타악기",
        frozenset(
            {
                "drum",
                "maracas",
            }
        ),
    ),
    (
        "nl",
        "musical-instruments",
        "percussie",
        frozenset(
            {
                "drum",
                "maracas",
            }
        ),
    ),
    (
        "zh-CN",
        "musical-instruments",
        "打击乐器",
        frozenset(
            {
                "drum",
                "maracas",
            }
        ),
    ),
    (
        "zh-TW",
        "musical-instruments",
        "打擊樂器",
        frozenset(
            {
                "drum",
                "maracas",
            }
        ),
    ),
    # fork, knife and spoon are all cutlery
    (
        "de",
        "kitchen-items",
        "Besteck",
        frozenset(
            {
                "fork",
                "knife",
                "spoon",
            }
        ),
    ),
    (
        "es",
        "kitchen-items",
        "cubierto",
        frozenset(
            {
                "fork",
                "knife",
                "spoon",
            }
        ),
    ),
    (
        "fr",
        "kitchen-items",
        "couvert",
        frozenset(
            {
                "fork",
                "knife",
                "spoon",
            }
        ),
    ),
    (
        "it",
        "kitchen-items",
        "posate",
        frozenset(
            {
                "fork",
                "knife",
            }
        ),
    ),
    (
        "ja",
        "kitchen-items",
        "カトラリー",
        frozenset(
            {
                "fork",
                "spoon",
            }
        ),
    ),
    (
        "pl",
        "kitchen-items",
        "sztućce",
        frozenset(
            {
                "fork",
                "knife",
                "spoon",
            }
        ),
    ),
    (
        "pt",
        "kitchen-items",
        "talher",
        frozenset(
            {
                "fork",
                "knife",
                "spoon",
            }
        ),
    ),
    # guitar and violin are both string instruments
    (
        "de",
        "musical-instruments",
        "Saiteninstrument",
        frozenset(
            {
                "guitar",
                "violin",
            }
        ),
    ),
    (
        "en",
        "musical-instruments",
        "string instrument",
        frozenset(
            {
                "guitar",
                "violin",
            }
        ),
    ),
    (
        "es",
        "musical-instruments",
        "instrumento de cuerda",
        frozenset(
            {
                "guitar",
                "violin",
            }
        ),
    ),
    (
        "nl",
        "musical-instruments",
        "snaarinstrument",
        frozenset(
            {
                "guitar",
                "violin",
            }
        ),
    ),
    (
        "zh-CN",
        "musical-instruments",
        "弦乐器",
        frozenset(
            {
                "guitar",
                "violin",
            }
        ),
    ),
    (
        "zh-TW",
        "musical-instruments",
        "弦樂器",
        frozenset(
            {
                "guitar",
                "violin",
            }
        ),
    ),
    # hamster and mouse are both rodents
    (
        "en",
        "pets",
        "rodent",
        frozenset(
            {
                "hamster",
                "mouse",
            }
        ),
    ),
    (
        "es",
        "pets",
        "roedor",
        frozenset(
            {
                "hamster",
                "mouse",
            }
        ),
    ),
    (
        "fr",
        "pets",
        "rongeur",
        frozenset(
            {
                "hamster",
                "mouse",
            }
        ),
    ),
    (
        "it",
        "pets",
        "roditore",
        frozenset(
            {
                "hamster",
                "mouse",
            }
        ),
    ),
    (
        "nl",
        "pets",
        "knaagdieren",
        frozenset(
            {
                "hamster",
                "mouse",
            }
        ),
    ),
    (
        "pl",
        "pets",
        "gryzoń",
        frozenset(
            {
                "hamster",
                "mouse",
            }
        ),
    ),
    # plates and bowls are both dishes
    (
        "en",
        "kitchen-items",
        "dish",
        frozenset(
            {
                "bowl",
                "plate",
            }
        ),
    ),
    # ręka means both hand and arm
    (
        "pl",
        "body-parts",
        "ręka",
        frozenset(
            {
                "arm",
                "hand",
            }
        ),
    ),
    # sorcier is the wizard's word; it meets sorcière only through the plural rule
    (
        "fr",
        "fantasy",
        "sorcière",
        frozenset(
            {
                "witch",
                "wizard",
            }
        ),
    ),
    # taco is a golf club and a hockey stick
    (
        "pt",
        "sports-equipment",
        "taco",
        frozenset(
            {
                "golf-club",
                "hockey-stick",
            }
        ),
    ),
    # the word covers caterpillars in everyday speech
    (
        "es",
        "insects",
        "gusano",
        frozenset(
            {
                "caterpillar",
                "worm",
            }
        ),
    ),
    (
        "pl",
        "insects",
        "robak",
        frozenset(
            {
                "caterpillar",
                "worm",
            }
        ),
    ),
    # the word covers elves and goblins
    (
        "fr",
        "fantasy",
        "lutin",
        frozenset(
            {
                "elf",
                "goblin",
            }
        ),
    ),
    (
        "pt",
        "fantasy",
        "duende",
        frozenset(
            {
                "elf",
                "goblin",
            }
        ),
    ),
    (
        "nl",
        "fantasy",
        "elfje",
        frozenset(
            {
                "elf",
                "fairy",
            }
        ),
    ),
    (
        "zh-CN",
        "fantasy",
        "精灵",
        frozenset(
            {
                "elf",
                "fairy",
            }
        ),
    ),
    (
        "zh-TW",
        "fantasy",
        "精靈",
        frozenset(
            {
                "elf",
                "fairy",
            }
        ),
    ),
    # the word covers gummy bears and jelly beans
    (
        "es",
        "candy",
        "gominola",
        frozenset(
            {
                "gummy-bear",
                "jellybean",
            }
        ),
    ),
    (
        "pl",
        "candy",
        "żelek",
        frozenset(
            {
                "gummy-bear",
                "jellybean",
            }
        ),
    ),
    (
        "en",
        "architecture",
        "tall building",
        frozenset(
            {
                "skyscraper",
                "tower",
            }
        ),
    ),
    (
        "ko",
        "architecture",
        "고층 건물",
        frozenset(
            {
                "skyscraper",
                "tower",
            }
        ),
    ),
    (
        "nl",
        "architecture",
        "hoog gebouw",
        frozenset(
            {
                "skyscraper",
                "tower",
            }
        ),
    ),
    (
        "pl",
        "architecture",
        "wysoki budynek",
        frozenset(
            {
                "skyscraper",
                "tower",
            }
        ),
    ),
    # 裙子 covers dresses and skirts
    (
        "zh-CN",
        "clothes",
        "裙子",
        frozenset(
            {
                "dress",
                "skirt",
            }
        ),
    ),
    (
        "zh-TW",
        "clothes",
        "裙子",
        frozenset(
            {
                "dress",
                "skirt",
            }
        ),
    ),
    # 足 means both foot and leg
    (
        "ja",
        "body-parts",
        "足",
        frozenset(
            {
                "foot",
                "leg",
            }
        ),
    ),
    # 锅 covers pans and pots
    (
        "zh-CN",
        "kitchen-items",
        "锅",
        frozenset(
            {
                "pan",
                "pot",
            }
        ),
    ),
    # 雷 is thunder and lightning
    (
        "ja",
        "weather-phenomena",
        "雷",
        frozenset(
            {
                "lightning",
                "thunder",
            }
        ),
    ),
    # 魔法使い is any magic user, witch or wizard
    (
        "ja",
        "fantasy",
        "魔法使い",
        frozenset(
            {
                "witch",
                "wizard",
            }
        ),
    ),
    # both are berries in everyday speech
    (
        "pt",
        "fruits",
        "frutas vermelhas",
        frozenset(
            {
                "blueberry",
                "strawberry",
            }
        ),
    ),
    # power is an everyday word for both
    (
        "en",
        "scientific-terms",
        "power",
        frozenset(
            {
                "electricity",
                "energy",
            }
        ),
    ),
)
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


def _collisions() -> list[tuple[str, str, str, str, str, str]]:
    """Return (category, locale, card, word, other card, other word) for words that score for two cards."""
    prompts = {prompt["id"]: prompt for prompt in PROMPTS}
    found = []
    for category in CATEGORIES:
        words: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for item in category["items"]:
            for tr in prompts[item]["translations"]:
                for word in [tr["label"], *(tr.get("aliases") or [])]:
                    words[tr["locale"]].append((item, word))
        for locale, pairs in words.items():
            found.extend(
                (category["id"], locale, item_a, word_a, item_b, word_b)
                for i, (item_a, word_a) in enumerate(pairs)
                for item_b, word_b in pairs[i + 1 :]
                if item_a != item_b and guess_matcher.exact_match(word_a, word_b, locale)
            )
    return found


def _allowed_by(collision: tuple[str, str, str, str, str, str]) -> int | None:
    """Return the index of the SHARED_ANSWERS entry that allows a collision, if any."""
    category, locale, item_a, word_a, item_b, word_b = collision
    for index, (entry_locale, entry_category, answer, cards) in enumerate(SHARED_ANSWERS):
        if (
            (entry_locale, entry_category) == (locale, category)
            and {item_a, item_b} <= cards
            and guess_matcher.exact_match(answer, word_a, locale)
            and guess_matcher.exact_match(answer, word_b, locale)
        ):
            return index
    return None


def test_no_alias_matches_another_card_in_the_same_category() -> None:
    """A guess scores for one card only, unless the shared answer is listed as fitting every card."""
    bad = [collision for collision in _collisions() if _allowed_by(collision) is None]
    assert not bad, f"{len(bad)} collisions: {bad}"


def test_every_shared_answer_entry_is_still_needed() -> None:
    """An allowlist entry that no longer matches a shared answer is stale."""
    used = {_allowed_by(collision) for collision in _collisions()}
    stale = [entry for index, entry in enumerate(SHARED_ANSWERS) if index not in used]
    assert not stale, f"{len(stale)} stale entries: {stale}"


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
