"""Frozen QR12 condition matrix; generation never selects outcomes or seeds."""

import argparse
from pathlib import Path

from analysis.experiment_0009 import csv_write

GRIDS = {"P": (48, 0.05), "T": (48, 0.025), "F": (96, 0.025)}


def condition(
    name,
    grid,
    seed=401,
    geometry=0,
    policy="FIXED",
    forcing="PULSE",
    horizon=40,
    mask=None,
    scalar=0,
    checkpoint="",
):
    n, dt = GRIDS[grid]
    count = 1 if 10 <= geometry <= 13 else 2 if geometry in (2, 20, 21) else 4
    return dict(
        case=name,
        seed=seed,
        n=n,
        dt=dt,
        geometry=geometry,
        policy=policy,
        forcing=forcing,
        horizon=horizon,
        mask=(1 << count) - 1 if mask is None else mask,
        scalar=scalar,
        checkpoint=checkpoint,
    )


def plan(root, stage):
    root = Path(root)
    p = []
    if stage == "a":
        for label, grids in (
            ("FIXED", "PTF"),
            ("QUIET", "PF"),
            ("OFF", "PF"),
            ("SENSOR_OFF", "P"),
            ("REPEAT", "P"),
            ("NEW_LEGACY", "PF"),
            ("ORACLE", "PF"),
        ):
            for grid in grids:
                p.append(
                    condition(
                        label + "_" + grid,
                        grid,
                        horizon=24,
                        geometry=2 if label in ("NEW_LEGACY", "ORACLE") else 0,
                        mask=0 if label == "OFF" else None,
                        policy=label if label in ("ORACLE", "SENSOR_OFF") else "FIXED",
                        forcing="QUIET" if label == "QUIET" else "PULSE",
                    )
                )
    elif stage == "b":
        for label, grids in (
            ("ADAPTIVE", "PTF"),
            ("QUIET", "PF"),
            ("OFF", "PF"),
            ("TRACE_OFF", "PF"),
            ("VETO_ALL", "PF"),
            ("REPEAT", "P"),
        ):
            for grid in grids:
                p.append(
                    condition(
                        label + "_" + grid,
                        grid,
                        policy="TRACE_OFF"
                        if label == "TRACE_OFF"
                        else "FIXED"
                        if label == "VETO_ALL"
                        else "ADAPTIVE",
                        forcing="QUIET" if label == "QUIET" else "PULSE",
                        mask=0 if label == "OFF" else None,
                    )
                )
    elif stage == "c":
        for label in ("PERMIT", "VETO", "SHAM", "EXTERNAL", "ISOLATED_PERMIT", "ISOLATED_VETO"):
            for grid in "PF":
                p.append(
                    condition(
                        label + "_" + grid,
                        grid,
                        policy=label,
                        horizon=24,
                        mask=1 if label.startswith("ISOLATED") else 15,
                        checkpoint=str(
                            root
                            / "b"
                            / ("ADAPTIVE_" + grid)
                            / ("pre-" + ("000320" if grid == "P" else "000640") + ".q12")
                        ),
                    )
                )
    elif stage == "d":
        labels = (
            "FIXED",
            "ADAPTIVE",
            "OFF",
            "COMMON",
            "NONADAPTIVE",
            "SUSTAINED_FIXED",
            "SUSTAINED_ADAPTIVE",
            "ALT_FIXED",
            "ALT_ADAPTIVE",
            "SIMPLE",
            "IND0",
            "IND1",
            "IND2",
            "IND3",
            "SOLO0",
            "PERTURB_FIXED",
            "PERTURB_ADAPTIVE",
        )
        for seed in (409, 419):
            for label in labels if seed == 409 else ("FIXED", "ADAPTIVE"):
                for grid in "PF":
                    p.append(
                        condition(
                            f"s{seed}_{label}_{grid}",
                            grid,
                            seed=seed,
                            policy="ADAPTIVE"
                            if "ADAPTIVE" in label
                            else "NONADAPTIVE"
                            if label == "NONADAPTIVE"
                            else "FIXED",
                            forcing="COMMON"
                            if label == "COMMON"
                            else label
                            if label.startswith(("IND", "SUSTAINED", "PERTURB"))
                            else "PULSE",
                            geometry=1
                            if label.startswith("ALT")
                            else 10 + int(label[-1])
                            if label.startswith("IND")
                            else 10
                            if label == "SOLO0"
                            else 0,
                            mask=0 if label == "OFF" else None,
                            scalar=int(label == "SIMPLE"),
                        )
                    )
    elif stage == "e":
        for grid in "PTF":
            p.append(condition("DIRECT4_" + grid, grid, seed=427, horizon=8))
        for label, g in (("PAIR01", 20), ("PAIR23", 21)):
            p.append(condition(label + "_P", "P", seed=427, horizon=8, geometry=g))
    assert len(p) == dict(a=13, b=12, c=12, d=38, e=5)[stage]
    return p


def create(root, stage):
    root = Path(root)
    dest = root / stage
    dest.mkdir(parents=True)
    rows = plan(root, stage)
    csv_write(dest / "plan.csv", rows)
    csv_write(dest / "initial-status.csv", [dict(case=r["case"], status="NOT RUN") for r in rows])
    gate = "A" if stage == "a" else str(root / ("a" if stage in ("b", "e") else "b") / "gates.json")
    (dest / "PREREQUISITE").write_text(gate + "\n")
    return dest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=list("abcde"))
    p.add_argument("root", type=Path)
    a = p.parse_args()
    print(create(a.root, a.stage))


if __name__ == "__main__":
    main()
