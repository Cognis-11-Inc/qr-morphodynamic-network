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


class ScientificBoundaryTests(unittest.TestCase):
    def test_external_features_exclude_the_actuated_source(self):
        from analysis.audit_0011 import signature

        dtype = np.dtype([("tick", "<u8"), ("nodes", io.NODE, (2,)), ("checksum", "<u8")])
        frames = np.zeros(481, dtype=dtype)
        frames["tick"] = np.arange(481)
        frames["nodes"][:, 1]["u"] = 0.12
        frames["nodes"][:, 1]["v"] = -0.03
        frames["nodes"][:, 1]["z"] = np.linspace(-0.5, 0.5, 405)
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "unrelated-A", Path(tmp) / "unrelated-B"
            a.mkdir()
            b.mkdir()
            header = b"QR11OBS1" + struct.pack("<3QdQ", 1, 2, 48, 0.05, 480)
            (a / "observations.q11o").write_bytes(header + frames.tobytes())
            frames["nodes"][:, 0]["u"] = 9876
            frames["nodes"][:, 0]["z"] = 0.99
            (b / "observations.q11o").write_bytes(header + frames.tobytes())
            for name in ("SIGNED", "ENERGY", "ALL_TRACE", "INSTANT", "QR10_STYLE"):
                np.testing.assert_array_equal(signature(a, name), signature(b, name))

    def test_fit_rejects_preexisting_held_out_observations(self):
        from analysis.communication_0011 import fit

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "held").mkdir()
            with self.assertRaises(ValueError):
                fit(Path(tmp))

    def test_morphology_auditor_rejects_a_legal_but_wrong_edit(self):
        import csv

        from analysis.audit_coupling_0010 import neuron_energy
        from analysis.morphology_0011 import verify_operation

        def save(path, nodes):
            b = b"QR11NEU1" + struct.pack("<3Qd", 1, 2, 960, 0.05) + nodes.tobytes()
            path.write_bytes(b + struct.pack("<Q", fnv(b)))

        before = np.zeros(2, dtype=io.NODE)
        before["palette"] = np.arange(64) % 5
        before["age"] = 960
        before["z"][:, 277] = 0.5
        before["z"][:, 278] = 0.4
        before["u"][:, 0] = 0.2
        after = before.copy()
        after["palette"][:, [0, 1]] = before["palette"][:, [1, 0]]
        after["committed"] = 1
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save(root / "before.n11", before)
            save(root / "after.n11", after)
            with (root / "commit.csv").open("w") as f:
                w = csv.writer(f)
                w.writerow(("neuron", "before_energy", "after_energy", "switch_work", "positions"))
                for i in (0, 1):
                    e0 = neuron_energy(before[i]["palette"], before[i]["u"], before[i]["v"])
                    e1 = neuron_energy(after[i]["palette"], after[i]["u"], after[i]["v"])
                    w.writerow((i, e0, e1, e1 - e0, 2))
            (root / "swaps.csv").write_text("neuron,a,b\n0,0,1\n1,0,1\n")
            self.assertTrue(verify_operation(root, True)["valid"])
            after["palette"][0, [2, 3]] = after["palette"][0, [3, 2]]
            save(root / "after.n11", after)
            with self.assertRaises(ValueError):
                verify_operation(root, True)
