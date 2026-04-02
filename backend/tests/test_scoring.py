"""Tests for fuzzy matching and scoring functionality."""

# spell-checker: ignore elefant, girafe, rabit, aple, bannana, pinapple, gutar, paino, violen, trumpit
import pytest

from app.scoring import GuessMatcher


class TestGuessMatcher:
    """Test suite for GuessMatcher class."""

    @pytest.fixture
    def matcher(self) -> GuessMatcher:
        """Create a GuessMatcher instance."""
        return GuessMatcher()

    def test_generate_variants(self, matcher: GuessMatcher) -> None:
        """Test variant generation."""
        variants = matcher.generate_variants("cat")
        assert "cat" in variants
        assert "cats" in variants
        assert "cates" in variants

        dog_variants = matcher.generate_variants("dogs")
        assert "dogs" in dog_variants
        assert "dog" in dog_variants

    def test_exact_match_plural(self, matcher: GuessMatcher) -> None:
        """Test exact matching with plurals."""
        assert matcher.exact_match("cat", "cats") is True
        assert matcher.exact_match("cats", "cat") is True
        assert matcher.exact_match("box", "boxes") is True
        assert matcher.exact_match("boxes", "box") is True

    def test_fuzzy_match_typo(self, matcher: GuessMatcher) -> None:
        """Test fuzzy matching with typos."""
        # girafe/giraffe: ~92% similarity — well above threshold
        is_match, score = matcher.fuzzy_match("girafe", "giraffe")
        assert is_match is True
        assert score >= 85

        # tigger/tiger: ~91% similarity — above threshold
        is_match, score = matcher.fuzzy_match("tigger", "tiger")
        assert is_match is True
        assert score >= 85

        # elefant/elephant: ~80% similarity — below the 85% threshold,
        # so this is intentionally NOT a fuzzy match with current settings.
        is_match, score = matcher.fuzzy_match("elefant", "elephant")
        assert is_match is False
        assert score < 85

    def test_fuzzy_match_no_match(self, matcher: GuessMatcher) -> None:
        """Test fuzzy matching with completely different words."""
        is_match, score = matcher.fuzzy_match("cat", "elephant")
        assert is_match is False
        assert score < 85

    def test_match_guess_exact(self, matcher: GuessMatcher) -> None:
        """Test matching a guess with exact match."""
        correct = ["cat", "dog", "bird"]
        result = matcher.match_guess("cat", correct)

        assert result["matched"] is True
        assert result["matched_item"] == "cat"
        assert result["similarity"] == 100.0
        assert result["method"] == "exact"

    def test_match_guess_fuzzy(self, matcher: GuessMatcher) -> None:
        """Test matching a guess with fuzzy match."""
        correct = ["giraffe", "elephant", "zebra"]
        # girafe scores ~92% against giraffe — above the 85% threshold
        result = matcher.match_guess("girafe", correct)

        assert result["matched"] is True
        assert result["matched_item"] == "giraffe"
        assert result["similarity"] >= 85
        assert result["method"] == "fuzzy"

    def test_match_guess_with_alternatives(self, matcher: GuessMatcher) -> None:
        """Test matching with alternative spellings."""
        correct = ["color"]
        alternatives = ["colour"]  # British spelling

        result = matcher.match_guess("colour", correct, alternatives)

        assert result["matched"] is True
        assert result["method"] == "alternative"

    def test_match_guess_no_match(self, matcher: GuessMatcher) -> None:
        """Test no match found."""
        correct = ["cat", "dog"]
        result = matcher.match_guess("elephant", correct)

        assert result["matched"] is False
        assert result["matched_item"] is None
        assert result["method"] == "none"

    def test_score_guesses_perfect_score(self, matcher: GuessMatcher) -> None:
        """Test scoring with all correct guesses."""
        guesses = ["cat", "dog", "bird"]
        correct = ["cat", "dog", "bird"]

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 3
        assert result["total"] == 3
        assert result["percentage"] == 100.0
        assert len(result["matches"]) == 3
        assert len(result["unmatched_answers"]) == 0

    def test_score_guesses_partial_score(self, matcher: GuessMatcher) -> None:
        """Test scoring with some correct guesses."""
        guesses = ["cat", "elephant", "bird"]
        correct = ["cat", "dog", "bird", "fish"]

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 2  # cat and bird matched
        assert result["total"] == 4
        assert result["percentage"] == 50.0
        assert "dog" in result["unmatched_answers"]
        assert "fish" in result["unmatched_answers"]

    def test_score_guesses_with_typos(self, matcher: GuessMatcher) -> None:
        """Test scoring with typos (fuzzy matching)."""
        # girafe (~92%), monky (~91%), zebra (exact) — all above the 85% threshold
        guesses = ["girafe", "monky", "zebra"]
        correct = ["giraffe", "monkey", "zebra"]

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 3  # All should match via fuzzy
        assert result["total"] == 3
        assert result["percentage"] == 100.0

    def test_score_guesses_no_duplicates(self, matcher: GuessMatcher) -> None:
        """Test that duplicate guesses don't count twice."""
        guesses = ["cat", "cat", "cat", "dog"]
        correct = ["cat", "dog", "bird"]

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 2  # Only cat and dog (no duplicates)
        assert result["total"] == 3

    def test_score_guesses_with_alternatives(self, matcher: GuessMatcher) -> None:
        """Test scoring with alternative spellings."""
        guesses = ["colour", "gray", "centre"]
        correct = ["color", "grey", "center"]
        alternatives_map = {"color": ["colour"], "grey": ["gray"], "center": ["centre"]}

        result = matcher.score_guesses(guesses, correct, alternatives_map)

        assert result["score"] == 3
        assert result["percentage"] == 100.0

    def test_score_guesses_empty_guesses(self, matcher: GuessMatcher) -> None:
        """Test scoring with no guesses."""
        guesses = []
        correct = ["cat", "dog"]

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 0
        assert result["total"] == 2
        assert result["percentage"] == 0.0

    def test_score_guesses_empty_correct(self, matcher: GuessMatcher) -> None:
        """Test scoring with no correct answers."""
        guesses = ["cat", "dog"]
        correct = []

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 0
        assert result["total"] == 0
        assert result["percentage"] == 0.0

    def test_match_details(self, matcher: GuessMatcher) -> None:
        """Test that match details are returned."""
        # Use girafe/giraffe (~92%) instead of elefant/elephant (~80%)
        # since only scores above the 85% threshold are fuzzy matches.
        guesses = ["cat", "girafe"]
        correct = ["cat", "giraffe"]

        result = matcher.score_guesses(guesses, correct)

        assert len(result["matches"]) == 2

        # Check first match (exact)
        cat_match = result["matches"][0]
        assert cat_match["guess"] == "cat"
        assert cat_match["matched_item"] == "cat"
        assert cat_match["method"] == "exact"

        # Check second match (fuzzy)
        giraffe_match = result["matches"][1]
        assert giraffe_match["guess"] == "girafe"
        assert giraffe_match["matched_item"] == "giraffe"
        assert giraffe_match["method"] == "fuzzy"


class TestRealWorldScenarios:
    """Test real-world game scenarios."""

    @pytest.fixture
    def matcher(self) -> GuessMatcher:
        """Create a GuessMatcher instance."""
        return GuessMatcher()

    def test_animals_category(self, matcher: GuessMatcher) -> None:
        """Test with animals category."""
        correct = ["cat", "dog", "fish", "bird", "rabbit", "cow", "duck", "sheep", "pig", "horse"]
        guesses = ["cat", "dogs", "fsh", "bir", "rabit", "elephant"]  # Mix of correct and typos

        result = matcher.score_guesses(guesses, correct)

        # Should match: cat, dogs->dog, fsh->fish (maybe), bird, rabit->rabbit
        assert result["score"] >= 4  # At least these should match

    def test_drawing_game_scenario(self, matcher: GuessMatcher) -> None:
        """Test realistic drawing game scenario."""
        # What the drawer was supposed to draw
        correct = ["mango", "banana", "grapes", "pear", "watermelon"]

        # What the guesser typed — all typos score above 85%:
        # manago/mango=91%, bannana/banana=92%, grape/grapes=exact,
        # pear/pear=exact, watermellon/watermelon=97%
        guesses = ["manago", "bannana", "grape", "pear", "watermellon", "orange", "kiwi"]

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 5
        assert result["total"] == 5
        assert "orange" not in [m["matched_item"] for m in result["matches"]]

    def test_musical_instruments(self, matcher: GuessMatcher) -> None:
        """Test with musical instruments."""
        correct = ["guitar", "drums", "trumpet", "clarinet", "accordion"]
        # gutar/guitar=91%, drum/drums=exact, trumpit/trumpet=86%,
        # clarnet/clarinet=93%, accordian/accordion=89%
        guesses = ["gutar", "drum", "trumpit", "clarnet", "accordian"]

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 5
