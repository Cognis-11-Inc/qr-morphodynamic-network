"""QR13 leakage, provenance-family and CPU instrument invariants on labelled fixtures."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis.dataset_0013 import arrays, partition
from analysis.structure_0013 import stiffness


class ObservationTests(unittest.TestCase):
    def test_family_partitions_do_not_use_timestamp_or_grid(self):
        self.assertEqual(partition(401), "train")
        self.assertEqual(partition(409), "validation")
        self.assertEqual(partition(419), "retrospective_test")
        self.assertEqual(partition(431), "prospective_test")

    def test_future_mutation_changes_target_not_first_forecast_input(self):
        # Synthetic software fixture only; never used as scientific data.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            n = 16
            values = dict(
                time=np.arange(n) * 0.2,
                u=np.zeros((n, 4, 64)),
                v=np.zeros((n, 4, 64)),
                packet=np.zeros((n, 4, 7)),
                z=np.zeros((n, 4, 405)),
                palette=np.zeros((n, 4, 64), dtype=np.uint8),
                controller=np.zeros((n, 4, 4)),
                energy=np.zeros((n, 4)),
                global_metrics=np.zeros((n, 9)),
            )
            record = dict(id="fixture", metadata=dict(forcing="PULSE"))
            np.savez(root / "data/fixture.npz", **values)
            old = arrays(root, record)
            values["u"][3, 0, 0] = 5.0
            values["palette"][3, 0, 0] = 4
            np.savez(root / "data/fixture.npz", **values)
            new = arrays(root, record)
            self.assertTrue(np.array_equal(old["x"][0], new["x"][0]))
            self.assertTrue(np.array_equal(old["palette"][0], new["palette"][0]))
            self.assertEqual(new["y"][0, 0, 0], 5.0)
            self.assertEqual(new["time"][0], 0.4)

    def test_stiffness_is_positive_symmetric_and_uses_palette(self):
        k, g = stiffness(np.zeros(64, dtype=int))
        other, _ = stiffness(np.ones(64, dtype=int))
        self.assertTrue(np.array_equal(k, k.T))
        self.assertGreater(np.linalg.eigvalsh(k).min(), 0)
        self.assertTrue((g > 0).all())
        self.assertGreater(np.linalg.norm(k - other), 0)


@unittest.skipUnless(importlib.util.find_spec("torch"), "optional external instrument dependency")
class TorchSmokeTests(unittest.TestCase):
    def test_cpu_forward_backward_does_not_change_observation(self):
        import torch

        from analysis.models_0013 import Predictor, setup

        setup()
        for kind in ("mlp", "gru"):
            model = Predictor(8, 5, 12, kind)
            x = torch.arange(48, dtype=torch.float32).reshape(2, 3, 8) / 48
            before = x.clone()
            palette = torch.zeros(2, 5)
            result = model(x, palette)
            result.square().mean().backward()
            self.assertEqual(tuple(result.shape), (2, 12))
            self.assertTrue(torch.isfinite(result).all())
            self.assertTrue(torch.equal(x, before))
            self.assertTrue(any(p.grad is not None for p in model.parameters()))

    def test_same_cpu_seed_reproduces_weights(self):
        import torch

        from analysis.models_0013 import Autoencoder, setup

        setup(17)
        a = Autoencoder().state_dict()
        setup(17)
        b = Autoencoder().state_dict()
        self.assertTrue(all(torch.equal(a[k], b[k]) for k in a))


if __name__ == "__main__":
    unittest.main()
