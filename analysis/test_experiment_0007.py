"""Independent decoder and train/evaluation isolation checks on synthetic data."""

import unittest

import numpy as np

from analysis.experiment_0007 import TRAIN, fit, predict


class OperationalTests(unittest.TestCase):
    def test_numeric_prediction_and_ambiguity(self):
        means = np.array([np.zeros(120), np.ones(120)])
        self.assertEqual(predict(np.zeros(120), means)[0], 0)
        self.assertEqual(predict(np.ones(120), means)[0], 1)
        self.assertIsNone(predict(np.full(120, 0.5), means)[0])
        with self.assertRaises(ValueError):
            predict(np.full(120, np.nan), means)
        with self.assertRaises(ValueError):
            predict(np.zeros(121), means)

    def test_heldout_data_cannot_enter_fit(self):
        vectors = {seed: np.array([np.zeros(120), np.ones(120)]) for seed in TRAIN}
        np.testing.assert_array_equal(fit(vectors)[1], np.ones(120))
        vectors[59] = vectors[7]
        with self.assertRaises(ValueError):
            fit(vectors)

    def test_checkpoint_physical_port_and_corruption(self):
        import struct
        import tempfile
        from pathlib import Path

        from analysis.experiment_0005 import fnv
        from analysis.experiment_0007 import decode

        # Entirely synthetic zero field, unregistered seed; not an engine observation.
        body = bytearray(b"QR6FLD01")
        body.extend(struct.pack("<QQdQQQQ", 1, 0, 0.025, 12345, 0, 4, 9))
        body.extend(b"test")
        body.extend(bytes(262144 * 17))
        body.extend(struct.pack("<Q", fnv(body)))
        outer = bytearray(b"QR7FLD01")
        outer.extend(struct.pack("<4Q", 1, 2183, 2, 2))
        outer.extend(body)
        outer.extend(struct.pack("<Q", fnv(outer)))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.q7f"
            path.write_bytes(outer)
            self.assertEqual(decode(path)["port"], 2183)
            outer[150] ^= 1
            path.write_bytes(outer)
            with self.assertRaises(ValueError):
                decode(path)
