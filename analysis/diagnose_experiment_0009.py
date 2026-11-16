"""Post-outcome QR9 failure diagnosis; never changes frozen acceptance decisions."""

import argparse
import json
import math
from pathlib import Path

import numpy as np

from analysis import experiment_0009 as q


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    root = parser.parse_args().root
    verdict = json.loads((root / "verification.json").read_text())
    failures = [g for g in verdict["failures"] if g["gate"].startswith("energy_reconstruction")]
    worst = max(failures, key=lambda g: g["value"])
    time = float(worst["gate"].split("_t")[1])
    dt = float(worst["case"].split("_dt")[1])
    folder = root / worst["case"]
    frame = q.decode(folder / f"{round(time / dt):06}.q9a")
    values = frame["fields"].ravel()
    factor = 0.5 * (24 / frame["n"]) ** 3
    naive = 0.0
    for value in values:
        x = float(value)
        naive += x * x
    naive *= factor
    accurate = math.fsum(float(x) * float(x) for x in values) * factor
    pairwise = q.energy(frame["fields"], 24 / frame["n"])
    recorded = float(q.rows(folder / "metrics.csv")[round(time / dt)]["energy"])
    assert naive == recorded
    assert abs(accurate - pairwise) / accurate < 1e-14
    predictions = []
    for mode in q.MODES:
        for n, dt in q.GRIDS:
            k = np.array(mode) * np.pi / 24
            h = 24 / n
            kh = 2 / h * (9 / 8 * np.sin(k * h / 2) - np.sin(3 * k * h / 2) / 24)
            wh, wc = float(np.linalg.norm(kh)), float(np.linalg.norm(k))
            wn = 2 * math.asin(dt * wh / 2) / dt
            scale = 1 / math.sqrt(1 - (dt * wh / 2) ** 2)
            errors = [
                math.hypot(
                    math.cos(wn * t) - math.cos(wc * t),
                    scale * math.sin(wn * t) - math.sin(wc * t),
                )
                for t in (6, 12, 24)
            ]
            observed = next(
                float(x["continuum_max"])
                for x in q.rows(root / "case_summary.csv")
                if x["case"] == f"{q.fixture_name(mode)}_n{n}_dt{dt}"
            )
            assert abs(max(errors) - observed) < 1e-10
            predictions.append(
                dict(
                    mode=mode,
                    n=n,
                    dt=dt,
                    continuum_frequency=wc,
                    semidiscrete_frequency=wh,
                    split_frequency=wn,
                    formula_max_error=max(errors),
                    measured_max_error=observed,
                )
            )
    result = dict(
        scope="Post-outcome analytic diagnosis only; frozen failures remain unchanged.",
        energy=dict(
            case=worst["case"],
            time=time,
            recorded=recorded,
            serial_naive_sum=naive,
            math_fsum=accurate,
            numpy_pairwise=pairwise,
            serial_matches_recorded=naive == recorded,
            pairwise_fsum_relative=abs(pairwise - accurate) / accurate,
        ),
        modal_predictions=predictions,
    )
    (root / "diagnosis.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Serial summation reproduced; analytic dispersion predicts all12 modal maxima.")


if __name__ == "__main__":
    main()
