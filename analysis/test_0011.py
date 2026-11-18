"""Synthetic QR11 schema, locality, trace input and restriction checks."""

import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis import io_0011 as io
from analysis.audit_0011 import neural_free, phi
from analysis.experiment_0005 import fnv


class ListeningTests(unittest.TestCase):
    def test_trace_phi_preserves_polarity_and_bounds(self):
        a = np.zeros(2, dtype=io.NODE)
        a["palette"] = np.arange(64) % 5
        a["u"] = np.sin(np.arange(64))
        a["v"] = 0.2
        a["packet"] = np.array([0.01, -0.02, 0.03, -0.04, 0.02, -0.01, 0.03])
        b = a.copy()
        b["u"] *= -1
        b["v"] *= -1
        b["packet"][:, [0, 1, 2, 3, 6]] *= -1
        x, y = phi(a), phi(b)
        np.testing.assert_array_equal(x[:, [0, 1, 2, 3, 6]], -y[:, [0, 1, 2, 3, 6]])
        np.testing.assert_array_equal(x[:, 7:], y[:, 7:])
        self.assertTrue((abs(x) <= 1).all())
        self.assertEqual(a.dtype.itemsize, 4416)

    def test_snapshot_corruption_and_legal_state(self):
        a = np.zeros(2, dtype=io.NODE)
        b = bytearray(b"QR11NEU1" + struct.pack("<3Qd", 1, 2, 0, 0.05) + a.tobytes())
        b += struct.pack("<Q", fnv(b))
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "state.n11"
            p.write_bytes(b)
            self.assertEqual(io.neurons(p)["nodes"].shape, (2,))
            b[-20] ^= 1
            p.write_bytes(b)
            with self.assertRaises(ValueError):
                io.neurons(p)

    def test_local_sensor_restriction_and_neural_zero(self):
        fields = np.zeros((4, 48, 48, 48))
        fields[0] = 1
        np.testing.assert_allclose(io.local(fields, (10.5, 12.5, 12.5)), [1, 0, 0, 0, 0.5])
        np.testing.assert_array_equal(
            io.restrict(np.ones((4, 96, 96, 96))), np.ones((4, 48, 48, 48))
        )
        p = np.ones((2, 64), dtype=int)
        u, v, loss = neural_free(p, np.zeros((2, 64)), np.zeros((2, 64)), 0.05)
        self.assertEqual(
            float(np.max(abs(u))) + float(np.max(abs(v))) + float(np.max(abs(loss))), 0
        )


if __name__ == "__main__":
    unittest.main()
