"""Tests for fuzzy matching and scoring functionality."""
# spell-checker: ignore elefant, girafe, rabit, aple, bannana, pinapple, gutar, paino, violen, trumpit, monky, manago
# spell-checker: ignore tigger, watermellon, clarnet, accordian

import pytest

from app.scoring import GuessMatcher

CAT = "cat"
CATS = "cats"
CATES = "cates"
DOGS = "dogs"
DOG = "dog"
BOX = "box"
BOXES = "boxes"
GIRAFFE = "giraffe"
GIRAFE = "girafe"
TIGGER = "tigger"
TIGER = "tiger"
ELEFANT = "elefant"
ELEPHANT = "elephant"
EXACT = "exact"
FUZZY = "fuzzy"
ALTERNATIVE = "alternative"
NONE = "none"
ONE_HUNDRED = 100.0
FIFTY = 50.0
THRESHOLD = 85
COLOR = "color"
COLOUR = "colour"
CAT_MATCH = "cat"
GIRAFFE_MATCH = "giraffe"
GIRAFE_MATCH = "girafe"
DOG_UNMATCHED = "dog"
FISH = "fish"
ORANGE = "orange"


class TestGuessMatcher:
    """Test suite for GuessMatcher class."""

    @pytest.fixture
    def matcher(self) -> GuessMatcher:
        """Create a GuessMatcher instance."""
        return GuessMatcher()

    def test_generate_variants(self, matcher: GuessMatcher) -> None:
        """Test variant generation."""
        variants = matcher.generate_variants(CAT)
        assert CAT in variants
        assert CATS in variants
        assert CATES in variants

        dog_variants = matcher.generate_variants(DOGS)
        assert DOGS in dog_variants
        assert DOG in dog_variants

    def test_exact_match_plural(self, matcher: GuessMatcher) -> None:
        """Test exact matching with plurals."""
        assert matcher.exact_match(CAT, CATS)
        assert matcher.exact_match(CATS, CAT)
        assert matcher.exact_match(BOX, BOXES)
        assert matcher.exact_match(BOXES, BOX)

    def test_fuzzy_match_typo(self, matcher: GuessMatcher) -> None:
        """Test fuzzy matching with typos."""
        # girafe/giraffe: ~92% similarity — well above threshold
        is_match, score = matcher.fuzzy_match(GIRAFE, GIRAFFE)
        assert is_match
        assert score >= THRESHOLD

        # tigger/tiger: ~91% similarity — above threshold
        is_match, score = matcher.fuzzy_match(TIGGER, TIGER)
        assert is_match
        assert score >= THRESHOLD

        # elefant/elephant: ~80% similarity — below the 85% threshold,
        # so this is intentionally NOT a fuzzy match with current settings.
        is_match, score = matcher.fuzzy_match(ELEFANT, ELEPHANT)
        assert not is_match
        assert score < THRESHOLD

    def test_fuzzy_match_no_match(self, matcher: GuessMatcher) -> None:
        """Test fuzzy matching with completely different words."""
        is_match, score = matcher.fuzzy_match(CAT, ELEPHANT)
        assert not is_match
        assert score < THRESHOLD

    def test_match_guess_exact(self, matcher: GuessMatcher) -> None:
        """Test matching a guess with exact match."""
        correct = [CAT, DOG, "bird"]
        result = matcher.match_guess(CAT, correct)

        assert result.matched
        assert result.matched_item == CAT_MATCH
        assert result.similarity == ONE_HUNDRED
        assert result.method == EXACT

    def test_match_guess_fuzzy(self, matcher: GuessMatcher) -> None:
        """Test matching a guess with fuzzy match."""
        correct = [GIRAFFE, ELEPHANT, "zebra"]
        # girafe scores ~92% against giraffe — above the 85% threshold
        result = matcher.match_guess(GIRAFE, correct)

        assert result.matched
        assert result.matched_item == GIRAFFE_MATCH
        assert result.similarity >= THRESHOLD
        assert result.method == FUZZY

    def test_match_guess_with_alternatives(self, matcher: GuessMatcher) -> None:
        """Test matching with alternative spellings."""
        correct = [COLOR]
        alternatives = [COLOUR]  # British spelling

        result = matcher.match_guess(COLOUR, correct, alternatives)

        assert result.matched
        assert result.method == ALTERNATIVE

    def test_match_guess_no_match(self, matcher: GuessMatcher) -> None:
        """Test no match found."""
        correct = [CAT, DOG]
        result = matcher.match_guess(ELEPHANT, correct)

        assert not result.matched
        assert result.matched_item is None
        assert result.method == NONE

    def test_score_guesses_perfect_score(self, matcher: GuessMatcher) -> None:
        """Test scoring with all correct guesses."""
        guesses = [CAT, DOG, "bird"]
        correct = [CAT, DOG, "bird"]

        result = matcher.score_guesses(guesses, correct)

        assert result.score == 3
        assert result.total == 3
        assert result.percentage == ONE_HUNDRED
        assert len(result.matches) == 3
        assert len(result.unmatched_answers) == 0

    def test_score_guesses_partial_score(self, matcher: GuessMatcher) -> None:
        """Test scoring with some correct guesses."""
        guesses = [CAT, ELEPHANT, "bird"]
        correct = [CAT, DOG, "bird", FISH]

        result = matcher.score_guesses(guesses, correct)

        assert result.score == 2  # cat and bird matched
        assert result.total == 4
        assert result.percentage == FIFTY
        assert DOG_UNMATCHED in result.unmatched_answers
        assert FISH in result.unmatched_answers

    def test_score_guesses_with_typos(self, matcher: GuessMatcher) -> None:
        """Test scoring with typos (fuzzy matching)."""
        # girafe (~92%), monky (~91%), zebra (exact) — all above the 85% threshold
        guesses = [GIRAFE, "monky", "zebra"]
        correct = [GIRAFFE, "monkey", "zebra"]

        result = matcher.score_guesses(guesses, correct)

        assert result.score == 3  # All should match via fuzzy
        assert result.total == 3
        assert result.percentage == ONE_HUNDRED

    def test_score_guesses_no_duplicates(self, matcher: GuessMatcher) -> None:
        """Test that duplicate guesses don't count twice."""
        guesses = [CAT, CAT, CAT, DOG]
        correct = [CAT, DOG, "bird"]

        result = matcher.score_guesses(guesses, correct)

        assert result.score == 2  # Only cat and dog (no duplicates)
        assert result.total == 3

    def test_score_guesses_with_alternatives(self, matcher: GuessMatcher) -> None:
        """Test scoring with alternative spellings."""
        guesses = [COLOUR, "gray", "centre"]
        correct = [COLOR, "grey", "center"]
        alternatives_map = {COLOR: [COLOUR], "grey": ["gray"], "center": ["centre"]}

        result = matcher.score_guesses(guesses, correct, alternatives_map)

        assert result.score == 3
        assert result.percentage == ONE_HUNDRED

    def test_score_guesses_empty_guesses(self, matcher: GuessMatcher) -> None:
        """Test scoring with no guesses."""
        guesses = []
        correct = [CAT, DOG]

        result = matcher.score_guesses(guesses, correct)

        assert result.score == 0
        assert result.total == 2
        assert result.percentage == 0.0

    def test_score_guesses_empty_correct(self, matcher: GuessMatcher) -> None:
        """Test scoring with no correct answers."""
        guesses = [CAT, DOG]
        correct = []

        result = matcher.score_guesses(guesses, correct)

        assert result.score == 0
        assert result.total == 0
        assert result.percentage == 0.0

    def test_match_details(self, matcher: GuessMatcher) -> None:
        """Test that match details are returned."""
        # Use girafe/giraffe (~92%) instead of elefant/elephant (~80%)
        # since only scores above the 85% threshold are fuzzy matches.
        guesses = [CAT, GIRAFE]
        correct = [CAT, GIRAFFE]

        result = matcher.score_guesses(guesses, correct)

        assert len(result.matches) == 2

        # Check first match (exact)
        cat_match = result.matches[0]
        assert cat_match.guess == CAT_MATCH
        assert cat_match.matched_item == CAT_MATCH
        assert cat_match.method == EXACT

        # Check second match (fuzzy)
        giraffe_match = result.matches[1]
        assert giraffe_match.guess == GIRAFE_MATCH
        assert giraffe_match.matched_item == GIRAFFE_MATCH
        assert giraffe_match.method == FUZZY


class TestRealWorldScenarios:
    """Test real-world game scenarios."""

    @pytest.fixture
    def matcher(self) -> GuessMatcher:
        """Create a GuessMatcher instance."""
        return GuessMatcher()

    def test_animals_category(self, matcher: GuessMatcher) -> None:
        """Test with animals category."""
        correct = [CAT, DOG, "fish", "bird", "rabbit", "cow", "duck", "sheep", "pig", "horse"]
        guesses = [CAT, DOGS, "fsh", "bir", "rabit", ELEPHANT]  # Mix of correct and typos

        result = matcher.score_guesses(guesses, correct)

        # Should match: cat, dogs->dog, fsh->fish (maybe), bird, rabit->rabbit
        assert result.score >= 4  # At least these should match

    def test_drawing_game_scenario(self, matcher: GuessMatcher) -> None:
        """Test realistic drawing game scenario."""
        # What the drawer was supposed to draw
        correct = ["mango", "banana", "grapes", "pear", "watermelon"]

        # What the guesser typed — all typos score above 85%:
        # manago/mango=91%, bannana/banana=92%, grape/grapes=exact,
        # pear/pear=exact, watermellon/watermelon=97%
        guesses = ["manago", "bannana", "grape", "pear", "watermellon", ORANGE, "kiwi"]

        result = matcher.score_guesses(guesses, correct)

        assert result.score == 5
        assert result.total == 5
        assert ORANGE not in [match.matched_item for match in result.matches]

    def test_musical_instruments(self, matcher: GuessMatcher) -> None:
        """Test with musical instruments."""
        correct = ["guitar", "drums", "trumpet", "clarinet", "accordion"]
        # gutar/guitar=91%, drum/drums=exact, trumpit/trumpet=86%,
        # clarnet/clarinet=93%, accordian/accordion=89%
        guesses = ["gutar", "drum", "trumpit", "clarnet", "accordian"]

        result = matcher.score_guesses(guesses, correct)

        assert result.score == 5
