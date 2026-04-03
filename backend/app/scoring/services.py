"""Fuzzy matching and scoring logic for guess validation.

Uses rapidfuzz for high-performance fuzzy string matching.
"""

from __future__ import annotations

from rapidfuzz import fuzz

from app.scoring.models import GuessMatchDetailResult, GuessMatchResult, ScoreGuessesResult


class GuessMatcher:
    """Handles fuzzy matching of player guesses against correct answers."""

    EXACT_MATCH_THRESHOLD = 100
    FUZZY_MATCH_THRESHOLD = 85

    def __init__(self) -> None:
        self.cache: dict[str, set[str]] = {}

    def normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        return text.lower().strip()

    def generate_variants(self, word: str) -> set[str]:
        """Generate common variants of a word."""
        normalized = self.normalize(word)
        if normalized in self.cache:
            return self.cache[normalized]

        variants = {normalized}

        if normalized.endswith("s"):
            variants.add(normalized[:-1])
            if normalized.endswith("es"):
                variants.add(normalized[:-2])
        else:
            variants.add(f"{normalized}s")
            variants.add(f"{normalized}es")

        if normalized.endswith("ing"):
            variants.add(normalized[:-3])

        self.cache[normalized] = variants
        return variants

    def exact_match(self, guess: str, target: str) -> bool:
        """Check if guess exactly matches target."""
        return bool(self.generate_variants(guess) & self.generate_variants(target))

    def fuzzy_match(self, guess: str, target: str) -> tuple[bool, float]:
        """Check if guess fuzzy matches target."""
        guess_norm = self.normalize(guess)
        target_norm = self.normalize(target)

        if self.exact_match(guess, target):
            return True, 100.0

        token_score = fuzz.token_sort_ratio(guess_norm, target_norm)
        partial_score = fuzz.partial_ratio(guess_norm, target_norm)
        similarity = max(token_score, partial_score)
        return similarity >= self.FUZZY_MATCH_THRESHOLD, similarity

    def match_guess(
        self,
        guess: str,
        correct_answers: list[str],
        alternatives: list[str] | None = None,
    ) -> GuessMatchResult:
        """Match a guess against a list of correct answers."""
        if not self.normalize(guess):
            return GuessMatchResult(matched=False, matched_item=None, similarity=0.0, method="none")

        for answer in correct_answers:
            if self.exact_match(guess, answer):
                return GuessMatchResult(matched=True, matched_item=answer, similarity=100.0, method="exact")

        if alternatives:
            for alt in alternatives:
                if self.exact_match(guess, alt):
                    return GuessMatchResult(matched=True, matched_item=alt, similarity=100.0, method="alternative")

        best_match = None
        best_score = 0.0
        best_item = None

        for answer in correct_answers:
            is_match, score = self.fuzzy_match(guess, answer)
            if score > best_score:
                best_score = score
                best_match = is_match
                best_item = answer

        if best_match:
            return GuessMatchResult(matched=True, matched_item=best_item, similarity=best_score, method="fuzzy")

        return GuessMatchResult(matched=False, matched_item=None, similarity=best_score, method="none")

    def score_guesses(
        self,
        guesses: list[str],
        correct_answers: list[str],
        alternatives_map: dict[str, list[str]] | None = None,
    ) -> ScoreGuessesResult:
        """Score a list of guesses against correct answers."""
        all_alternatives = [alt for alts in (alternatives_map or {}).values() for alt in alts]

        matched_answers: set[str] = set()
        match_details: list[GuessMatchDetailResult] = []

        for guess in guesses:
            result = self.match_guess(guess, correct_answers, all_alternatives)

            if result.matched and result.matched_item is not None and result.matched_item not in matched_answers:
                matched_answers.add(result.matched_item)
                match_details.append(
                    GuessMatchDetailResult(
                        guess=guess,
                        matched_item=result.matched_item,
                        similarity=result.similarity,
                        method=result.method,
                    ),
                )

        unmatched = [ans for ans in correct_answers if ans not in matched_answers]

        return ScoreGuessesResult(
            score=len(matched_answers),
            total=len(correct_answers),
            percentage=(len(matched_answers) / len(correct_answers) * 100) if correct_answers else 0,
            matches=match_details,
            unmatched_answers=unmatched,
        )


guess_matcher = GuessMatcher()
