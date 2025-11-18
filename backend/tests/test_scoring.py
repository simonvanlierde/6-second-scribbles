"""
Tests for fuzzy matching and scoring functionality
"""
import pytest
from scoring import GuessMatcher


class TestGuessMatcher:
    """Test suite for GuessMatcher class"""

    @pytest.fixture
    def matcher(self):
        """Create a GuessMatcher instance"""
        return GuessMatcher()

    def test_normalize(self, matcher):
        """Test text normalization"""
        assert matcher.normalize("Hello World") == "hello world"
        assert matcher.normalize("  spaces  ") == "spaces"
        assert matcher.normalize("UPPERCASE") == "uppercase"

    def test_generate_variants(self, matcher):
        """Test variant generation"""
        variants = matcher.generate_variants("cat")
        assert "cat" in variants
        assert "cats" in variants
        assert "cates" in variants

        dog_variants = matcher.generate_variants("dogs")
        assert "dogs" in variants
        assert "dog" in dog_variants

    def test_exact_match_simple(, matcher):
        """Test exact matching"""
        assert matcher.exact_match("cat", "cat") is True
        assert matcher.exact_match("Cat", "cat") is True  # Case insensitive
        assert matcher.exact_match("cat", "dog") is False

    def test_exact_match_plural(self, matcher):
        """Test exact matching with plurals"""
        assert matcher.exact_match("cat", "cats") is True
        assert matcher.exact_match("cats", "cat") is True
        assert matcher.exact_match("box", "boxes") is True
        assert matcher.exact_match("boxes", "box") is True

    def test_fuzzy_match_typo(self, matcher):
        """Test fuzzy matching with typos"""
        is_match, score = matcher.fuzzy_match("elefant", "elephant")
        assert is_match is True
        assert score > 85

        is_match, score = matcher.fuzzy_match("girafe", "giraffe")
        assert is_match is True
        assert score > 85

    def test_fuzzy_match_no_match(self, matcher):
        """Test fuzzy matching with completely different words"""
        is_match, score = matcher.fuzzy_match("cat", "elephant")
        assert is_match is False
        assert score < 85

    def test_match_guess_exact(self, matcher):
        """Test matching a guess with exact match"""
        correct = ["cat", "dog", "bird"]
        result = matcher.match_guess("cat", correct)

        assert result["matched"] is True
        assert result["matched_item"] == "cat"
        assert result["similarity"] == 100.0
        assert result["method"] == "exact"

    def test_match_guess_fuzzy(self, matcher):
        """Test matching a guess with fuzzy match"""
        correct = ["elephant", "giraffe", "zebra"]
        result = matcher.match_guess("elefant", correct)

        assert result["matched"] is True
        assert result["matched_item"] == "elephant"
        assert result["similarity"] >= 85
        assert result["method"] == "fuzzy"

    def test_match_guess_with_alternatives(self, matcher):
        """Test matching with alternative spellings"""
        correct = ["color"]
        alternatives = ["colour"]  # British spelling

        result = matcher.match_guess("colour", correct, alternatives)

        assert result["matched"] is True
        assert result["method"] == "alternative"

    def test_match_guess_no_match(self, matcher):
        """Test no match found"""
        correct = ["cat", "dog"]
        result = matcher.match_guess("elephant", correct)

        assert result["matched"] is False
        assert result["matched_item"] is None
        assert result["method"] == "none"

    def test_score_guesses_perfect_score(self, matcher):
        """Test scoring with all correct guesses"""
        guesses = ["cat", "dog", "bird"]
        correct = ["cat", "dog", "bird"]

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 3
        assert result["total"] == 3
        assert result["percentage"] == 100.0
        assert len(result["matches"]) == 3
        assert len(result["unmatched_answers"]) == 0

    def test_score_guesses_partial_score(self, matcher):
        """Test scoring with some correct guesses"""
        guesses = ["cat", "elephant", "bird"]
        correct = ["cat", "dog", "bird", "fish"]

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 2  # cat and bird matched
        assert result["total"] == 4
        assert result["percentage"] == 50.0
        assert "dog" in result["unmatched_answers"]
        assert "fish" in result["unmatched_answers"]

    def test_score_guesses_with_typos(self, matcher):
        """Test scoring with typos (fuzzy matching)"""
        guesses = ["elefant", "girafe", "zebra"]
        correct = ["elephant", "giraffe", "zebra"]

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 3  # All should match via fuzzy
        assert result["total"] == 3
        assert result["percentage"] == 100.0

    def test_score_guesses_no_duplicates(self, matcher):
        """Test that duplicate guesses don't count twice"""
        guesses = ["cat", "cat", "cat", "dog"]
        correct = ["cat", "dog", "bird"]

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 2  # Only cat and dog (no duplicates)
        assert result["total"] == 3

    def test_score_guesses_with_alternatives(self, matcher):
        """Test scoring with alternative spellings"""
        guesses = ["colour", "gray", "centre"]
        correct = ["color", "grey", "center"]
        alternatives_map = {
            "color": ["colour"],
            "grey": ["gray"],
            "center": ["centre"]
        }

        result = matcher.score_guesses(guesses, correct, alternatives_map)

        assert result["score"] == 3
        assert result["percentage"] == 100.0

    def test_score_guesses_empty_guesses(self, matcher):
        """Test scoring with no guesses"""
        guesses = []
        correct = ["cat", "dog"]

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 0
        assert result["total"] == 2
        assert result["percentage"] == 0.0

    def test_score_guesses_empty_correct(self, matcher):
        """Test scoring with no correct answers"""
        guesses = ["cat", "dog"]
        correct = []

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 0
        assert result["total"] == 0
        assert result["percentage"] == 0.0

    def test_case_insensitive_matching(self, matcher):
        """Test that matching is case insensitive"""
        guesses = ["CAT", "Dog", "BIRD"]
        correct = ["cat", "dog", "bird"]

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 3
        assert result["percentage"] == 100.0

    def test_whitespace_handling(self, matcher):
        """Test that extra whitespace is handled"""
        guesses = ["  cat  ", "dog", "  bird"]
        correct = ["cat", "dog", "bird"]

        result = matcher.score_guesses(guesses, correct)

        assert result["score"] == 3

    def test_match_details(self, matcher):
        """Test that match details are returned"""
        guesses = ["cat", "elefant"]
        correct = ["cat", "elephant"]

        result = matcher.score_guesses(guesses, correct)

        assert len(result["matches"]) == 2

        # Check first match (exact)
        cat_match = result["matches"][0]
        assert cat_match["guess"] == "cat"
        assert cat_match["matched_item"] == "cat"
        assert cat_match["method"] == "exact"

        # Check second match (fuzzy)
        elephant_match = result["matches"][1]
        assert elephant_match["guess"] == "elefant"
        assert elephant_match["matched_item"] == "elephant"
        assert elephant_match["method"] == "fuzzy"


class TestRealWorldScenarios:
    """Test real-world game scenarios"""

    @pytest.fixture
    def matcher(self):
        return GuessMatcher()

    def test_animals_category(self, matcher):
        """Test with animals category"""
        correct = ["cat", "dog", "fish", "bird", "rabbit", "cow", "duck", "sheep", "pig", "horse"]
        guesses = ["cat", "dogs", "fsh", "bir", "rabit", "elephant"]  # Mix of correct and typos

        result = matcher.score_guesses(guesses, correct)

        # Should match: cat, dogs->dog, fsh->fish (maybe), bird, rabit->rabbit
        assert result["score"] >= 4  # At least these should match

    def test_drawing_game_scenario(self, matcher):
        """Test realistic drawing game scenario"""
        # What the drawer was supposed to draw
        correct = ["apple", "banana", "grapes", "pear", "pineapple"]

        # What the guesser typed
        guesses = ["aple", "bannana", "grape", "pear", "pinapple", "orange", "watermelon"]

        result = matcher.score_guesses(guesses, correct)

        # Should match all 5 correct ones (with fuzzy matching)
        assert result["score"] == 5
        assert result["total"] == 5
        assert "orange" not in [m["matched_item"] for m in result["matches"]]

    def test_musical_instruments(self, matcher):
        """Test with musical instruments"""
        correct = ["guitar", "piano", "drums", "violin", "trumpet"]
        guesses = ["gutar", "paino", "drum", "violen", "trumpit"]

        result = matcher.score_guesses(guesses, correct)

        # All should match via fuzzy matching or plurals
        assert result["score"] == 5
