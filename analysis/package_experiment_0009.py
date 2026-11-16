"""Package QR9 measured standalone prerequisite and its gated-off neural ledger."""

import argparse
import json
import shutil
from pathlib import Path

from analysis.package_experiment_0007 import sha, source_metadata, write_zip

INSTRUCTIONS = """# Experiment 0009 portable standalone review

Read docs/EXPERIMENT_0009_RESULTS.md and EXPERIMENT_0009.md first.
The standalone prerequisite FAILED. No neural coupling/decoder was executed.
All445 conditional population cases are explicitly NOT_RUN in the ledger.

Extract QUICK_REVIEW and FULL_FIELDS together into one empty directory.
All tracked source, fixtures, historical specifications and figures are included.
No viewer or GPU is needed. Install the pinned dependencies in a new venv:

    python -m venv .venv
    .venv/bin/python -m pip install -r requirements-analysis.txt
    .venv/bin/python -m analysis.experiment_0009 data/standalone

The auditor independently remeasures all68 fields and580 frozen gates, including
the failures. A successful auditor process is NOT a scientific PASS. Read
data/standalone/verification.json. The compact review alone retains every-tick
metrics/probes and audit tables but cannot reconstruct omitted full fields.

Build/test the portable source:

    cargo build --locked --release --bin experiment_0009
    cargo test --locked --lib
    sha256sum -c docs/EXPERIMENT_0009_PROTECTED_SHA256.txt

For a fresh physics execution (NEVER overwrite archived data):

    target/release/experiment_0009 standalone my-new-standalone
    .venv/bin/python -m analysis.experiment_0009 my-new-standalone

Each ZIP has a separately named member SHA256 manifest, checked along with CRC
when packaged. Source-integrity.json records the delivery source commit and
every tracked source hash; data/provenance.json separately identifies the original
pre-execution code/compiler/executable. Integrity hashes are not authentication.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--downloads", type=Path)
    args = parser.parse_args()
    root = args.root
    verdict = json.loads((root / "standalone/verification.json").read_text())
    assert verdict["executions"] == 17
    paths, head = source_metadata()
    sources = [Path(p) for p in paths if p]
    integrity = dict(head=head, sources={str(p): sha(p) for p in sources})
    (root / "source-integrity.json").write_text(json.dumps(integrity, indent=2) + "\n")
    common = [(p, str(p)) for p in sources]
    common.append((root / "source-integrity.json", "source-integrity.json"))
    for name in ("provenance.json", "conditional_matrix_ledger.csv", "local-checks.json"):
        common.append((root / name, "data/" + name))
    reduced, fields, raw = [], [], []
    for path in sorted((root / "standalone").rglob("*")):
        if path.is_file():
            name = "data/" + str(path.relative_to(root))
            raw.append(f"{sha(path)}  {name}\n")
            (fields if path.suffix == ".q9a" else reduced).append((path, name))
    assert len(fields) == 68
    (root / "RAW_SHA256SUMS.txt").write_text("".join(raw))
    common.append((root / "RAW_SHA256SUMS.txt", "RAW_SHA256SUMS.txt"))
    output = root / "packages"
    output.mkdir(exist_ok=True)
    receipts = [
        write_zip(
            output / "QR_Neural_Memory_Experiment_0009_Quick_Review.zip",
            common + reduced,
            {"PORTABLE_README.md": INSTRUCTIONS},
        ),
        write_zip(
            output / "QR_Neural_Memory_Experiment_0009_Full_Fields.zip",
            fields,
            {"PORTABLE_README.md": INSTRUCTIONS},
        ),
    ]
    if args.downloads:
        args.downloads.mkdir(exist_ok=True)
        for receipt in receipts:
            target = args.downloads / receipt["file"]
            shutil.copy2(output / receipt["file"], target)
            assert sha(target) == receipt["sha256"]
        shutil.copy2(
            "docs/EXPERIMENT_0009_RESULTS.md", args.downloads / "EXPERIMENT_0009_RESULTS.md"
        )
    (root / "delivery.json").write_text(json.dumps(receipts, indent=2) + "\n")
    print(json.dumps(receipts, indent=2))


if __name__ == "__main__":
    main()
