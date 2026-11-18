"""Viewer-independent QR11 review and complete signed field/trace archives."""

import argparse
import csv
import json
import shutil
from pathlib import Path

import numpy as np

from analysis import io_0011 as io
from analysis.audit_0011 import signature
from analysis.package_experiment_0007 import sha, source_metadata, write_zip
from analysis.report_0011 import STAGES, ledger

INSTRUCTIONS = """# Experiment 0011 portable review

Read EXPERIMENT_0011.md and docs/EXPERIMENT_0011_RESULTS.md first. Scientific
FAIL/INDETERMINATE/NOT RUN results are preserved. No overall success score.
Extract Quick_Review and Full_Fields_Traces into ONE empty directory. Raw paths
preserve results/experiment_0011 so original relative calibration/state references
remain valid. No viewer or GPU is required. Install pinned requirements-analysis
and requirements-plot in a fresh venv. Scientific replay:

    python -m analysis.gates_0011 l1 results/experiment_0011
    python -m analysis.gates_0011 pilot results/experiment_0011
    python -m analysis.audit_0011 results/experiment_0011/train --fresh
    python -m analysis.audit_0011 results/experiment_0011/held --fresh
    python -m analysis.audit_0011 results/experiment_0011/controls --fresh
    python -m analysis.communication_0011 review results/experiment_0011

Audit only EXECUTED stages listed in EXECUTION_LEDGER.csv. Missing dependent
stages are NOT RUN; do not invent outputs. Morphology operations can be checked
from before/after owned states without rerunning physical trajectories:

    python -m analysis.validate_0011 results/experiment_0011

The final receipt gives concrete complete validation commands and stage verdicts.
Never refit frozen templates. Later morphology/retention, IF executed:

    python -m analysis.audit_0011 results/experiment_0011/retention_pilot --fresh
    python -m analysis.audit_0011 results/experiment_0011/retention_train --fresh
    python -m analysis.audit_0011 results/experiment_0011/retention_held --fresh
    python -m analysis.communication_0011 review-retained results/experiment_0011

Rebuild source: cargo test --locked --lib
               cargo build --locked --release --bin experiment_0011
Verify baseline: sha256sum -c docs/EXPERIMENT_0011_PROTECTED_SHA256.txt

Quick_Review contains all source/specifications/reports/plots, owned checkpoints,
control/calibration/work/prediction ledgers, compact local histories and numeric
feature files. Full_Fields_Traces adds every actual signed fluid checkpoint,
every-tick405-component owned trace/u/v stream, original executable and QR10
reference fields. Full independent audits require BOTH archives. Small feature
files contain only numeric receiver observations; labels stay in a separate index.
Caches bind raw bytes and verifier source; --fresh forces independent remeasurement.

Per-archive member SHA256 and CRC are checked when packaged; RAW_SHA256SUMS binds
original raw data. Source-freeze snapshots and execution provenance identify the
actual original engine, not merely final delivery HEAD. Integrity is not authentication.
"""


def compact(root):
    root = Path(root)
    dest = root / "compact_review"
    dest.mkdir(exist_ok=True)
    features = []
    for stage in STAGES:
        if not (root / stage / "ledger.csv").exists():
            continue
        from analysis.experiment_0009 import rows

        for entry in rows(root / stage / "ledger.csv"):
            folder = root / stage / entry["case"]
            m = rows(folder / "metadata.csv")[0]
            # Calibration trajectories remain independent physical references, not fitting examples.
            if entry["case"].startswith("cal_"):
                continue
            s = io.stream(folder / "observations.q11o")
            a = s["frames"]["nodes"][:, 1]
            time = np.arange(s["ticks"] + 1) * s["dt"]
            target = dest / stage / entry["case"]
            target.mkdir(parents=True, exist_ok=True)
            values = np.column_stack(
                (time, a["packet"], a["z"].reshape(len(a), 3, 135)[:, :, :7].reshape(len(a), 21))
            )
            np.savetxt(
                target / "local_history.csv",
                values,
                delimiter=",",
                header="time,q,wx,wy,wz,density,power,dqdt,"
                + ",".join(f"tau{k}_{j}" for k in range(3) for j in range(7)),
                comments="",
                fmt="%.17e",
            )
            if stage in ("train", "held"):
                for rep in ("SIGNED", "ENERGY", "ALL_TRACE", "INSTANT", "QR10_STYLE"):
                    value = signature(folder, rep)
                    value.astype("<f8").tofile(target / (rep + ".f64"))
                    features.append(
                        dict(
                            stage=stage,
                            case=entry["case"],
                            seed=m["seed"],
                            distance=m["distance"],
                            source_module=m["module"],
                            representation=rep,
                            dimension=len(value),
                            file=str((target / (rep + ".f64")).relative_to(root)),
                        )
                    )
    if features:
        with (dest / "feature_index.csv").open("w") as f:
            w = csv.DictWriter(f, fieldnames=list(features[0]))
            w.writeheader()
            w.writerows(features)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--downloads", type=Path)
    a = p.parse_args()
    root = a.root
    assert not root.is_absolute(), "Archive preserves project-relative raw paths"
    ledger(root)
    compact(root)
    paths, head = source_metadata()
    sources = [Path(x) for x in paths if x]
    integrity = dict(head=head, sources={str(x): sha(x) for x in sources})
    (root / "source-integrity.json").write_text(json.dumps(integrity, indent=2) + "\n")
    reduced = []
    full = []
    raw = []
    for path in sorted(root.rglob("*")):
        if (
            not path.is_file()
            or "packages" in path.relative_to(root).parts
            or path.name
            in ("delivery.json", "source-integrity.json", "RAW_SHA256SUMS.txt", "package.log")
        ):
            continue
        name = str(path)
        raw.append(f"{sha(path)}  {name}\n")
        (
            full
            if path.suffix in (".q11", ".q11o", ".q10")
            or path.name.endswith("-runner")
            or path.name == "registered-runner"
            else reduced
        ).append((path, name))
    (root / "RAW_SHA256SUMS.txt").write_text("".join(raw))
    common = [(x, str(x)) for x in sources] + [
        (root / "source-integrity.json", "source-integrity.json"),
        (root / "RAW_SHA256SUMS.txt", "RAW_SHA256SUMS.txt"),
    ]
    output = root / "packages"
    output.mkdir(exist_ok=True)
    receipts = [
        write_zip(
            output / "QR_Neural_Memory_Experiment_0011_Quick_Review.zip",
            common + reduced,
            {"PORTABLE_README.md": INSTRUCTIONS},
        ),
        write_zip(
            output / "QR_Neural_Memory_Experiment_0011_Full_Fields_Traces.zip",
            full,
            {"PORTABLE_README.md": INSTRUCTIONS},
        ),
    ]
    if a.downloads:
        a.downloads.mkdir(exist_ok=True)
        for r in receipts:
            target = a.downloads / r["file"]
            shutil.copy2(output / r["file"], target)
            assert sha(target) == r["sha256"]
        shutil.copy2("docs/EXPERIMENT_0011_RESULTS.md", a.downloads / "EXPERIMENT_0011_RESULTS.md")
    (root / "delivery.json").write_text(json.dumps(receipts, indent=2) + "\n")
    print(json.dumps(receipts, indent=2))


if __name__ == "__main__":
    main()
