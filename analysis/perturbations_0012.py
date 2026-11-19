"""Descriptive per-node reach, onset and decay of the registered D impulse."""

import json
from pathlib import Path

import numpy as np

from analysis.causal_0012 import relative_delta
from analysis.experiment_0009 import csv_write
from analysis.gates_0012 import uv


def review(root):
    root = Path(root)
    out = []
    for policy in ("FIXED", "ADAPTIVE"):
        deltas = {}
        bases = {}
        for grid in "PF":
            stride = 1 if grid == "P" else 2
            a = uv(root / "d" / f"s409_PERTURB_{policy}_{grid}")[::stride]
            b = uv(root / "d" / f"s409_{policy}_{grid}")[::stride]
            deltas[grid] = a - b
            bases[grid] = b
        time = np.arange(len(deltas["P"])) * 0.05
        for node in range(4):
            fine = deltas["F"][:, node]
            coarse = deltas["P"][:, node]
            series = np.linalg.norm(fine.reshape(len(fine), -1), axis=1)
            peak = float(series.max())
            indices = np.flatnonzero(series > 1e-4 * max(peak, 1e-30))
            early = (time >= 24) & (time <= 28)
            late = time >= 36
            out.append(
                dict(
                    policy=policy,
                    node=node,
                    delta_norm=float(np.linalg.norm(fine)),
                    grid_error=float(np.linalg.norm(coarse - fine)),
                    relative_effect=relative_delta(fine, bases["F"][:, node]),
                    onset=float(time[indices[0]]) if len(indices) else None,
                    peak=peak,
                    late_to_early_rms=float(
                        np.sqrt(np.mean(series[late] ** 2))
                        / max(float(np.sqrt(np.mean(series[early] ** 2))), 1e-30)
                    ),
                    scope=(
                        "Descriptive registered perturbation; "
                        "adaptive global refinement invalid, no revised gate."
                    ),
                )
            )
    csv_write(root / "perturbation-effects.csv", out)
    (root / "perturbation-details.json").write_text(json.dumps(out, indent=2) + "\n")
    return out
