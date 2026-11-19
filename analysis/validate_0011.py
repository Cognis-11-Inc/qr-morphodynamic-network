"""Fresh portable QR11 physical, trace, morphology and frozen-readout validation."""

import argparse
import json
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from analysis import io_0011 as io
from analysis.audit_0011 import audit_stage
from analysis.audit_coupling_0010 import neuron_energy
from analysis.communication_0011 import review, review_retained
from analysis.experiment_0005 import require
from analysis.experiment_0009 import rows
from analysis.experiment_0010 import energy
from analysis.gates_0011 import l1, pilot
from analysis.morphology_0011 import retention_pilot, review_pilot, verify_operation
from analysis.report_0011 import STAGES, ledger


def stage_with_resets(folder):
    result = audit_stage(folder, fresh=True)
    resets = []
    for row in rows(folder / "ledger.csv"):
        case = folder / row["case"]
        metadata = rows(case / "metadata.csv")[0]
        if not metadata["state_ref"]:
            continue
        state = Path(metadata["state_ref"])
        nodes = io.neurons(state)["nodes"]
        reference = Path((state.parent / "fluid_reference.txt").read_text().strip())
        fluid = io.fluid(reference)
        removed = math.fsum(
            [energy(fluid["fields"], 24 / fluid["n"])]
            + [neuron_energy(n["palette"], n["u"], n["v"]) for n in nodes]
        )
        receipt = rows(case / "reset.csv")[0]
        error = abs(float(receipt["removed_energy"]) - removed) / max(removed, 1e-30)
        require(error <= 1e-12, "QR11 independently reconstructed reset energy removal")
        require(float(receipt["source_restore_work"]) == 0, "QR11 zero-state source restoration")
        initial = io.neurons(case / "000000.n11")["nodes"]
        for key in ("u", "v", "packet", "previous", "age", "z", "loss", "committed"):
            require(np.count_nonzero(initial[key]) == 0, "QR11 exact complete reset")
        require(
            np.count_nonzero(io.fluid(case / "000000.q11")["fields"]) == 0,
            "QR11 exact complete fluid reset",
        )
        resets.append(dict(case=row["case"], removed_energy=removed, relative_error=error))
    result["independent_reset_energy"] = resets
    return result


def validate(root, jobs=1):
    root = Path(root)
    checks = {}
    stages = [stage for stage in STAGES if (root / stage / "ledger.csv").exists()]
    # Independent analysis only: never launch or parallelize a physical trajectory.
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        audits = {stage: pool.submit(stage_with_resets, root / stage) for stage in stages}
        for stage, result in audits.items():
            checks[stage] = result.result()
    checks["L1"] = l1(root)
    checks["pilot"] = pilot(root)
    if (root / "morph_pilot/plan.csv").exists():
        checks["L4"] = review_pilot(root)
    for stage in ("morph_pilot", "morph_main"):
        if (root / stage / "plan.csv").exists():
            checks[stage] = {
                r["case"]: verify_operation(
                    root / stage / r["case"], r["enabled"].lower() == "true"
                )
                for r in rows(root / stage / "plan.csv")
            }
    checks["temporary_readouts"] = review(root)
    if (root / "retention_pilot/ledger.csv").exists():
        checks["retention_pilot_gates"] = retention_pilot(root)
    if (root / "retention_held/ledger.csv").exists():
        checks["retained_readouts"] = review_retained(root)
    checks["coverage"] = ledger(root)
    (root / "portable-validation.json").write_text(json.dumps(checks, indent=2) + "\n")
    print("Fresh independent validation complete; scientific nulls remain separate verdicts.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--jobs", type=int, choices=range(1, 5), default=1)
    a = p.parse_args()
    validate(a.root, a.jobs)


if __name__ == "__main__":
    main()
