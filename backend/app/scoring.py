"""Fuzzy matching and scoring logic for guess validation.

Uses rapidfuzz for high-performance fuzzy string matching
"""

from rapidfuzz import fuzz


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
    PARTIAL_MATCH_THRESHOLD = 90  # For partial ratio matching

    def __init__(self):
        """Initialize the guess matcher."""
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
        if word in self.cache:
            return self.cache[word]

        variants = {self.normalize(word)}
        normalized = self.normalize(word)

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

        self.cache[word] = variants
        return variants

    def exact_match(self, guess: str, target: str) -> bool:
        """Check if guess exactly matches target (case-insensitive, with variants)."""
        guess_variants = self.generate_variants(guess)
        target_variants = self.generate_variants(target)

        return bool(guess_variants & target_variants)

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

        # Use the highest score
        similarity = max(token_score, partial_score)

        # Check if it meets threshold
        is_match = similarity >= self.FUZZY_MATCH_THRESHOLD

        return is_match, similarity

    def match_guess(self, guess: str, correct_answers: list[str], alternatives: list[str] | None = None) -> dict:
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
        guess_norm = self.normalize(guess)

        if not guess_norm:
            return {"matched": False, "matched_item": None, "similarity": 0.0, "method": "none"}

        # Check exact matches first
        for answer in correct_answers:
            if self.exact_match(guess, answer):
                return {"matched": True, "matched_item": answer, "similarity": 100.0, "method": "exact"}

        # Check alternatives if provided
        if alternatives:
            for alt in alternatives:
                if self.exact_match(guess, alt):
                    return {"matched": True, "matched_item": alt, "similarity": 100.0, "method": "alternative"}

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
            return {"matched": True, "matched_item": best_item, "similarity": best_score, "method": "fuzzy"}

        return {"matched": False, "matched_item": None, "similarity": best_score, "method": "none"}

    def score_guesses(
        self, guesses: list[str], correct_answers: list[str], alternatives_map: dict[str, list[str]] | None = None
    ) -> dict:
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
        alternatives_map = alternatives_map or {}
        matched_answers = set()
        match_details = []

        for guess in guesses:
            alternatives = []
            for answer in correct_answers:
                if answer in alternatives_map:
                    alternatives.extend(alternatives_map[answer])

            result = self.match_guess(guess, correct_answers, alternatives)

            if result["matched"] and result["matched_item"] not in matched_answers:
                matched_answers.add(result["matched_item"])
                match_details.append(
                    {
                        "guess": guess,
                        "matched_item": result["matched_item"],
                        "similarity": result["similarity"],
                        "method": result["method"],
                    }
                )

        unmatched = [ans for ans in correct_answers if ans not in matched_answers]

        return {
            "score": len(matched_answers),
            "total": len(correct_answers),
            "percentage": (len(matched_answers) / len(correct_answers) * 100) if correct_answers else 0,
            "matches": match_details,
            "unmatched_answers": unmatched,
        }


# Global instance
guess_matcher = GuessMatcher()
