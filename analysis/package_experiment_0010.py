"""Package QR10 source, complete observations, integrity and portable review."""

import argparse
import json
import shutil
from pathlib import Path

from analysis.experiment_0009 import csv_write, rows
from analysis.package_experiment_0007 import sha, source_metadata, write_zip

README = """# Experiment 0010 portable review

Read docs/EXPERIMENT_0010_RESULTS.md and EXPERIMENT_0010.md first.
Historical QR9 remains FAIL. No overall QR10 success score.
Extract Quick_Review and Full_Fields together in an empty folder.
Source is included; observations are under data/, large signed fields separately.
Install requirements-analysis.txt and requirements-plot.txt in a fresh venv.
No GPU, Bevy or native viewer required.

    python -m analysis.experiment_0010 data/numerical

A successful audit process is not a scientific PASS: inspect verification.json,
category gates, pilot evidence and NOT RUN dependencies. Coupling, if present:

    python -m analysis.audit_coupling_0010 data/pilot
    python -m analysis.audit_coupling_0010 data/extended/train --extended
    python -m analysis.audit_coupling_0010 data/extended/evaluate --extended
    python -m analysis.communication_0010 review data/extended
    python -m analysis.audit_coupling_0010 data/extended/interference --extended
    python -m analysis.communication_0010 interference data/extended

The Quick_Review alone can reproduce held-out numeric predictions from remote
histories and frozen means, but full independent field/energy verification needs
both archives. Source-freeze tarballs preserve the exact original registration,
engine and decoder versions; final source-integrity.json identifies delivery.
Do not call fit against archived frozen templates: it correctly refuses a refit.

Fresh extended execution follows independently passed pilot:

    target/release/coupling_0010 train NEW_EXTENDED PASSED_PILOT
    python -m analysis.audit_coupling_0010 NEW_EXTENDED/train --extended
    python -m analysis.communication_0010 fit NEW_EXTENDED
    target/release/coupling_0010 evaluate NEW_EXTENDED PASSED_PILOT
    python -m analysis.audit_coupling_0010 NEW_EXTENDED/evaluate --extended
    python -m analysis.communication_0010 review NEW_EXTENDED
    target/release/coupling_0010 interference NEW_EXTENDED PASSED_PILOT
    python -m analysis.audit_coupling_0010 NEW_EXTENDED/interference --extended
    python -m analysis.communication_0010 interference NEW_EXTENDED

Fresh fitting expects sibling pilot/ and extended/ layout as in this archive.

To rebuild: cargo build --locked --release --bin experiment_0010
To rerun fresh: target/release/experiment_0010 standalone NEW_DIRECTORY
Never overwrite archived evidence or refit held-out outcomes.
Raw/source SHA256 manifests plus per-archive member SHA and CRC are checked during
packaging. provenance.json identifies original pre-execution sources/executable;
source-integrity.json identifies delivery source. Integrity is not authentication.
"""


def execution_receipt(root):
    ledger = []
    for stage, provenance_name in (
        ("numerical", "provenance.json"),
        ("pilot", "pilot-provenance.json"),
        ("extended/train", "extended-provenance.json"),
        ("extended/evaluate", "extended-provenance.json"),
        ("extended/interference", "extended-provenance.json"),
    ):
        provenance = json.loads((root / provenance_name).read_text())
        assert (root / stage / "COMPLETE").exists(), stage
        for entry in rows(root / stage / "ledger.csv"):
            ledger.append(
                dict(
                    stage=stage,
                    case=entry["case"],
                    status=entry["status"],
                    kind="EXECUTED",
                    elapsed_seconds=entry["elapsed_seconds"],
                    source_head=provenance["head"],
                    executable_sha256=provenance["executable_sha256"],
                    raw_dir=f"{stage}/{entry['case']}",
                )
            )
    assert len(ledger) == 159 and all(r["status"] == "COMPLETE" for r in ledger)
    elapsed = sum(float(r["elapsed_seconds"]) for r in ledger)
    raw_bytes = sum(
        p.stat().st_size for r in ledger for p in (root / r["raw_dir"]).rglob("*") if p.is_file()
    )
    actual_fields = sum(1 for r in ledger for _ in (root / r["raw_dir"]).glob("*.q10"))
    actual_neurons = sum(1 for r in ledger for _ in (root / r["raw_dir"]).glob("*.neuron.csv"))
    assert actual_fields == 503 and actual_neurons == 399
    assert elapsed <= 1800 and raw_bytes <= 8_000_000_000, "registered resource budget"
    for entry in rows(root / "extended/reuses.csv"):
        provenance = json.loads((root / "pilot-provenance.json").read_text())
        ledger.append(
            dict(
                stage="extended/train",
                case=entry["case"],
                status="REUSED",
                kind="REUSED",
                elapsed_seconds="0",
                source_head=provenance["head"],
                executable_sha256=provenance["executable_sha256"],
                raw_dir="pilot/" + entry["case"],
            )
        )
    assert len(ledger) == 161
    csv_write(root / "EXECUTION_LEDGER.csv", ledger)
    receipt = dict(
        schema=1,
        actual_executions=159,
        explicit_reuses=2,
        full_fluid_checkpoints=actual_fields,
        full_neural_checkpoints=actual_neurons,
        case_wall_seconds=elapsed,
        raw_case_bytes=raw_bytes,
        physics_wall_budget_seconds=1800,
        raw_budget_bytes=8_000_000_000,
        no_overall_scientific_score=True,
    )
    (root / "EXECUTION_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--downloads", type=Path)
    args = parser.parse_args()
    root = args.root
    execution_receipt(root)
    paths, head = source_metadata()
    sources = [Path(p) for p in paths if p]
    integrity = dict(head=head, sources={str(p): sha(p) for p in sources})
    (root / "source-integrity.json").write_text(json.dumps(integrity, indent=2) + "\n")
    reduced, fields, manifest = [], [], []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if (
            not path.is_file()
            or "packages" in relative.parts
            or path.name
            in (
                "source-integrity.json",
                "delivery.json",
                "RAW_SHA256SUMS.txt",
            )
        ):
            continue
        name = "data/" + str(relative)
        manifest.append(f"{sha(path)}  {name}\n")
        (
            fields
            if path.suffix == ".q10"
            or path.name.endswith(".neuron.csv")
            or path.name in ("registered-runner", "coupled-runner", "extended-runner")
            else reduced
        ).append((path, name))
    (root / "RAW_SHA256SUMS.txt").write_text("".join(manifest))
    common = [(p, str(p)) for p in sources] + [
        (root / "source-integrity.json", "source-integrity.json"),
        (root / "RAW_SHA256SUMS.txt", "RAW_SHA256SUMS.txt"),
    ]
    output = root / "packages"
    output.mkdir(exist_ok=True)
    receipts = [
        write_zip(
            output / "QR_Neural_Memory_Experiment_0010_Quick_Review.zip",
            common + reduced,
            {"PORTABLE_README.md": README},
        ),
        write_zip(
            output / "QR_Neural_Memory_Experiment_0010_Full_Fields.zip",
            fields,
            {"PORTABLE_README.md": README},
        ),
    ]
    if args.downloads:
        args.downloads.mkdir(exist_ok=True)
        for receipt in receipts:
            target = args.downloads / receipt["file"]
            shutil.copy2(output / receipt["file"], target)
            assert sha(target) == receipt["sha256"]
        shutil.copy2(
            "docs/EXPERIMENT_0010_RESULTS.md", args.downloads / "EXPERIMENT_0010_RESULTS.md"
        )
    (root / "delivery.json").write_text(json.dumps(receipts, indent=2) + "\n")
    print(json.dumps(receipts, indent=2))


if __name__ == "__main__":
    main()
