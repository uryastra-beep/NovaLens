import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import runtime_control


class HarvisBridgeTests(unittest.TestCase):
    def test_bridge_paths_use_novalens_appdata(self) -> None:
        with tempfile.TemporaryDirectory() as folder, patch.dict(
            os.environ,
            {"APPDATA": folder},
        ):
            root = Path(folder)
            self.assertEqual(
                runtime_control.bridge_request_path(),
                root / "NovaLens" / runtime_control.BRIDGE_REQUEST_NAME,
            )
            self.assertEqual(
                runtime_control.bridge_response_path(),
                root / "NovaLens" / runtime_control.BRIDGE_RESPONSE_NAME,
            )

    def test_bridge_response_is_atomic_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as folder, patch.dict(
            os.environ,
            {"APPDATA": folder},
        ):
            self.assertTrue(
                runtime_control.write_bridge_response(
                    "request-1",
                    "completed",
                    "x" * (runtime_control.BRIDGE_MAX_TEXT_CHARACTERS + 50),
                )
            )

            payload = json.loads(
                runtime_control.bridge_response_path().read_text(encoding="utf-8")
            )
            self.assertEqual(payload["version"], 1)
            self.assertEqual(payload["id"], "request-1")
            self.assertEqual(payload["status"], "completed")
            self.assertEqual(
                len(payload["text"]),
                runtime_control.BRIDGE_MAX_TEXT_CHARACTERS,
            )


if __name__ == "__main__":
    unittest.main()
