"""Fresh portable QR11 physical, trace, morphology and frozen-readout validation."""

import argparse
import json
from pathlib import Path

from analysis.audit_0011 import audit_stage
from analysis.communication_0011 import review, review_retained
from analysis.experiment_0009 import rows
from analysis.gates_0011 import l1, pilot
from analysis.morphology_0011 import retention_pilot, verify_operation
from analysis.report_0011 import STAGES, ledger


def validate(root):
    root = Path(root)
    checks = {}
    for stage in STAGES:
        folder = root / stage
        if (folder / "ledger.csv").exists():
            checks[stage] = audit_stage(folder, fresh=True)
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
    a = p.parse_args()
    validate(a.root)


if __name__ == "__main__":
    main()
