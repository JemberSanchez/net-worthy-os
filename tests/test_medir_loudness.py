"""tools/medir_loudness.py: the peak it reports as dBTP must be the true (inter-sample) peak."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from medir_loudness import pico_dbtp  # noqa: E402


class TestPicoReal(unittest.TestCase):
    def test_sees_the_peak_between_samples(self):
        # sine at sr/4, 45° phase: every sample sits at 0.707*A, the waveform reaches A (-6.02 dB)
        sr = 48000
        t = np.arange(sr) / sr
        audio = (0.5 * np.sin(2 * np.pi * sr / 4 * t + np.pi / 4))[:, None]
        self.assertAlmostEqual(20 * np.log10(np.abs(audio).max()), -9.03, places=1)  # sample peak
        self.assertAlmostEqual(pico_dbtp(audio), -6.02, delta=0.2)


if __name__ == "__main__":
    unittest.main()
