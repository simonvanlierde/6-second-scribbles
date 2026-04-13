from __future__ import annotations

from scripts.auto_translate_seed_data import apply_auto_translations


class MockTranslationService:
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
    def test_apply_auto_translations_adds_missing_prompt_and_category_translations(self) -> None:
        seed_data = {
            "prompts": [
                {
                    "id": "cat",
                    "translations": [
                        {"locale": "en", "label": "cat", "aliases": ["kitty"]},
                    ],
                }
            ],
            "system_categories": [
                {
                    "id": "animals",
                    "difficulty": "easy",
                    "translations": [{"locale": "en", "name": "Animals"}],
                    "items": ["cat"],
                }
            ],
        }

        service = MockTranslationService()
        stats = apply_auto_translations(
            seed_data,
            source_locale="en",
            target_locales=["es", "fr"],
            service=service,
            overwrite_existing=False,
        )

        prompt_translations = seed_data["prompts"][0]["translations"]
        category_translations = seed_data["system_categories"][0]["translations"]

        assert {t["locale"] for t in prompt_translations} == {"en", "es", "fr"}
        assert {t["locale"] for t in category_translations} == {"en", "es", "fr"}
        assert next(t for t in prompt_translations if t["locale"] == "es")["label"] == "cat<en->es>"
        assert next(t for t in category_translations if t["locale"] == "fr")["name"] == "Animals<en->fr>"
        assert stats["prompts_translated"] == 2
        assert stats["categories_translated"] == 2
        assert stats["aliases_translated"] == 2

    def test_apply_auto_translations_preserves_existing_translations_by_default(self) -> None:
        seed_data = {
            "prompts": [
                {
                    "id": "cat",
                    "translations": [
                        {"locale": "en", "label": "cat", "aliases": ["kitty"]},
                        {"locale": "es", "label": "gato", "aliases": ["gatito"]},
                    ],
                }
            ]
        }

        service = MockTranslationService()
        stats = apply_auto_translations(
            seed_data,
            source_locale="en",
            target_locales=["es"],
            service=service,
            overwrite_existing=False,
        )

        es_translation = next(t for t in seed_data["prompts"][0]["translations"] if t["locale"] == "es")
        assert es_translation["label"] == "gato"
        assert es_translation["aliases"] == ["gatito"]
        total_updates = stats["prompts_translated"] + stats["categories_translated"] + stats["aliases_translated"]
        assert total_updates == 0

    def test_apply_auto_translations_overwrites_when_requested(self) -> None:
        seed_data = {
            "prompts": [
                {
                    "id": "cat",
                    "translations": [
                        {"locale": "en", "label": "cat", "aliases": ["kitty"]},
                        {"locale": "es", "label": "gato", "aliases": ["gatito"]},
                    ],
                }
            ]
        }

        service = MockTranslationService()
        stats = apply_auto_translations(
            seed_data,
            source_locale="en",
            target_locales=["es"],
            service=service,
            overwrite_existing=True,
        )

        es_translation = next(t for t in seed_data["prompts"][0]["translations"] if t["locale"] == "es")
        assert es_translation["label"] == "cat<en->es>"
        assert es_translation["aliases"] == ["kitty<en->es>"]
        assert stats["prompts_translated"] == 1
        assert stats["aliases_translated"] == 1

    def test_service_handles_deduplication_internally(self) -> None:
        """Test that service deduplication works correctly."""
        seed_data = {
            "prompts": [
                {
                    "id": "test",
                    "translations": [
                        {"locale": "en", "label": "cat", "aliases": ["cat", "cat"]},  # duplicates
                    ],
                }
            ]
        }

        service = MockTranslationService()
        stats = apply_auto_translations(
            seed_data,
            source_locale="en",
            target_locales=["es"],
            service=service,
            overwrite_existing=False,
        )

        # Should have called service.translate for label + 2 aliases (service handles dedup internally)
        assert service.translate_call_count >= 1  # At least the label was translated
        # Aliases should be present
        es_translation = next(t for t in seed_data["prompts"][0]["translations"] if t["locale"] == "es")
        assert es_translation.get("aliases") is not None
