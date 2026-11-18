"""Synthetic QR10 independent references and strict corruption checks."""

import math
import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis import experiment_0010 as q
from analysis.experiment_0005 import fnv


class QR10Tests(unittest.TestCase):
    def test_compensated_reference_and_partition(self):
        fields = np.zeros((4, 24, 24, 24))
        fields[0].flat[0] = 1e8
        fields[0].flat[1:] = 1
        self.assertEqual(q.energy(fields, 1), 0.5 * math.fsum([1e16, 24**3 - 1]))
        self.assertEqual(len(list(q.layout())), 26)

    def test_split_and_semidiscrete_have_distinct_time_error(self):
        exact = q.old.exact(24, (4, 0, 0), 6, True)
        errors = [
            q.old.relative(q.split_exact(24, (4, 0, 0), 6, dt), exact)
            for dt in (0.05, 0.025, 0.0125)
        ]
        self.assertTrue(0.24 < errors[1] / errors[0] < 0.26)
        self.assertTrue(0.24 < errors[2] / errors[1] < 0.26)
        np.testing.assert_array_equal(
            q.split_exact(24, (4, 0, 0), 0, 0.05), q.old.exact(24, (4, 0, 0), 0)
        )

    def test_schema_exact_length_checksum_and_identity(self):
        data = bytearray(b"QR10AC01" + struct.pack("<3Qd4Q", 1, 24, 0, 0.05, 2, 0, 0, 0))
        data.extend(bytes(32 * 24**3))
        data.extend(struct.pack("<Q", fnv(data)))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.q10"
            path.write_bytes(data)
            self.assertEqual(q.energy(q.decode(path)["fields"], 1), 0)
            data[-20] ^= 1
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                q.decode(path)
            path.write_bytes(data[:-1])
            with self.assertRaises(ValueError):
                q.decode(path)


if __name__ == "__main__":
    unittest.main()
