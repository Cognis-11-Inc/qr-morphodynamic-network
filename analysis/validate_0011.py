"""Fresh portable QR11 physical, trace, morphology and frozen-readout validation."""

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from analysis.audit_0011 import audit_stage
from analysis.communication_0011 import review, review_retained
from analysis.experiment_0009 import rows
from analysis.gates_0011 import l1, pilot
from analysis.morphology_0011 import retention_pilot, verify_operation
from analysis.report_0011 import STAGES, ledger


def validate(root, jobs=1):
    root = Path(root)
    checks = {}
    stages = [stage for stage in STAGES if (root / stage / "ledger.csv").exists()]
    # Independent analysis only: never launch or parallelize a physical trajectory.
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        audits = {stage: pool.submit(audit_stage, root / stage, True) for stage in stages}
        for stage, result in audits.items():
            checks[stage] = result.result()
    checks["L1"] = l1(root)
    checks["pilot"] = pilot(root)
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
