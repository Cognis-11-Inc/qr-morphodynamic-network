"""Build and independently integrity-check viewer-free QR8 evidence archives."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from analysis.package_experiment_0007 import sha, source_metadata, write_zip

INSTRUCTIONS = """# Experiment 0008 portable review

Read docs/EXPERIMENT_0008_RESULTS.md and the frozen registration. Figures resolve
locally. No viewer or GPU is needed. All source files, embedded legacy Markdown,
registered geometry JSON, test fixtures and source-integrity.json are included.
Each archive has its own named *_SHA256SUMS.txt; integrity is not authenticity.

QUICK_REVIEW contains every numeric feature, frozen reference template, prediction,
margin, global mechanical diagnostic, source and verification receipt. It can
independently reproduce the numerical classifier and feature margins, while stored
physical gates require the full dataset for remeasurement.
DATA adds complete original region/probe streams and audit inputs. FULL_FIELDS
contains all582 actual complete signed/energy checkpoints. Extract DATA and
FULL_FIELDS together into one directory, then run:

    python -m venv .venv
    .venv/bin/python -m pip install -r requirements-analysis.txt
    .venv/bin/python -m analysis.experiment_0008 data review
    .venv/bin/python -m analysis.audit_experiment_0008 data --fresh

From QUICK_REVIEW, the first command reproduces all404 references/readouts without
full fields. To validate original data checksums: cd data and run
`sha256sum -c ../RAW_SHA256SUMS.txt` after extracting both companion archives.
The independent auditor reconstructs energy/rules/regions from actual fields;
checksum checks alone do not establish physical or information verdicts.

To reproduce physics, build `cargo build --locked --release --bin experiment_0008`.
Run train in a NEW root; run auditor --follow in another terminal; run Python fit
only after train is complete/audited, then evaluate/refine/repeat. See README.
Fresh repeated runs are never overwrites or relabelled aliases. No palette learns.
"""


def verify_existing(path, expected):
    import zipfile

    name = path.stem + "_SHA256SUMS.txt"
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        actual = {}
        for line in archive.read(name).decode().splitlines():
            digest, member = line.split("  ", 1)
            with archive.open(member) as stream:
                assert hashlib.file_digest(stream, "sha256").hexdigest() == digest
            actual[member] = digest
        assert actual == expected
    return dict(file=path.name, bytes=path.stat().st_size, sha256=sha(path), members=len(expected))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--downloads", type=Path)
    parser.add_argument("--reuse-full-fields", action="store_true")
    args = parser.parse_args()
    root = args.root
    assert (root / "verification.json").exists()
    output = root / "packages"
    output.mkdir(exist_ok=True)
    tracked, head = source_metadata()
    sources = [Path(p) for p in tracked if p]
    manifests = dict(
        head=head,
        registration="8e74e54",
        implementation="325fe77",
        sources={str(p): sha(p) for p in sources},
    )
    (root / "source-integrity.json").write_text(json.dumps(manifests, indent=2) + "\n")
    common = [(p, str(p)) for p in sources]
    for name in ("tables", "features", "models"):
        common.extend(
            (p, "data/" + str(p.relative_to(root)))
            for p in sorted((root / name).rglob("*"))
            if p.is_file()
        )
    for name in (
        "verification.json",
        "regions.json",
        "EXECUTION_PROVENANCE.json",
        "local-checks.json",
    ):
        if (root / name).exists():
            common.append((root / name, "data/" + name))
    common.append((root / "source-integrity.json", "source-integrity.json"))
    reduced = []
    quick = []
    fields = []
    raw = []
    for stage in ("train", "evaluate", "refine", "repeat", "audit"):
        for p in sorted((root / stage).rglob("*")):
            if not p.is_file():
                continue
            relative = str(p.relative_to(root))
            raw.append(f"{sha(p)}  {relative}\n")
            if p.suffix == ".q8f":
                fields.append((p, "data/" + relative))
            else:
                reduced.append((p, "data/" + relative))
                if stage != "audit" and p.suffix not in (".q8r", ".q8p"):
                    quick.append((p, "data/" + relative))
    (root / "RAW_SHA256SUMS.txt").write_text("".join(raw))
    common.append((root / "RAW_SHA256SUMS.txt", "RAW_SHA256SUMS.txt"))
    extra = {"PORTABLE_README.md": INSTRUCTIONS}
    receipts = [
        write_zip(
            output / "QR_Neural_Memory_Experiment_0008_Quick_Review.zip", common + quick, extra
        ),
        write_zip(output / "QR_Neural_Memory_Experiment_0008_Data.zip", common + reduced, extra),
    ]
    full = output / "QR_Neural_Memory_Experiment_0008_Full_Fields.zip"
    if args.reuse_full_fields:
        expected = {name: sha(path) for path, name in fields}
        expected["PORTABLE_README.md"] = hashlib.sha256(INSTRUCTIONS.encode()).hexdigest()
        receipts.append(verify_existing(full, expected))
    else:
        receipts.append(write_zip(full, fields, extra))
    if args.downloads:
        args.downloads.mkdir(exist_ok=True)
        for receipt in receipts:
            source = output / receipt["file"]
            target = args.downloads / receipt["file"]
            shutil.copy2(source, target)
            assert sha(target) == receipt["sha256"]
        shutil.copy2(
            "docs/EXPERIMENT_0008_RESULTS.md", args.downloads / "EXPERIMENT_0008_RESULTS.md"
        )
    (root / "delivery.json").write_text(json.dumps(receipts, indent=2) + "\n")
    print(json.dumps(receipts, indent=2))


if __name__ == "__main__":
    main()
