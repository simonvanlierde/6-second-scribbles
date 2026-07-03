"""Tests for fuzzy matching and scoring functionality."""
# spell-checker: ignore elefant, girafe

import pytest

from app.scoring import GuessMatcher, _generate_variants, normalize_text

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
THRESHOLD = 85
COLOR = "color"
COLOUR = "colour"
CAT_MATCH = "cat"
GIRAFFE_MATCH = "giraffe"


class TestGuessMatcher:
    """Test suite for GuessMatcher class."""

    @pytest.fixture
    def matcher(self) -> GuessMatcher:
        """Create a GuessMatcher instance."""
        return GuessMatcher()

    def test_generate_variants(self) -> None:
        """Test variant generation."""
        variants = _generate_variants(normalize_text(CAT))
        assert CAT in variants
        assert CATS in variants
        assert CATES in variants

        dog_variants = _generate_variants(normalize_text(DOGS))
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
