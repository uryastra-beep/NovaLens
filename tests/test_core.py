from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config_manager
from backend import _extraer_texto_rest
from config_manager import cargar_api_key, validar_configuracion


class ConfigValidationTests(unittest.TestCase):
    def test_corrupted_sections_fall_back_without_crashing(self) -> None:
        config = validar_configuracion(
            {
                "appearance": "broken",
                "behavior": None,
                "hotkeys": [],
                "system": "broken",
            }
        )

        self.assertIsInstance(config["appearance"], dict)
        self.assertEqual(config["appearance"]["primary_color"], "#522E18")
        self.assertEqual(config["behavior"]["visible_seconds"], 10)
        self.assertEqual(config["hotkeys"]["open"], "p+enter")
        self.assertEqual(config["system"]["language"], "english")

    def test_string_false_is_not_treated_as_true(self) -> None:
        config = validar_configuracion(
            {
                "behavior": {"click_through_on_blur": "false"},
                "system": {"start_with_windows": "false"},
            }
        )

        self.assertFalse(config["behavior"]["click_through_on_blur"])
        self.assertFalse(config["system"]["start_with_windows"])

    def test_non_finite_numbers_use_safe_defaults(self) -> None:
        config = validar_configuracion(
            {
                "appearance": {
                    "font_size": "nan",
                    "transparency": "inf",
                },
                "system": {"start_with_windows": float("nan")},
            }
        )

        self.assertEqual(config["appearance"]["font_size"], 16)
        self.assertEqual(config["appearance"]["transparency"], 60)
        self.assertFalse(config["system"]["start_with_windows"])

    def test_env_file_without_key_falls_back_to_process_environment(self) -> None:
        previous_path = config_manager.ARCHIVO_ENV

        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("# intentionally empty\n", encoding="utf-8")
            config_manager.ARCHIVO_ENV = env_path

            try:
                with patch.dict(os.environ, {"GEMINI_API_KEY": "AQ.test-fallback"}):
                    self.assertEqual(cargar_api_key(), "AQ.test-fallback")
            finally:
                config_manager.ARCHIVO_ENV = previous_path


class GeminiRestParsingTests(unittest.TestCase):
    def test_extracts_text_from_current_interactions_steps(self) -> None:
        payload = {
            "steps": [
                {
                    "type": "model_output",
                    "content": [
                        {"type": "text", "text": "Hello"},
                        {"type": "text", "text": "world"},
                    ],
                }
            ]
        }

        self.assertEqual(_extraer_texto_rest(payload), "Hello\nworld")

    def test_ignores_non_text_steps(self) -> None:
        payload = {
            "steps": [
                {"type": "tool_result", "content": [{"type": "text", "text": "skip"}]},
                {"type": "model_output", "content": [{"type": "image", "data": "..."}]},
            ]
        }

        self.assertEqual(_extraer_texto_rest(payload), "")


if __name__ == "__main__":
    unittest.main()
