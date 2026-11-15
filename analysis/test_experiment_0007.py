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
