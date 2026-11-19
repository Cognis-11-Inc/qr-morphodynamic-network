"""Viewer-independent QR12 review and complete signed field/trace archives."""

import argparse
import json
import shutil
from pathlib import Path

import numpy as np

from analysis import io_0012 as io
from analysis.package_experiment_0007 import sha, source_metadata, write_zip
from analysis.report_0012 import coverage

INSTRUCTIONS = """# QR Morphodynamic Network — Experiment 0012 portable review

Read EXPERIMENT_0012.md, docs/EXPERIMENT_0012_RESULTS.md, EXPERIMENT_0012_COMPOSITION.md
and EXECUTION_CLARIFICATIONS first. Separate PASS/FAIL/INDETERMINATE/NOT RUN results,
original verifier defects, failed remote-effect threshold and failed categorical
engineering advantage are preserved. No overall score or memory/learning claim.

Extract BOTH archives into ONE empty directory. Original project-relative paths
results/experiment_0012 preserve calibration-free input and causal ancestry.
Create a fresh venv and install requirements-dev.txt,requirements-analysis.txt,
requirements-plot.txt. No viewer/GPU needed. Rebuild and independently audit:

    cargo test --locked --all-targets --all-features
    cargo build --locked --release --bin experiment_0012
    python -m ruff check analysis
    sha256sum -c docs/EXPERIMENT_0012_PROTECTED_SHA256.txt
    OPENBLAS_NUM_THREADS=1 python -m analysis.validate_0012 results/experiment_0012 --jobs 4
    python -m analysis.report_0012 results/experiment_0012

The validator executes independent analysis, never additional physical trajectories.
It checks all actual complete-state/trace/ODE/event/work records, exact causal
ancestry/interventions, numerical refinements, collective observables, formal
interface tests and independent re-execution of predictions from equations.
Prediction replay is verification, not fitting; original predictions were frozen
before direct E outcomes. Original executable/source-freeze/provenance identify
the actual engine d548de4, distinct from final delivery HEAD.

Quick_Review contains all tracked source/specifications/reports/figures, metadata,
event/force/port/work/refinement/verdict ledgers, initial/final owned node arrays
and compact actual node histories. Full_Evidence contains all complete fluid and
node checkpoints, every actual tick of complete owned states/traces/controllers,
original executable, original QR11 oracle observations and frozen predictions.
Full scientific validation requires BOTH. Compact plots/metrics are not a second
simulation. Old failures and initial mislabeled/incorrect-verifier receipts remain.

ZIP CRC/member SHA256 and original RAW_SHA256SUMS bind integrity, not authenticity.
Source-integrity HEAD and all source hashes are explicit. Runtime, portability,
commercial applications and categorical advantage remain separate questions.
"""


def compact(root):
    from analysis.experiment_0009 import rows

    dest = root / "compact_review"
    dest.mkdir(exist_ok=True)
    for stage in "abcde":
        if not (root / stage / "ledger.csv").exists():
            continue
        for entry in rows(root / stage / "ledger.csv"):
            folder = root / stage / entry["case"]
            s = io.stream(folder)
            nodes = s["frames"]["nodes"]
            target = dest / stage / entry["case"]
            target.mkdir(parents=True, exist_ok=True)
            np.savez(target / "initial-final-nodes.npz", initial=nodes[0], final=nodes[-1])
            lines = []
            metrics = rows(folder / "metrics.csv")
            for tick, frame in enumerate(nodes):
                for i, n in enumerate(frame):
                    lines.append(
                        [
                            (s["start"] + tick) * s["dt"],
                            i,
                            n["u"][9],
                            n["v"][9],
                            n["packet"][0],
                            float(metrics[tick]["e" + str(i)]),
                            max(n["z"][277:341]),
                            int(n["events"]) if "events" in n.dtype.names else 0,
                        ]
                    )
            np.savetxt(
                target / "node-history.csv",
                lines,
                delimiter=",",
                header="time,node,u9,v9,q,energy,H8max,events",
                comments="",
                fmt="%.17e",
            )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--downloads", type=Path)
    a = p.parse_args()
    root = a.root
    assert not root.is_absolute(), "Archive preserves project-relative raw paths"
    coverage(root)
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
            if path.suffix in (".q12", ".q12o", ".q11", ".q11o", ".n11")
            or ("predictions" in path.relative_to(root).parts and path.suffix == ".npz")
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
            output / "QR_Morphodynamic_Network_Experiment_0012_Quick_Review.zip",
            common + reduced,
            {"PORTABLE_README.md": INSTRUCTIONS},
        ),
        write_zip(
            output / "QR_Morphodynamic_Network_Experiment_0012_Full_Evidence.zip",
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
        for name in ("EXPERIMENT_0012_RESULTS.md", "EXPERIMENT_0012_EXPLOITATION.md"):
            shutil.copy2(Path("docs") / name, a.downloads / name)
    (root / "delivery.json").write_text(json.dumps(receipts, indent=2) + "\n")
    print(json.dumps(receipts, indent=2))


if __name__ == "__main__":
    main()
