"""Localization manager for handling translations."""

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger()


class LocalizationManager:
    """Manages translations and localization."""

    def __init__(self, translations_dir: str = "translations"):
        """Initialize the localization manager.
        
        Args:
            translations_dir: Directory containing translation files
        """
        self.translations_dir = Path(__file__).parent / translations_dir
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.default_language = "en"
        self.missing_keys: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._load_translations()

    def _load_translations(self) -> None:
        """Load all translation files."""
        if not self.translations_dir.exists():
            logger.warning("Translations directory not found", dir=self.translations_dir)
            return

        for file_path in self.translations_dir.glob("*.json"):
            language_code = file_path.stem
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.translations[language_code] = json.load(f)
                logger.info("Loaded translations", language=language_code, file=str(file_path))
            except Exception as e:
                logger.error("Failed to load translation file", file=str(file_path), error=str(e))

    def get(self, key: str, language: str = None, **kwargs) -> str:
        """Get translated text for the given key.
        
        Args:
            key: Translation key (supports dot notation for nested keys)
            language: Language code (defaults to default_language)
            **kwargs: Variables to format into the translation
            
        Returns:
            Translated and formatted text
        """
        if language is None:
            language = self.default_language

        # Get the translation from the specified language or fallback to default
        translation_dict = self.translations.get(language, self.translations.get(self.default_language, {}))
        
        # Navigate nested keys using dot notation
        keys = key.split(".")
        value = translation_dict
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                # If key not found, track it and return the key itself as fallback
                self._track_missing_key(key, language)
                logger.warning("Translation key not found", key=key, language=language)
                return key

        # Format the translation with provided variables
        if isinstance(value, str) and kwargs:
            try:
                return value.format(**kwargs)
            except KeyError as e:
                logger.error("Missing variable in translation", key=key, variable=str(e))
                return value
        
        return str(value)

    def get_available_languages(self) -> Dict[str, str]:
        """Get list of available languages.
        
        Returns:
            Dictionary mapping language codes to language names
        """
        languages = {}
        for lang_code in self.translations:
            lang_info = self.translations[lang_code].get("_meta", {})
            languages[lang_code] = lang_info.get("name", lang_code.upper())
        
        return languages

    def is_language_available(self, language: str) -> bool:
        """Check if a language is available.
        
        Args:
            language: Language code to check
            
        Returns:
            True if language is available
        """
        return language in self.translations

    def _track_missing_key(self, key: str, language: str) -> None:
        """Track missing translation keys with frequency and timestamp.
        
        Args:
            key: The missing translation key
            language: The language code that was requested
        """
        with self._lock:
            key_id = f"{key}:{language}"
            current_time = datetime.now().isoformat()
            
            if key_id in self.missing_keys:
                self.missing_keys[key_id]["frequency"] += 1
                self.missing_keys[key_id]["last_accessed"] = current_time
            else:
                self.missing_keys[key_id] = {
                    "key": key,
                    "language": language,
                    "frequency": 1,
                    "first_accessed": current_time,
                    "last_accessed": current_time
                }

    def dump_missing_translations(self, output_file: str = "missing_translations.json") -> None:
        """Export missing translation keys to a JSON file.
        
        Args:
            output_file: Path to the output JSON file
        """
        with self._lock:
            # Create output data structure
            output_data = {
                "generated_at": datetime.now().isoformat(),
                "total_missing_keys": len(self.missing_keys),
                "missing_keys": list(self.missing_keys.values()),
                "summary_by_language": {}
            }
            
            # Generate summary by language
            for key_data in self.missing_keys.values():
                lang = key_data["language"]
                if lang not in output_data["summary_by_language"]:
                    output_data["summary_by_language"][lang] = {
                        "count": 0,
                        "total_frequency": 0
                    }
                output_data["summary_by_language"][lang]["count"] += 1
                output_data["summary_by_language"][lang]["total_frequency"] += key_data["frequency"]
            
            # Write to file with thread-safe access
            try:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                
                logger.info("Missing translations exported", 
                           file=str(output_path), 
                           total_keys=len(self.missing_keys))
                           
            except Exception as e:
                logger.error("Failed to export missing translations", 
                           file=output_file, 
                           error=str(e))
                raise

    def get_missing_keys_summary(self) -> Dict[str, Any]:
        """Get summary of missing translation keys.
        
        Returns:
            Dictionary with summary information about missing keys
        """
        with self._lock:
            return {
                "total_missing_keys": len(self.missing_keys),
                "languages_affected": list(set(data["language"] for data in self.missing_keys.values())),
                "most_frequent_keys": sorted(
                    self.missing_keys.values(),
                    key=lambda x: x["frequency"],
                    reverse=True
                )[:10]
            }