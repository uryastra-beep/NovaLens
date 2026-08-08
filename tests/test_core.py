from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from unittest.mock import patch

import config_manager
import screen_selector
from backend import _extraer_texto_rest
from config_manager import cargar_api_key, validar_configuracion
from rolling_audio import RollingAudioBuffer
from screen_selector import normalizar_region


class ConfigValidationTests(unittest.TestCase):
    def test_corrupted_sections_fall_back_without_crashing(self) -> None:
        config = validar_configuracion(
            {
                "appearance": "broken",
                "behavior": None,
                "audio": "broken",
                "hotkeys": [],
                "system": "broken",
            }
        )

        self.assertIsInstance(config["appearance"], dict)
        self.assertEqual(config["appearance"]["primary_color"], "#522E18")
        self.assertEqual(config["behavior"]["visible_seconds"], 10)
        self.assertTrue(config["audio"]["enabled"])
        self.assertEqual(config["audio"]["duration_seconds"], 10)
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

    def test_audio_options_are_normalized_and_clamped(self) -> None:
        config = validar_configuracion(
            {
                "audio": {
                    "enabled": "false",
                    "duration_seconds": 999,
                    "show_indicator": "false",
                }
            }
        )

        self.assertFalse(config["audio"]["enabled"])
        self.assertEqual(config["audio"]["duration_seconds"], 30)
        self.assertFalse(config["audio"]["show_indicator"])

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


class ScreenRegionTests(unittest.TestCase):
    def test_normalizes_reverse_drag_and_clamps_to_screen(self) -> None:
        self.assertEqual(
            normalizar_region((120, 90), (-20, 10), 100, 80),
            (0, 10, 100, 80),
        )

    def test_rejects_accidental_tiny_selection(self) -> None:
        self.assertIsNone(normalizar_region((10, 10), (15, 18), 100, 80))

    def test_selector_prefers_thread_dpi_context_after_flet_starts(self) -> None:
        set_thread = mock.Mock(return_value=123)
        set_process = mock.Mock(return_value=1)
        windll = SimpleNamespace(
            user32=SimpleNamespace(
                SetThreadDpiAwarenessContext=set_thread,
                SetProcessDpiAwarenessContext=set_process,
            ),
            shcore=SimpleNamespace(
                SetProcessDpiAwareness=mock.Mock(),
            ),
        )

        with (
            mock.patch.object(screen_selector.os, "name", "nt"),
            mock.patch.object(
                screen_selector.ctypes,
                "windll",
                windll,
                create=True,
            ),
        ):
            screen_selector._preparar_dpi()

        set_thread.assert_called_once()
        set_process.assert_not_called()
        windll.shcore.SetProcessDpiAwareness.assert_not_called()

    def test_selector_checks_failed_context_before_using_fallback(self) -> None:
        set_thread = mock.Mock(return_value=0)
        set_process = mock.Mock(return_value=0)
        set_legacy = mock.Mock()
        windll = SimpleNamespace(
            user32=SimpleNamespace(
                SetThreadDpiAwarenessContext=set_thread,
                SetProcessDpiAwarenessContext=set_process,
            ),
            shcore=SimpleNamespace(SetProcessDpiAwareness=set_legacy),
        )

        with (
            mock.patch.object(screen_selector.os, "name", "nt"),
            mock.patch.object(
                screen_selector.ctypes,
                "windll",
                windll,
                create=True,
            ),
        ):
            screen_selector._preparar_dpi()

        set_thread.assert_called_once()
        set_process.assert_called_once()
        set_legacy.assert_called_once_with(
            screen_selector.PROCESS_PER_MONITOR_DPI_AWARE
        )

    def test_native_capture_uses_exact_virtual_desktop_coordinates(self) -> None:
        select_object = mock.Mock(side_effect=[4, 3])

        def get_dibits(dc, bitmap, start, lines, data, info, usage):
            del dc, bitmap, start, info, usage
            screen_selector.ctypes.memmove(
                data,
                bytes((10, 20, 30, 0)),
                4,
            )
            return lines

        user32 = SimpleNamespace(
            GetDC=mock.Mock(return_value=1),
            ReleaseDC=mock.Mock(return_value=1),
        )
        gdi32 = SimpleNamespace(
            CreateCompatibleDC=mock.Mock(return_value=2),
            CreateCompatibleBitmap=mock.Mock(return_value=3),
            SelectObject=select_object,
            BitBlt=mock.Mock(return_value=1),
            GetDIBits=mock.Mock(side_effect=get_dibits),
            DeleteObject=mock.Mock(return_value=1),
            DeleteDC=mock.Mock(return_value=1),
        )
        windll = SimpleNamespace(user32=user32, gdi32=gdi32)

        with mock.patch.object(
            screen_selector.ctypes,
            "windll",
            windll,
            create=True,
        ):
            imagen = screen_selector._capturar_escritorio_virtual(
                -10,
                -20,
                1,
                1,
            )

        self.assertEqual(imagen.size, (1, 1))
        self.assertEqual(imagen.getpixel((0, 0)), (30, 20, 10))
        gdi32.BitBlt.assert_called_once_with(
            2,
            0,
            0,
            1,
            1,
            1,
            -10,
            -20,
            screen_selector.SRCCOPY | screen_selector.CAPTUREBLT,
        )
        self.assertEqual(select_object.call_count, 2)
        user32.ReleaseDC.assert_called_once_with(None, 1)

    def test_selected_preview_clips_one_full_size_draw(self) -> None:
        dib = mock.Mock()
        gdi32 = SimpleNamespace(
            SaveDC=mock.Mock(return_value=7),
            IntersectClipRect=mock.Mock(return_value=2),
            RestoreDC=mock.Mock(return_value=1),
        )

        screen_selector._dibujar_region_original_sin_escalar(
            11,
            dib,
            gdi32,
            (100, 200, 500, 600),
            1920,
            1080,
        )

        gdi32.IntersectClipRect.assert_called_once_with(
            11,
            100,
            200,
            500,
            600,
        )
        dib.draw.assert_called_once_with(11, (0, 0, 1920, 1080))
        gdi32.RestoreDC.assert_called_once_with(11, 7)


class RollingAudioBufferTests(unittest.TestCase):
    def test_shortening_duration_discards_old_pcm_immediately(self) -> None:
        buffer = RollingAudioBuffer(
            duration_seconds=10,
            sample_rate=8_000,
            channels=1,
        )
        buffer._callback(b"\0" * 80_000, 0, None, None)

        buffer.set_duration(3)

        self.assertEqual(buffer.duration_seconds, 3)
        self.assertLessEqual(buffer.available_seconds(), 3.0)


if __name__ == "__main__":
    unittest.main()
