"""Verify external QR7 protocol identity and export controller energy consequences."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from analysis import experiment_0007 as q7
from analysis.experiment_0005 import fnv, require, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root
    verified = json.loads((root / "verification.json").read_text())
    for r in verified["trajectories"].values():
        q7.CHECKED.update(r["frames"])
    operations = []
    reuse_count = 0
    actual_count = 0
    for stage_name in ("train", "evaluate", "refine", "repeat"):
        stage = root / stage_name
        for folder in sorted(stage.iterdir()):
            if not folder.is_dir():
                continue
            if (folder / "REUSED").exists():
                source = (folder / "REUSED").read_text()
                require("/" not in source and ".." not in source, "reuse safety")
                params = rows(stage / source / "parameters.csv")[0]
                equivalence = (folder / "EQUIVALENT").read_text()
                require(
                    equivalence
                    == f"initial_fingerprint={params['initial_fingerprint']}\nfull_reset=true\n",
                    "actual calibration state equivalence",
                )
                name = folder.name.rsplit("_p", 1)[0]
                cal = source.rsplit("_p", 1)[0]
                require(
                    (stage / f"{name}.f64").read_bytes() == (stage / f"{cal}.f64").read_bytes(),
                    "exact logical reuse features",
                )
                reuse_count += 1
                continue
            if not (folder / "parameters.csv").exists():
                continue
            require(
                (folder / "COMPLETE").exists() and (folder / "RESET").exists(),
                "completed operation/reset",
            )
            params = rows(folder / "parameters.csv")[0]
            seed = int(params["seed"])
            initial = q7.checkpoint(stage, folder.name, 0)
            metrics = rows(folder / "metrics.csv")
            last = metrics[-1]
            end_energy = sum(float(last[key]) for key in ("kinetic", "onsite", "coupling"))
            switch = 0.0
            if params["operation"] == "Write":
                cal_stage = root / "train" if stage_name == "repeat" else stage
                virgin = q7.checkpoint(cal_stage, f"s{seed}_CALIBRATE_p9", 0)["palette"]
                require(
                    np.array_equal(initial["palette"], virgin),
                    "RESTORE virgin palette identity before WRITE",
                )
                post = q7.decode(folder / "post.q7f")
                commit = rows(folder / "commit.csv")[0]
                switch = float(commit["switch_work"])
                end_energy = float(commit["post"])
                retained_palette = post["palette"]
            else:
                retained_palette = initial["palette"]
            require(
                f"palette_fnv={fnv(retained_palette.tobytes())}\n"
                in (folder / "RESET").read_text(),
                "exact retained state identity",
            )
            e0 = float(params["initial_energy"])
            # RESET is external extraction/removal of the final mechanical energy.
            operations.append(
                dict(
                    stage=stage_name,
                    trajectory=folder.name,
                    operation=params["operation"],
                    seed=seed,
                    rule=int(params["rule"]),
                    pulse_energy=e0,
                    morphology_switch_work=switch,
                    energy_before_reset=end_energy,
                    reset_external_work=-end_energy,
                    total_external_mechanical_work=e0 + switch - end_energy,
                    damping_loss=float(last["loss"]) + float(last["boundary_loss"]),
                    restore_palette_at_zero_energy=params["operation"] == "Write",
                )
            )
            actual_count += 1
    require(actual_count == 499 and reuse_count == 192, "complete actual/reused operation coverage")
    tables = root / "tables"
    tables.mkdir(exist_ok=True)
    with (tables / "operations.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(operations[0]))
        writer.writeheader()
        writer.writerows(operations)
    receipt = dict(
        actual_operations=actual_count,
        reused_trajectories=reuse_count,
        virgin_restore_identity=True,
        reuse_identity=True,
        reset_palette_identity=True,
        reset_energy_scope="external reset energy removal; forgetting untested",
    )
    (root / "protocol-verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
