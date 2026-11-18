"""Synthetic independent QR10 isolated-neuron energy and transducer invariants."""

import unittest

import numpy as np

from analysis.audit_coupling_0010 import coefficients, neuron_energy


class CouplingTests(unittest.TestCase):
    def test_internal_gradient_matches_energy_and_boundary_degree(self):
        p = np.arange(64).reshape(8, 8) % 5
        omega, gamma, g = coefficients(p)
        self.assertEqual(float(gamma[0, 0]), 0.1)
        u = np.sin(np.arange(64) * 0.3).reshape(8, 8)
        v = np.zeros((8, 8))
        for module in (0, 9, 27, 63):
            y, x = divmod(module, 8)
            analytic = omega[y, x] * u[y, x]
            for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= yy < 8 and 0 <= xx < 8:
                    analytic += 0.15 * g[y, x] * g[yy, xx] * (u[y, x] - u[yy, xx])
            plus = u.copy()
            minus = u.copy()
            plus[y, x] += 1e-5
            minus[y, x] -= 1e-5
            gradient = (neuron_energy(p, plus, v) - neuron_energy(p, minus, v)) / 2e-5
            self.assertAlmostEqual(gradient, analytic, places=8)
        self.assertEqual(neuron_energy(p, u, v), neuron_energy(p, -u, -v))

    def test_exact_rotation_has_equal_opposite_exchange(self):
        for x, v in ((0.0, 1.0), (1.0, 0.0), (0.3, -0.7), (0.0, 0.0)):
            angle = 0.013
            xa = np.cos(angle) * x + np.sin(angle) * v
            va = np.cos(angle) * v - np.sin(angle) * x
            self.assertAlmostEqual(x * x + v * v, xa * xa + va * va, places=15)


if __name__ == "__main__":
    unittest.main()
