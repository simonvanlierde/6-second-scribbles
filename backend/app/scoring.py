"""Fuzzy matching and scoring logic for guess validation.

Uses rapidfuzz for high-performance fuzzy string matching
"""

from __future__ import annotations

from rapidfuzz import fuzz

from app.result_models import GuessMatchDetailResult, GuessMatchResult, ScoreGuessesResult


class GuessMatcher:
    """Handles fuzzy matching of player guesses against correct answers.

    Features:
    - Case-insensitive matching
    - Handles plurals (basic: adds/removes 's', 'es')
    - Fuzzy matching for typos and misspellings
    - Configurable similarity thresholds
    """

    # Similarity thresholds
    EXACT_MATCH_THRESHOLD = 100
    FUZZY_MATCH_THRESHOLD = 85  # 85% similarity required for fuzzy match

    def __init__(self):
        self.cache: dict[str, set[str]] = {}  # Cache for performance

    def normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        return text.lower().strip()

    def generate_variants(self, word: str) -> set[str]:
        """Generate common variants of a word.

        Returns set of variants including:
        - Original word
        - Lowercase version
        - Without trailing 's' (singular form)
        - With trailing 's' (plural form)
        - With trailing 'es' (plural form)
        """
        normalized = self.normalize(word)
        if normalized in self.cache:
            return self.cache[normalized]

        variants = {normalized}

        # Add plural/singular variants
        if normalized.endswith("s"):
            # Try removing 's'
            variants.add(normalized[:-1])
            # Try removing 'es'
            if normalized.endswith("es"):
                variants.add(normalized[:-2])
        else:
            # Add 's' and 'es'
            variants.add(f"{normalized}s")
            variants.add(f"{normalized}es")

        # Add with/without common endings
        if normalized.endswith("ing"):
            variants.add(normalized[:-3])  # Remove 'ing'

        self.cache[normalized] = variants
        return variants

    def exact_match(self, guess: str, target: str) -> bool:
        """Check if guess exactly matches target (case-insensitive, with variants)."""
        return bool(self.generate_variants(guess) & self.generate_variants(target))

    def fuzzy_match(self, guess: str, target: str) -> tuple[bool, float]:
        """Check if guess fuzzy matches target.

        Returns:
            (is_match, similarity_score)
        """
        guess_norm = self.normalize(guess)
        target_norm = self.normalize(target)

        # Try exact match first
        if self.exact_match(guess, target):
            return True, 100.0

        # Use rapidfuzz for fuzzy matching
        # Token sort ratio: handles word order differences
        token_score = fuzz.token_sort_ratio(guess_norm, target_norm)

        # Partial ratio: handles substring matches
        partial_score = fuzz.partial_ratio(guess_norm, target_norm)

        similarity = max(token_score, partial_score)
        return similarity >= self.FUZZY_MATCH_THRESHOLD, similarity

    def match_guess(
        self,
        guess: str,
        correct_answers: list[str],
        alternatives: list[str] | None = None,
    ) -> GuessMatchResult:
        """Match a guess against a list of correct answers.

        Args:
            guess: The player's guess
            correct_answers: List of correct answers
            alternatives: Optional list of alternative acceptable answers

        Returns:
            {
                'matched': bool,
                'matched_item': str or None,
                'similarity': float,
                'method': 'exact' | 'fuzzy' | 'alternative' | 'none'
            }
        """
        if not self.normalize(guess):
            return GuessMatchResult(matched=False, matched_item=None, similarity=0.0, method="none")

        # Check exact matches first
        for answer in correct_answers:
            if self.exact_match(guess, answer):
                return GuessMatchResult(matched=True, matched_item=answer, similarity=100.0, method="exact")

        # Check alternatives if provided
        if alternatives:
            for alt in alternatives:
                if self.exact_match(guess, alt):
                    return GuessMatchResult(matched=True, matched_item=alt, similarity=100.0, method="alternative")

        # Try fuzzy matching
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
        """Score a list of guesses against correct answers.

        Args:
            guesses: List of player guesses
            correct_answers: List of correct answers
            alternatives_map: Dict mapping correct answers to their alternatives

        Returns:
            {
                'score': int,  # Number of correct guesses
                'total': int,  # Total correct answers
                'matches': List[Dict],  # Detailed match results
                'unmatched_answers': List[str]  # Answers not guessed
            }
        """
        # Flatten all alternatives once, rather than rebuilding per guess
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


# Global instance
guess_matcher = GuessMatcher()
