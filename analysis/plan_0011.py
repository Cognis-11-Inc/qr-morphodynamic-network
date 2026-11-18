"""Frozen QR11 configuration plans; all physical updates and work fitting are Rust."""

import argparse
import csv
import json
import shutil
from pathlib import Path

from analysis.package_experiment_0007 import sha

GRIDS = {"P": (48, 0.05), "T": (48, 0.025), "F": (96, 0.025)}
TRAIN = (307, 311, 313, 317)
HELD = (331, 337, 347, 349)
FIELDS = (
    "case",
    "seed",
    "n",
    "dt",
    "distance",
    "module",
    "signal",
    "horizon",
    "policy",
    "mode",
    "three",
    "coupled",
    "state",
    "virgin",
)


def condition(
    name,
    grid="P",
    seed=301,
    distance=4,
    module=9,
    signal="STD",
    horizon=48,
    policy="fixed:1",
    mode="ON",
    three=0,
    coupled=1,
    state="",
    virgin="",
):
    n, dt = GRIDS[grid]
    return dict(
        zip(
            FIELDS,
            (
                name,
                seed,
                n,
                dt,
                distance,
                module,
                signal,
                horizon,
                policy,
                mode,
                three,
                coupled,
                state,
                virgin,
            ),
            strict=True,
        )
    )


def write(root, stage, plan, prerequisite):
    folder = Path(root) / stage
    folder.mkdir()
    with (folder / "plan.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(plan)
    (folder / "PREREQUISITE").write_text(str(prerequisite) + "\n")
    (folder / "initial-status.csv").write_text(
        "case,status\n" + "".join(r["case"] + ",NOT_RUN\n" for r in plan)
    )
    return folder


def l1(root):
    root = Path(root)
    root.mkdir(parents=True)
    plan = []
    for grid in ("P", "T", "F"):
        plan.append(condition("REF_" + grid, grid, 211, 2, signal="REF", horizon=24))
    for signal, name in (("REFNEG", "NEG"), ("ZERO", "QUIET")):
        for grid in ("P", "F"):
            plan.append(
                condition(
                    name + "_" + grid,
                    grid,
                    211,
                    2,
                    signal=signal,
                    horizon=24,
                    policy="fixed:0" if signal == "ZERO" else "fixed:1",
                )
            )
    for grid in ("P", "F"):
        plan.append(condition("OFF_" + grid, grid, 211, 2, signal="REF", horizon=24, coupled=0))
    plan.append(condition("SENSOR_OFF_P", "P", 211, 2, signal="REF", horizon=24, mode="SENSOR_OFF"))
    plan.append(condition("REPEAT_P", "P", 211, 2, signal="REF", horizon=24))
    for signal, name in (("AB+", "ABPLUS"), ("AB-", "ABMINUS")):
        plan.append(condition(name + "_P", "P", 211, 4, signal=signal, horizon=24, three=1))
    assert len(plan) == 13
    reference = root / "references"
    reference.mkdir()
    binding = {}
    old = Path("results/experiment_0010")
    for grid in ("P", "T", "F"):
        n, dt = GRIDS[grid]
        binding["REF_" + grid] = old / "pilot" / f"s211_m9_b0_d2_n{n}_dt{dt}_FLUID"
    for case, arm in (("ABPLUS_P", "IAB+"), ("ABMINUS_P", "IAB-")):
        binding[case] = old / "extended/interference" / f"s211_m9_b0_d4_n48_dt0.05_{arm}"
    inventory = {}
    for case, folder in binding.items():
        target = reference / case
        target.mkdir()
        for path in folder.iterdir():
            if (
                path.suffix == ".q10"
                or path.name.endswith(".neuron.csv")
                or path.name == "metadata.csv"
            ):
                shutil.copy2(path, target / path.name)
                inventory[str((target / path.name).relative_to(root))] = sha(path)
    (reference / "SOURCE_SHA256.json").write_text(
        json.dumps(dict(original_head="41c01eb", files=inventory), indent=2) + "\n"
    )
    return write(root, "l1", plan, "L1")


def paired(plan, folder, name, grid, **kwargs):
    cal = "cal_" + name
    plan.append(condition(cal, grid, mode="SENSOR_OFF", **kwargs))
    plan.append(condition(name, grid, policy="work1:" + str(Path(folder) / cal), **kwargs))


def pilot(root):
    root = Path(root)
    folder = root / "pilot"
    plan = []
    for signal, module, label in (("STD", 9, "S9"), ("STD", 27, "S27"), ("ORDER", 9, "ORDER")):
        for grid in ("P", "T", "F"):
            paired(plan, folder, label + "_" + grid, grid, module=module, signal=signal)
    for signal in ("NEG", "SINGLE"):
        for grid in ("P", "F"):
            paired(plan, folder, signal + "_" + grid, grid, signal=signal)
    for grid in ("P", "F"):
        amplitude = "same:" + str(folder / ("cal_S9_" + grid))
        plan.extend(
            (
                condition("QUIET_" + grid, grid, signal="ZERO", policy="fixed:0"),
                condition("OFF_" + grid, grid, policy=amplitude, coupled=0),
                condition("TRACE_OFF_" + grid, grid, policy=amplitude, mode="OFF"),
                condition("SCRAMBLED_" + grid, grid, policy=amplitude, mode="SCRAMBLED"),
            )
        )
    plan.append(condition("REPEAT_P", policy="same:" + str(folder / "cal_S9_P")))
    assert len(plan) == 35
    return write(root, "pilot", plan, root / "l1/gates.json")


def main_matrix(root, stage):
    root = Path(root)
    folder = root / stage
    plan = []
    seeds = TRAIN if stage == "train" else HELD
    grids = ("P",) if stage == "train" else ("P", "F")
    for seed in seeds:
        for d in (4, 6):
            for module in (9, 27):
                for grid in grids:
                    paired(
                        plan,
                        folder,
                        f"s{seed}_d{d}_m{module}_{grid}",
                        grid,
                        seed=seed,
                        distance=d,
                        module=module,
                    )
    assert len(plan) == (32 if stage == "train" else 64)
    return write(root, stage, plan, root / "pilot/gates.json")


def controls(root):
    root = Path(root)
    folder = root / "controls"
    plan = []
    for signal in ("ORDER", "NEG"):
        for grid in ("P", "F"):
            paired(plan, folder, signal + "_" + grid, grid, seed=331, signal=signal)
    assert len(plan) == 8
    return write(root, "controls", plan, root / "pilot/gates.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("l1", "pilot", "train", "held", "controls"))
    parser.add_argument("root", type=Path)
    a = parser.parse_args()
    function = {
        "l1": l1,
        "pilot": pilot,
        "train": lambda r: main_matrix(r, "train"),
        "held": lambda r: main_matrix(r, "held"),
        "controls": controls,
    }[a.stage]
    print(function(a.root))


if __name__ == "__main__":
    main()
