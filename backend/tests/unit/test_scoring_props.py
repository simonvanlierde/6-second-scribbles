"""Property tests for guess normalization, matching and scoring."""

from hypothesis import example, given, settings
from hypothesis import strategies as st

# spell-checker: ignore abcdeiknorstgy
from app.scoring import GuessTarget, _generate_variants, guess_matcher, normalize_text

words = st.text(alphabet=st.characters(categories=["L", "M", "Zs"]), max_size=12)
ascii_words = st.text(alphabet="abcdeiknorstgy ", min_size=1, max_size=10)
fast = settings(max_examples=150, deadline=None)


@fast
@given(st.text())
# A combining mark before a space hid the space from strip() until the mark was dropped.
@example("\u0301 a")
def test_normalize_text_is_idempotent(text: str) -> None:
    """Normalizing twice changes nothing."""
    once = normalize_text(text)
    assert normalize_text(once) == once


@fast
@given(words.map(normalize_text).filter(bool))
def test_every_variant_of_a_word_is_a_word(word: str) -> None:
    """Stripping a suffix never leaves an empty word, which would match any other."""
    assert "" not in _generate_variants(word)


def test_suffix_only_words_do_not_match_each_other() -> None:
    """Short words that are all suffix only match themselves."""
    for guess, target in (("s", "ing"), ("es", "s"), ("ing", "es")):
        assert not guess_matcher.match_guess(guess, [target]).matched, (guess, target)


# ASCII only: upper() is not reversible for every letter (the Turkish dotless i, U+0131, becomes "I", which
# casefolds to "i"), and that is a different word, not a different case.
@fast
@given(ascii_words, ascii_words)
def test_case_and_outer_spaces_never_change_a_match(guess: str, target: str) -> None:
    """Upper or title case and outer whitespace give the same result."""
    expected = guess_matcher.match_guess(guess, [target]).matched
    for variant in (guess.upper(), guess.title(), f"  {guess}\t"):
        assert guess_matcher.match_guess(variant, [target]).matched == expected


@fast
@given(st.lists(words, max_size=6), st.lists(words, max_size=5))
def test_no_target_is_matched_twice(guesses: list[str], labels: list[str]) -> None:
    """Each target scores at most once, so the score is at most min(guesses, targets)."""
    targets = [GuessTarget(item_id=i, label=label, aliases=[]) for i, label in enumerate(labels)]
    result = guess_matcher.score_guesses_against_targets(guesses, targets)

    matched = [m.matched_item for m in result.matches]
    assert len(result.matches) == result.score
    assert result.score <= min(len(guesses), len(targets))
    assert len(result.unmatched_answers) == len(targets) - result.score
    # Labels may repeat, so count rather than compare sets.
    for label in set(matched):
        assert matched.count(label) <= labels.count(label)
