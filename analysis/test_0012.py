"""QR12 plan coverage, local eligibility and complete-state boundary invariants."""

import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis.audit_0012 import proposal
from analysis.experiment_0005 import fnv
from analysis.io_0012 import NODE, snapshot
from analysis.plan_0012 import plan


class MorphodynamicTests(unittest.TestCase):
    def test_matrix_has_80_unique_trajectories_and_declared_private_fluids(self):
        all_cases = [
            (stage, row) for stage in "abcde" for row in plan(Path("results/fixture12"), stage)
        ]
        self.assertEqual(len(all_cases), 80)
        self.assertEqual(len({(s, r["case"]) for s, r in all_cases}), 80)
        private = [r for s, r in all_cases if s == "d" and 10 <= r["geometry"] <= 13]
        self.assertEqual(len(private), 10)
        self.assertTrue(all(r["mask"] == 1 for r in private))
        branches = [r for s, r in all_cases if s == "c"]
        self.assertTrue(all(r["checkpoint"].endswith(".q12") for r in branches))

    def test_local_candidate_requires_real_eligibility_and_refractory(self):
        n = np.zeros(1, dtype=NODE)[0]
        n["age"] = 320
        n["palette"] = np.arange(64) % 5
        self.assertIsNone(proposal(n, True, 0, 0.05))
        n["z"][277 + 9] = 0.4
        n["z"][277 + 10] = 0.5
        self.assertEqual(proposal(n, True, 0, 0.05), (9, 10))
        self.assertIsNone(proposal(n, False, 0, 0.05))
        self.assertIsNone(proposal(n, True, 319, 0.05))

    def test_complete_checkpoint_checksum_and_controller_constraints(self):
        count, n = 4, 4
        b = b"QR12FUL1" + struct.pack("<3Qd5Q", 1, n, 0, 0.05, 997, count, 0, 0, 15)
        b += np.array(
            ((10, 10, 12), (14, 10, 12), (10, 14, 12), (14, 14, 12)), dtype="<f8"
        ).tobytes()
        b += bytes(32 * n**3)
        nodes = np.zeros(count, dtype=NODE)
        b += nodes.tobytes() + bytes(64 + 96 * count)
        b += struct.pack("<Q", fnv(b))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "state.q12"
            p.write_bytes(b)
            self.assertEqual(snapshot(p)["count"], 4)
            corrupt = bytearray(b)
            corrupt[100] ^= 1
            p.write_bytes(corrupt)
            with self.assertRaises(ValueError):
                snapshot(p)
            nodes["events"][0] = 4
            offset = 80 + 24 * count + 32 * n**3
            corrupt = b[:offset] + nodes.tobytes() + bytes(64 + 96 * count)
            p.write_bytes(corrupt + struct.pack("<Q", fnv(corrupt)))
            with self.assertRaises(ValueError):
                snapshot(p)


if __name__ == "__main__":
    unittest.main()


class CompositionBoundaryTests(unittest.TestCase):
    def test_shared_interfaces_reject_bad_physical_binding(self):
        from dataclasses import replace

        from analysis.composition_0012 import Interface, compile_modules, ordinary_validator

        valid = (Interface(), Interface(nodes=(2, 3)))
        self.assertEqual(len(compile_modules(valid)), 8)
        self.assertTrue(ordinary_validator(valid))
        for bad in (replace(valid[1], n=96), replace(valid[1], nodes=(1, 2))):
            with self.assertRaises(ValueError):
                compile_modules((valid[0], bad))
            self.assertFalse(ordinary_validator((valid[0], bad)))

    def test_vectorized_fluid_map_keeps_exact_zero_and_wall_slots(self):
        from analysis.composition_0012 import fluid_step

        a = np.zeros((4, 8, 8, 8))
        fluid_step(a, 0.05)
        self.assertEqual(np.count_nonzero(a), 0)
        a[0, 4, 4, 4] = 0.1
        for _ in range(3):
            fluid_step(a, 0.05)
        for j in range(3):
            sl = [slice(None)] * 3
            sl[2 - j] = -1
            self.assertEqual(np.count_nonzero(a[j + 1][tuple(sl)]), 0)
