"""Fuzzy matching and scoring logic for guess validation.

Uses rapidfuzz for high-performance fuzzy string matching.
"""

from __future__ import annotations

__all__ = [
    "GuessMatcher",
    "GuessTarget",
    "guess_matcher",
    "normalize_text",
]

import functools
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz


@dataclass(frozen=True)
class GuessTarget:
    """One canonical guess target with its localized accepted answers."""

    item_id: int
    label: str
    aliases: list[str]


def normalize_text(text: str) -> str:
    """Normalize text for comparison: casefold, strip, remove accents.

    Strips combining marks (accents) so ``café`` matches ``cafe``, but preserves
    the base characters of every script. The previous ``encode("ascii", "ignore")``
    dropped all non-Latin text to an empty string, making Cyrillic/CJK/Greek/Arabic
    answers permanently unscoreable.

    NOTE: accent-insensitive is correct for every shipped locale (European
    accents are optional; CJK/Korean carry no combining marks on their bases). It
    would over-match a tone/diacritic-phonemic locale where the mark IS the letter
    (Vietnamese ``má``/``ma``/``mã``, Arabic harakat). Make stripping locale-aware
    (thread the room locale from ``score_round``) if such a locale is ever added.
    """
    decomposed = unicodedata.normalize("NFD", text.casefold())
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    # Strip after dropping marks: a stray mark would otherwise shield a space next to it.
    return unicodedata.normalize("NFC", without_marks).strip()


# Languages whose regular plural adds -s or -es. Others (German "Ei"/"Eis", Dutch,
# Polish, Italian, CJK) form plurals differently, so a blind -s would join two words.
ENGLISH = "en"
_S_PLURAL_LANGUAGES = frozenset({ENGLISH, "es", "fr", "pt"})


@functools.lru_cache(maxsize=1024)
def _generate_variants(normalized: str, locale: str | None = None) -> frozenset[str]:
    """Generate the plural (and English -ing) variants of a normalized word.

    ``locale`` is the guesser's language; None keeps the English rules.
    """
    language = (locale or ENGLISH).split("-")[0].lower()
    variants = {normalized}

    if language in _S_PLURAL_LANGUAGES:
        if normalized.endswith("s"):
            variants.add(normalized[:-1])
            if normalized.endswith("es"):
                variants.add(normalized[:-2])
        else:
            variants.add(f"{normalized}s")
            variants.add(f"{normalized}es")

    if language == ENGLISH and normalized.endswith("ing"):
        variants.add(normalized[:-3])

    # A word that is all suffix ("s", "es", "ing") would leave "", which every such word shares.
    variants.discard("")
    return frozenset(variants)


class GuessMatcher:
    """Handles fuzzy matching of player guesses against correct answers."""

    FUZZY_MATCH_THRESHOLD = 85

    def exact_match(self, guess: str, target: str, locale: str | None = None) -> bool:
        """Check if guess exactly matches target, allowing the language's plural endings."""
        return bool(
            _generate_variants(normalize_text(guess), locale) & _generate_variants(normalize_text(target), locale)
        )

    def fuzzy_match(self, guess: str, target: str, locale: str | None = None) -> tuple[bool, float]:
        """Check if guess fuzzy matches target."""
        guess_norm = normalize_text(guess)
        target_norm = normalize_text(target)

        if self.exact_match(guess, target, locale):
            return True, 100.0

        token_score = fuzz.token_sort_ratio(guess_norm, target_norm)
        # partial_ratio scores any substring 100, so it's only trustworthy for
        # multi-character overlaps ("new york" in "new york city"). Gate it on a
        # minimum shared length, or a single CJK character would fully match a
        # 2-char word (e.g. "大" scoring 100 against "大象").
        shortest = min(len(guess_norm), len(target_norm))
        partial_score = fuzz.partial_ratio(guess_norm, target_norm) if shortest >= 4 else 0
        similarity = max(token_score, partial_score)
        return similarity >= self.FUZZY_MATCH_THRESHOLD, similarity

    def match_guess(
        self, guess: str, target: str, aliases: list[str] | None = None, locale: str | None = None
    ) -> float | None:
        """Return the similarity when the guess matches the target or one of its aliases, else None.

        Aliases count only on an exact match; the target also counts on a fuzzy one.
        """
        if not normalize_text(guess):
            return None
        if self.exact_match(guess, target, locale) or any(
            self.exact_match(guess, alias, locale) for alias in aliases or []
        ):
            return 100.0
        is_match, similarity = self.fuzzy_match(guess, target, locale)
        return similarity if is_match else None

    def score_guesses_against_targets(
        self, guesses: list[str], targets: list[GuessTarget], locale: str | None = None
    ) -> list[str]:
        """Return the guesses that matched a target; each target counts once, so the score is the length."""
        matched_item_ids: set[int] = set()
        matched_guesses: list[str] = []

        for guess in guesses:
            best_target: GuessTarget | None = None
            best_similarity = 0.0

            for target in targets:
                if target.item_id in matched_item_ids:
                    continue
                similarity = self.match_guess(guess, target.label, target.aliases, locale)
                if similarity is not None and (best_target is None or similarity > best_similarity):
                    best_target = target
                    best_similarity = similarity

            if best_target is not None:
                matched_item_ids.add(best_target.item_id)
                matched_guesses.append(guess)

        return matched_guesses


guess_matcher = GuessMatcher()
