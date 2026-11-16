"""Analytic QR9 fixtures; no registered case is executed by these tests."""

import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis import experiment_0009 as q
from analysis.experiment_0005 import fnv


class AcousticTests(unittest.TestCase):
    def test_energy_partition_and_sign_invariance(self):
        field = np.arange(4 * 6**3, dtype=float).reshape(4, 6, 6, 6) / 1000
        for axis in range(3):
            boundary = [slice(None)] * 3
            boundary[2 - axis] = -1
            field[axis + 1][tuple(boundary)] = 0
        self.assertAlmostEqual(q.energy(field, 0.5), q.density(field).sum() * 0.5**3)
        np.testing.assert_array_equal(q.density(field), q.density(-field))

    def test_analytic_solution_reference_and_refinement(self):
        density, c, bulk, mu = q.reference()
        self.assertTrue(1024 < density < 1026)
        self.assertAlmostEqual(c, 1521.4632)
        self.assertEqual(bulk, density * c**2)
        self.assertTrue(0.00107 < mu < 0.00108)
        for n in (24, 48):
            a = q.exact(n, (2, 0, 0), 0)
            b = q.exact(n, (2, 0, 0), 2.7)
            self.assertAlmostEqual(q.energy(a, 24 / n), q.energy(b, 24 / n), places=9)
        self.assertEqual(len(list(q.layout())), 17)

    def test_strict_schema_and_corruption(self):
        data = bytearray(b"QR9AC001" + struct.pack("<3Qd4Q", 1, 4, 0, 0.05, 2, 0, 0, 0))
        data.extend(bytes(32 * 4**3))
        data.extend(struct.pack("<Q", fnv(data)))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "zero.q9a"
            path.write_bytes(data)
            self.assertEqual(q.energy(q.decode(path)["fields"], 6), 0)
            data[-10] ^= 1
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                q.decode(path)
            path.write_bytes(data[:-1])
            with self.assertRaises(ValueError):
                q.decode(path)
            with self.assertRaises(FileNotFoundError):
                q.decode(Path(folder) / "missing.q9a")

    def test_wall_mirror_gradient_matches_analytic_eigenmode(self):
        n, h = 12, 2.0
        gradient = np.zeros((n - 1, n))
        for i in range(n - 1):
            gradient[i, i + 1] += 9 / 8 / h
            gradient[i, i] -= 9 / 8 / h
            gradient[i, min(i + 2, n - 1)] -= 1 / 24 / h
            gradient[i, max(i - 1, 0)] += 1 / 24 / h
        wavenumber = 2 * np.pi / 24
        pressure = np.cos(wavenumber * (np.arange(n) + 0.5) * h)
        kh = 2 / h * (9 / 8 * np.sin(wavenumber * h / 2) - np.sin(3 * wavenumber * h / 2) / 24)
        expected = -kh * np.sin(wavenumber * (np.arange(n - 1) + 1) * h)
        np.testing.assert_allclose(gradient @ pressure, expected, atol=1e-15)
        np.testing.assert_allclose(gradient.T @ gradient @ pressure, kh**2 * pressure, atol=1e-15)


if __name__ == "__main__":
    unittest.main()
