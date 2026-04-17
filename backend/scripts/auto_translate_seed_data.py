"""Auto-translate seed YAML entries using the translation service.

This script fills in missing translations for prompts and system categories.
It is designed for occasional batch updates, not runtime translation.

Uses TranslationService for caching, deduplication, and offline Argos translation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
import unicodedata
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from translation import TranslationService

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_SOURCE_LOCALE = "en"
DEFAULT_TARGET_LOCALES = ("es", "fr")
DEFAULT_SEED_PATH = Path(__file__).parent / "seed_data.yaml"
SEED_HASH_FILE = DEFAULT_SEED_PATH.parent / ".seed_translation_hash"
PROMPTS_KEY = "prompts"
SYSTEM_CATEGORIES_KEY = "system_categories"


def configure_logging() -> None:
    """Configure simple CLI logging for translation runs."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, strip, remove accents."""
    lowered = text.lower().strip()
    return unicodedata.normalize("NFD", lowered).encode("ascii", "ignore").decode("ascii")


configure_logging()


def _is_blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _normalize_locales(locales: list[str] | tuple[str, ...] | None) -> list[str]:
    if not locales:
        return list(DEFAULT_TARGET_LOCALES)
    normalized: list[str] = []
    for locale in locales:
        value = locale.strip().lower()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def _translations_by_locale(translations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for translation in translations:
        locale = str(translation.get("locale", "")).strip().lower()
        if locale:
            indexed[locale] = translation
    return indexed


def _ensure_translation_entry(translations: list[dict[str, Any]], locale: str) -> dict[str, Any]:
    indexed = _translations_by_locale(translations)
    existing = indexed.get(locale)
    if existing is not None:
        return existing
    created: dict[str, Any] = {"locale": locale}
    translations.append(created)
    return created


def _count_prompt_strings(prompt: dict[str, Any], *, normalized_source: str, normalized_targets: list[str]) -> int:
    translations = list(prompt.get("translations", []))
    indexed = _translations_by_locale(translations)
    source_translation = indexed.get(normalized_source)
    if source_translation is None or _is_blank(source_translation.get("label")):
        return 0

    source_aliases = [str(alias) for alias in (source_translation.get("aliases") or []) if not _is_blank(alias)]
    return (1 + len(source_aliases)) * len(normalized_targets)


def _count_category_strings(category: dict[str, Any], *, normalized_source: str, normalized_targets: list[str]) -> int:
    translations = list(category.get("translations", []))
    indexed = _translations_by_locale(translations)
    source_translation = indexed.get(normalized_source)
    if source_translation is None or _is_blank(source_translation.get("name")):
        return 0

    source_description = source_translation.get("description")
    return (1 + (1 if not _is_blank(source_description) else 0)) * len(normalized_targets)


def _dedupe_translated_aliases(aliases: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for alias in aliases:
        key = normalize_text(alias)
        if key not in seen:
            seen.add(key)
            deduped.append(alias.strip().lower())
    return deduped


def _translate_prompt(
    prompt: dict[str, Any],
    *,
    normalized_source: str,
    normalized_targets: list[str],
    service: TranslationService,
    overwrite_existing: bool,
    stats: dict[str, int],
) -> None:
    translations = list(prompt.get("translations", []))
    indexed = _translations_by_locale(translations)
    source_translation = indexed.get(normalized_source)
    if source_translation is None or _is_blank(source_translation.get("label")):
        stats["skipped_missing_source"] += 1
        return

    source_label = str(source_translation["label"])
    source_aliases = list(
        dict.fromkeys(str(alias) for alias in (source_translation.get("aliases") or []) if not _is_blank(alias))
    )

    for target_locale in normalized_targets:
        target_translation = _ensure_translation_entry(translations, target_locale)

        has_label = not _is_blank(target_translation.get("label"))
        if overwrite_existing or not has_label:
            target_translation["label"] = service.translate(normalized_source, target_locale, source_label)
            stats["prompts_translated"] += 1

        target_aliases = target_translation.get("aliases")
        has_aliases = isinstance(target_aliases, list) and len(target_aliases) > 0
        if source_aliases and (overwrite_existing or not has_aliases):
            translated = [service.translate(normalized_source, target_locale, alias) for alias in source_aliases]
            target_translation["aliases"] = _dedupe_translated_aliases(translated)
            stats["aliases_translated"] += len(source_aliases)

    prompt["translations"] = translations


def _translate_category(
    category: dict[str, Any],
    *,
    normalized_source: str,
    normalized_targets: list[str],
    service: TranslationService,
    overwrite_existing: bool,
    stats: dict[str, int],
) -> None:
    translations = list(category.get("translations", []))
    indexed = _translations_by_locale(translations)
    source_translation = indexed.get(normalized_source)
    if source_translation is None or _is_blank(source_translation.get("name")):
        stats["skipped_missing_source"] += 1
        return

    source_name = str(source_translation["name"])
    source_description = source_translation.get("description")

    for target_locale in normalized_targets:
        target_translation = _ensure_translation_entry(translations, target_locale)

        has_name = not _is_blank(target_translation.get("name"))
        if overwrite_existing or not has_name:
            target_translation["name"] = service.translate(normalized_source, target_locale, source_name)
            stats["categories_translated"] += 1

        if not _is_blank(source_description):
            has_description = not _is_blank(target_translation.get("description"))
            if overwrite_existing or not has_description:
                target_translation["description"] = service.translate(
                    normalized_source, target_locale, str(source_description)
                )
                stats["categories_translated"] += 1

    category["translations"] = translations


def apply_auto_translations(
    seed_data: dict[str, Any],
    *,
    source_locale: str,
    target_locales: list[str] | tuple[str, ...],
    service: TranslationService,
    overwrite_existing: bool,
) -> dict[str, int]:
    """Populate missing translations for prompts and system categories in-place."""
    start_time = time.time()
    stats = {
        "prompts_translated": 0,
        "categories_translated": 0,
        "aliases_translated": 0,
        "skipped_missing_source": 0,
        "total_operations": 0,
    }
    normalized_source = source_locale.strip().lower()
    normalized_targets = [locale for locale in _normalize_locales(target_locales) if locale != normalized_source]

    # Pre-fetch all language pairs if provided
    logger.info("Pre-fetching all language pairs...")
    service.prefetch_pairs(normalized_source, normalized_targets)
    prompts = list(seed_data.get(PROMPTS_KEY, []))
    categories = list(seed_data.get(SYSTEM_CATEGORIES_KEY, []))
    total_strings_to_estimate = sum(
        _count_prompt_strings(prompt, normalized_source=normalized_source, normalized_targets=normalized_targets)
        for prompt in prompts
    ) + sum(
        _count_category_strings(category, normalized_source=normalized_source, normalized_targets=normalized_targets)
        for category in categories
    )

    logger.info("Starting translation of ~%d strings...", total_strings_to_estimate)

    # Translate prompts
    for prompt in prompts:
        _translate_prompt(
            prompt,
            normalized_source=normalized_source,
            normalized_targets=normalized_targets,
            service=service,
            overwrite_existing=overwrite_existing,
            stats=stats,
        )
        stats["total_operations"] += 1
        if stats["total_operations"] % 100 == 0:
            logger.info("Progress: %d translations completed", stats["total_operations"])

    # Translate categories
    for category in categories:
        _translate_category(
            category,
            normalized_source=normalized_source,
            normalized_targets=normalized_targets,
            service=service,
            overwrite_existing=overwrite_existing,
            stats=stats,
        )
        stats["total_operations"] += 1
        if stats["total_operations"] % 100 == 0:
            logger.info("Progress: %d translations completed", stats["total_operations"])

    elapsed = time.time() - start_time
    logger.info(
        "Translation updates: prompts=%d categories=%d aliases=%d | elapsed=%.1fs",
        stats["prompts_translated"],
        stats["categories_translated"],
        stats["aliases_translated"],
        elapsed,
    )
    logger.info("Service cache stats: %s", service.cache_stats())

    return stats


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the auto-translation script."""
    parser = argparse.ArgumentParser(description="Auto-translate missing entries in seed_data.yaml")
    parser.add_argument("--seed-file", type=Path, default=DEFAULT_SEED_PATH)
    parser.add_argument("--source-locale", default=DEFAULT_SOURCE_LOCALE)
    parser.add_argument(
        "--target-locales",
        nargs="*",
        default=list(DEFAULT_TARGET_LOCALES),
        help="Target locales (space-separated or comma-separated, e.g. 'it nl' or 'it,nl')",
    )
    parser.add_argument("--overwrite-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--benchmark", action="store_true", help="Sample 50 prompts and extrapolate total time")
    parser.add_argument("--force", action="store_true", help="Skip hash check and re-translate even if unchanged")
    parser.add_argument("--reset-cache", action="store_true", help="Clear translation cache before running")
    parser.add_argument("--show-cache-stats", action="store_true", help="Show cache statistics and exit")
    parser.add_argument("--inspect-cache", action="store_true", help="Dump entire cache to JSON and exit (debug only)")
    args = parser.parse_args()

    # Handle comma-separated locales for convenience
    if args.target_locales and len(args.target_locales) == 1 and "," in args.target_locales[0]:  # noqa: PLR2004
        args.target_locales = args.target_locales[0].split(",")

    return args


def _compute_file_hash(path: Path) -> str:
    """Compute SHA256 hash of file contents."""
    sha256_hash = hashlib.sha256()
    sha256_hash.update(path.read_bytes())
    return sha256_hash.hexdigest()


def _read_last_hash() -> str | None:
    """Read last translation hash if it exists."""
    if SEED_HASH_FILE.exists():
        return SEED_HASH_FILE.read_text().strip()
    return None


def _write_hash(file_hash: str) -> None:
    """Write current hash to marker file."""
    SEED_HASH_FILE.write_text(file_hash)


def _handle_cache_commands(args: argparse.Namespace, service: TranslationService) -> bool:
    if args.reset_cache:
        logger.info("Clearing translation cache...")
        service.cache.reset()
        logger.info("Cache cleared.")
        return True

    if args.show_cache_stats:
        logger.info("Cache stats: %s", service.cache_stats())
        return True

    if args.inspect_cache:
        logger.info("Dumping translation cache...")
        logger.info(json.dumps(service.cache.cache, indent=2, ensure_ascii=False))
        return True

    return False


def main() -> None:
    """Main entry point for auto-translation script."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    seed_file: Path = args.seed_file
    if not seed_file.exists():
        msg = f"Seed file not found: {seed_file}"
        raise FileNotFoundError(msg)

    service = TranslationService()
    handled = _handle_cache_commands(args, service)
    if not handled:
        current_hash = _compute_file_hash(seed_file)
        last_hash = _read_last_hash()
        if current_hash == last_hash and not args.force and not args.overwrite_existing:
            logger.info("Seed file unchanged since last translation (hash: %s...). Skipping.", current_hash[:8])
            logger.info("Use --force to re-translate anyway.")
            handled = True

    seed_data: dict[str, Any] | None = None
    if not handled:
        seed_data = yaml.safe_load(seed_file.read_text(encoding="utf-8"))
        if not isinstance(seed_data, dict):
            msg = "Expected seed YAML root to be a mapping."
            raise TypeError(msg)

    if not handled and args.benchmark and seed_data is not None:
        logger.info("Running benchmark on sample of 50 prompts...")
        sample_data: dict[str, Any] = {"prompts": list(seed_data.get(PROMPTS_KEY, []))[:50]}
        start_bench = time.time()
        apply_auto_translations(
            sample_data,
            source_locale=str(args.source_locale),
            target_locales=list(args.target_locales),
            service=service,
            overwrite_existing=bool(args.overwrite_existing),
        )
        elapsed_bench = time.time() - start_bench
        total_prompts = len(list(seed_data.get(PROMPTS_KEY, [])))
        estimated_total = elapsed_bench * (total_prompts / 50)
        logger.info("Benchmark: 50 prompts took %.1f}s", elapsed_bench)
        logger.info(
            "Estimated total time for %d prompts: %.1f}s (%.1fm)",
            total_prompts,
            estimated_total,
            estimated_total / 60,
        )
        handled = True

    if not handled and seed_data is not None:
        stats = apply_auto_translations(
            seed_data,
            source_locale=str(args.source_locale),
            target_locales=list(args.target_locales),
            service=service,
            overwrite_existing=bool(args.overwrite_existing),
        )

        total_updates = stats["prompts_translated"] + stats["categories_translated"] + stats["aliases_translated"]
        if total_updates == 0:
            logger.info("No missing translations found. Nothing to update.")
        elif args.dry_run:
            logger.info("Dry run enabled: seed file was not modified.")
        else:
            seed_file.write_text(yaml.safe_dump(seed_data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            logger.info("Updated seed translations in %s", seed_file)

            current_hash = _compute_file_hash(seed_file)
            _write_hash(current_hash)
            logger.info("Hash marker updated. Next run will skip if unchanged.")


if __name__ == "__main__":
    main()
