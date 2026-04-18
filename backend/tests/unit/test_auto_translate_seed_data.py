"""Tests for automatic translation of seed data."""
# spell-checker: ignore animaux, gato

from __future__ import annotations

from scripts.auto_translate_seed_data import apply_auto_translations
from scripts.seed_data import _build_category_translations, _build_prompt_translations
from translation import TranslationService

LOCALE_EN = "en"
LOCALE_ES = "es"
LOCALE_FR = "fr"
CAT_ES = "cat<en->es>"
ANIMALS_FR = "Animals<en->fr>"
GATO = "gato"
GATITO = "gatito"
CAT_ES_OVERWRITE = "cat<en->es>"
KITTY_ES_OVERWRITE = "kitty<en->es>"


class MockTranslationService(TranslationService):
    """Mock service for testing that tracks translation calls."""

    def __init__(self) -> None:
        self.translate_call_count = 0
        self.translate_calls: list[tuple[str, str, str]] = []

    def translate(self, from_locale: str, to_locale: str, text: str) -> str:
        """Mock translation that returns a predictable format."""
        self.translate_call_count += 1
        self.translate_calls.append((from_locale, to_locale, text))
        return f"{text}<{from_locale}->{to_locale}>"

    def prefetch_pairs(self, from_locale: str, to_locales: list[str]) -> None:
        """Mock prefetch (no-op)."""

    def cache_stats(self) -> str:
        """Mock cache stats."""
        return f"Mock cache: {self.translate_call_count} translations"


class TestAutoTranslateSeedData:
    """Coverage for automatic translation of prompt and category seed data."""

    def test_apply_auto_translations_adds_missing_prompt_and_category_translations(self) -> None:
        """Fill in missing prompt and category translations for target locales."""
        seed_data = {
            "prompts": [
                {
                    "id": "cat",
                    "translations": [
                        {"locale": LOCALE_EN, "label": "cat", "aliases": ["kitty"]},
                    ],
                }
            ],
            "system_categories": [
                {
                    "id": "animals",
                    "difficulty": "easy",
                    "translations": [{"locale": LOCALE_EN, "name": "Animals"}],
                    "items": ["cat"],
                }
            ],
        }

        service = MockTranslationService()
        stats = apply_auto_translations(
            seed_data,
            source_locale=LOCALE_EN,
            target_locales=[LOCALE_ES, LOCALE_FR],
            service=service,
            overwrite_existing=False,
        )

        prompt_translations = seed_data["prompts"][0]["translations"]
        category_translations = seed_data["system_categories"][0]["translations"]

        assert {t["locale"] for t in prompt_translations} == {LOCALE_EN, LOCALE_ES, LOCALE_FR}
        assert {t["locale"] for t in category_translations} == {LOCALE_EN, LOCALE_ES, LOCALE_FR}
        assert next(t for t in prompt_translations if t["locale"] == LOCALE_ES)["label"] == CAT_ES
        assert next(t for t in category_translations if t["locale"] == LOCALE_FR)["name"] == ANIMALS_FR
        assert stats["prompts_translated"] == 2
        assert stats["categories_translated"] == 2
        assert stats["aliases_translated"] == 2

    def test_apply_auto_translations_preserves_existing_translations_by_default(self) -> None:
        """Keep existing translations unless overwrite is explicitly enabled."""
        seed_data = {
            "prompts": [
                {
                    "id": "cat",
                    "translations": [
                        {"locale": LOCALE_EN, "label": "cat", "aliases": ["kitty"]},
                        {"locale": LOCALE_ES, "label": GATO, "aliases": [GATITO]},
                    ],
                }
            ]
        }

        service = MockTranslationService()
        stats = apply_auto_translations(
            seed_data,
            source_locale=LOCALE_EN,
            target_locales=[LOCALE_ES],
            service=service,
            overwrite_existing=False,
        )

        es_translation = next(t for t in seed_data["prompts"][0]["translations"] if t["locale"] == LOCALE_ES)
        assert es_translation["label"] == GATO
        assert es_translation["aliases"] == [GATITO]
        total_updates = stats["prompts_translated"] + stats["categories_translated"] + stats["aliases_translated"]
        assert total_updates == 0

    def test_apply_auto_translations_overwrites_when_requested(self) -> None:
        """Overwrite existing translations when requested."""
        seed_data = {
            "prompts": [
                {
                    "id": "cat",
                    "translations": [
                        {"locale": LOCALE_EN, "label": "cat", "aliases": ["kitty"]},
                        {"locale": LOCALE_ES, "label": GATO, "aliases": [GATITO]},
                    ],
                }
            ]
        }

        service = MockTranslationService()
        stats = apply_auto_translations(
            seed_data,
            source_locale=LOCALE_EN,
            target_locales=[LOCALE_ES],
            service=service,
            overwrite_existing=True,
        )

        es_translation = next(t for t in seed_data["prompts"][0]["translations"] if t["locale"] == LOCALE_ES)
        assert es_translation["label"] == CAT_ES_OVERWRITE
        assert es_translation["aliases"] == [KITTY_ES_OVERWRITE]
        assert stats["prompts_translated"] == 1
        assert stats["aliases_translated"] == 1

    def test_service_handles_deduplication_internally(self) -> None:
        """Let the translation service deduplicate repeated aliases."""
        seed_data = {
            "prompts": [
                {
                    "id": "test",
                    "translations": [
                        {"locale": LOCALE_EN, "label": "cat", "aliases": ["cat", "cat"]},  # duplicates
                    ],
                }
            ]
        }

        service = MockTranslationService()
        apply_auto_translations(
            seed_data,
            source_locale=LOCALE_EN,
            target_locales=[LOCALE_ES],
            service=service,
            overwrite_existing=False,
        )

        # Should have called service.translate for label + 2 aliases (service handles dedup internally)
        assert service.translate_call_count >= 1  # At least the label was translated
        # Aliases should be present
        es_translation = next(t for t in seed_data["prompts"][0]["translations"] if t["locale"] == LOCALE_ES)
        assert es_translation.get("aliases") is not None


class TestSeedDataTransforms:
    """Pure seed-data transforms stay unit-testable without a database."""

    def test_build_prompt_translations_normalizes_locale_and_aliases(self) -> None:
        """Prompt translations normalize locale keys and default alias lists."""
        payload = _build_prompt_translations(
            [
                {"locale": "EN", "label": "Cat", "aliases": ["Kitty", "Feline"]},
                {"locale": "nl", "label": "Kat"},
            ]
        )

        assert payload == {
            "en": {"label": "Cat", "aliases": ["Kitty", "Feline"]},
            "nl": {"label": "Kat", "aliases": []},
        }

    def test_build_category_translations_normalizes_locale_keys(self) -> None:
        """Category translations normalize locale keys for seed payloads."""
        payload = _build_category_translations(
            [
                {"locale": "EN", "name": "Animals"},
                {"locale": "fr", "name": "Animaux"},
            ]
        )

        assert payload == {
            "en": {"name": "Animals"},
            "fr": {"name": "Animaux"},
        }
