"""QR8 analytic fixtures; no registered initial-state trajectory is simulated."""

import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis import experiment_0008 as q
from analysis.experiment_0005 import fnv


class CommunicationTests(unittest.TestCase):
    def test_registered_geometry_and_observation_budget(self):
        regions = q.geometry()
        self.assertEqual(
            [len(r["ids"]) for r in regions.values()], [6, 18, 38, 65, 146, 12, 35, 70, 114, 225]
        )
        self.assertTrue(
            all(
                len(r["probes"]) == 6 and not {2182, 2186}.intersection(r["ids"])
                for r in regions.values()
            )
        )
        self.assertEqual(len(list(q.layouts())), 101)
        self.assertEqual(q.hops(2182, 2186), 4)

    def test_half_edge_energy_sign_and_interference(self):
        p = np.zeros((4096, 8, 8), dtype="u1")
        u = np.zeros(p.shape)
        v = np.zeros_like(u)
        u[0, 1, 1] = 1
        u[0, 1, 2] = 1
        k, _a, m, parts = q.partitions(p, u, v)
        u[0, 1, 2] = -1
        k, b, m, other = q.partitions(p, u, v)
        self.assertAlmostEqual(sum(other) - sum(parts), 0.075, places=13)
        self.assertGreater(float(b[0, 0, 1]), 0)
        self.assertEqual(float(m[0, 0, 1]), 0)
        _, inverted, _, _ = q.partitions(p, -u, -v)
        np.testing.assert_array_equal(b, inverted)
        self.assertGreater(float((k + b).sum()), 0)

    def test_numeric_decoder_and_reference_isolation(self):
        means = np.array([[-1.0, 0.0], [1.0, 0.0]])
        self.assertEqual(q.predict(np.array([-1.0, 0.0]), means)[0], 0)
        self.assertIsNone(q.predict(np.zeros(2), means)[0])
        with self.assertRaises(ValueError):
            q.predict(np.array([np.nan, 0.0]), means)
        # Analytic numeric vectors only; keys do not simulate those bodies.
        vectors = {seed: means.copy() for seed in q.TRAIN}
        np.testing.assert_array_equal(q.fit(vectors), means)
        vectors[127] = means
        with self.assertRaises(ValueError):
            q.fit(vectors)

    def test_synthetic_zero_record_and_corruption(self):
        name = b"s12345_ZERO"
        body = bytearray(b"QR6FLD01")
        body.extend(struct.pack("<QQdQQQQ", 1, 0, 0.025, 12345, 0, len(name), 27))
        body.extend(name)
        body.extend(bytes(17 * q.FIELDS))
        body.extend(struct.pack("<Q", fnv(body)))
        data = bytearray(b"QR8FLD01")
        data.extend(struct.pack("<4Q2d2Q", 1, 6, 2182, 2186, 0.0, 0.0, len(body), q.FIELDS))
        data.extend(body)
        data.extend(bytes(16 * q.FIELDS))
        data.extend(struct.pack("<Q", fnv(data)))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.q8f"
            path.write_bytes(data)
            self.assertEqual(q.decode(path)["signal"], "ZERO")
            data[100] ^= 1
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                q.decode(path)
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(FileNotFoundError):
            q.decode(Path(folder) / "missing.q8f")
