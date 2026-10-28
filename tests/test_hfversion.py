"""HyperFrames version resolution (video-v2/motor/hfversion.py): one version per production, the
latest on npm unless HF_VERSION pins it, and core/carve checked against it."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video-v2", "motor"
    ),
)

import hfversion


def _npm(stdout: str, code: int = 0):
    return mock.patch.object(
        hfversion.subprocess,
        "run",
        return_value=subprocess.CompletedProcess(
            [], code, stdout=stdout, stderr="boom"
        ),
    )


class VersionTest(unittest.TestCase):
    def setUp(self):
        hfversion.version.cache_clear()
        self.addCleanup(hfversion.version.cache_clear)

    def test_pin_wins_and_npm_is_not_called(self):
        with (
            mock.patch.dict(os.environ, {"HF_VERSION": "0.8.62"}),
            _npm("9.9.9") as run,
        ):
            self.assertEqual(hfversion.version(), "0.8.62")
        run.assert_not_called()

    def test_latest_from_npm_resolved_once(self):
        with mock.patch.dict(os.environ, {"HF_VERSION": ""}), _npm("0.8.214\n") as run:
            self.assertEqual(hfversion.version(), "0.8.214")
            self.assertEqual(
                hfversion.npx("lint")[-2:], ["hyperframes@0.8.214", "lint"]
            )
        self.assertEqual(run.call_count, 1)

    def test_npm_failure_or_garbage_is_an_error_not_a_silent_default(self):
        for out, code in (("", 1), ("<html>proxy</html>", 0)):
            hfversion.version.cache_clear()
            with (
                mock.patch.dict(os.environ, {"HF_VERSION": ""}),
                _npm(out, code),
                self.assertRaises(hfversion.VersionError),
            ):
                hfversion.version()


class InstalledVersionTest(unittest.TestCase):
    def test_core_and_carve_versions_read_from_disk(self):
        with tempfile.TemporaryDirectory() as d:
            core = Path(d, "hf", "node_modules", "@hyperframes", "core")
            core.mkdir(parents=True)
            (core / "package.json").write_text(json.dumps({"version": "0.8.214"}))
            cli = Path(d, "repo", "packages", "cli")
            cli.mkdir(parents=True)
            (cli / "package.json").write_text(json.dumps({"version": "0.8.214"}))
            carve = Path(
                d, "repo", "skills", "media-use", "audio", "scripts", "carve.mjs"
            )
            carve.parent.mkdir(parents=True)
            carve.touch()
            self.assertEqual(hfversion.version_core(Path(d, "hf")), "0.8.214")
            self.assertEqual(hfversion.version_carve(carve), "0.8.214")
            self.assertIsNone(hfversion.version_core(d))  # no core installed there
            self.assertIsNone(hfversion.version_core(None))
            self.assertIsNone(hfversion.version_carve(None))


if __name__ == "__main__":
    unittest.main()
