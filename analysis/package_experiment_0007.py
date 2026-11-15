"""Build viewer-free QR7 review/data/full-field ZIPs with member SHA manifests."""

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_zip(path, members, extra=None):
    manifest = []
    manifest_name = path.stem + "_SHA256SUMS.txt"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for source, name in sorted(members, key=lambda entry: entry[1]):
            archive.write(source, name)
            manifest.append(f"{sha(source)}  {name}\n")
        if extra:
            for name, content in extra.items():
                archive.writestr(name, content)
                manifest.append(f"{hashlib.sha256(content.encode()).hexdigest()}  {name}\n")
        archive.writestr(manifest_name, "".join(manifest))
    # CRC plus independently streamed member SHA for every archived member.
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        for line in archive.read(manifest_name).decode().splitlines():
            digest, name = line.split("  ", 1)
            with archive.open(name) as stream:
                assert hashlib.file_digest(stream, "sha256").hexdigest() == digest, name
    return dict(file=path.name, bytes=path.stat().st_size, sha256=sha(path), members=len(manifest))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--downloads", type=Path)
    parser.add_argument("--record-provenance", type=Path, metavar="EXECUTABLE")
    args = parser.parse_args()
    root = args.root
    if args.record_provenance:
        root.mkdir(parents=True, exist_ok=True)
        destination = root / "EXECUTION_PROVENANCE.json"
        if destination.exists():
            raise FileExistsError(destination)
        provenance = dict(
            executable_sha256=sha(args.record_provenance),
            source_head=subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
            toolchain=subprocess.check_output(["rustc", "-Vv"]).decode(),
            scope="recorded before execution; caller must use these executable bytes unchanged",
        )
        destination.write_text(json.dumps(provenance, indent=2) + "\n")
        return
    assert (root / "verification.json").exists()
    output = root / "packages"
    output.mkdir(exist_ok=True)
    tracked = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    sources = [
        Path(p)
        for p in tracked
        if p
        and (
            p.startswith(("src/", "analysis/"))
            or p
            in (
                "Cargo.toml",
                "Cargo.lock",
                "rust-toolchain.toml",
                "pyproject.toml",
                "requirements-dev.txt",
                "requirements-analysis.txt",
                "requirements-plots.txt",
                "README.md",
                "AGENTS.md",
                "PRINCIPLES.md",
                "HYPOTHESES.md",
                "EXPERIMENT_0007.md",
                "EXPERIMENT_0006.md",
            )
        )
    ]
    docs = [
        Path(p)
        for p in (
            "docs/EXPERIMENT_0007_RESULTS.md",
            "docs/OPERATIONAL_LATTICE_MANUAL.md",
            "docs/EXPERIMENT_0007_SCHEMA.md",
            "docs/EXPERIMENT_0007_PROTECTED_SHA256.txt",
        )
    ]
    docs += sorted(Path("docs/figures").glob("experiment_0007_*.png"))
    common = [(p, str(p)) for p in docs]
    common += [
        (p, "data/" + str(p.relative_to(root)))
        for name in ("tables", "palettes")
        for p in sorted((root / name).rglob("*"))
        if p.is_file()
    ]
    common += [
        (root / name, "data/" + name)
        for name in (
            "verification.json",
            "TRAINING_SHA256.txt",
            "EXECUTION_PROVENANCE.json",
            "protocol-verification.json",
            "local-checks.json",
            "numeric-review.json",
        )
    ]
    provenance = dict(
        head=subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
        registration="2cc0e00",
        implementation="d7f97f0",
        sources={str(p): sha(p) for p in sources},
        docs={str(p): sha(p) for p in docs},
    )
    (root / "source-integrity.json").write_text(json.dumps(provenance, indent=2) + "\n")
    common.append((root / "source-integrity.json", "source-integrity.json"))
    quick = list(common) + [(p, str(p)) for p in sources]
    reduced = []
    fields = []
    raw_hashes = []
    for name in ("train", "evaluate", "refine", "repeat", "derived", "audit"):
        for file in sorted((root / name).rglob("*")):
            if not file.is_file():
                continue
            relative = str(file.relative_to(root))
            raw_hashes.append(f"{sha(file)}  {relative}\n")
            if file.suffix == ".q7f":
                fields.append((file, "data/" + relative))
            else:
                reduced.append((file, "data/" + relative))
                if name not in ("derived", "audit") and (
                    file.suffix in (".csv", ".txt")
                    or file.name in ("COMPLETE", "RESET", "REUSED", "EQUIVALENT", "TRAINING_FROZEN")
                    or (file.suffix == ".f64" and file.stat().st_size <= 1920)
                ):
                    quick.append((file, "data/" + relative))
    (root / "RAW_SHA256SUMS.txt").write_text("".join(raw_hashes))
    common.append((root / "RAW_SHA256SUMS.txt", "RAW_SHA256SUMS.txt"))
    quick.append((root / "RAW_SHA256SUMS.txt", "RAW_SHA256SUMS.txt"))
    instructions = """# Experiment 0007 portable evidence

Start with docs/EXPERIMENT_0007_RESULTS.md and docs/OPERATIONAL_LATTICE_MANUAL.md.
All linked figures are included. No viewer, GPU or Bevy is required.
Each archive has its own named *_SHA256SUMS.txt binding every ZIP member.
RAW_SHA256SUMS.txt binds every original
trajectory/history/probe/field/derived audit input. Integrity is not authenticity.

QUICK_REVIEW contains every classification/metric/parameter/reset/reuse record,
all actual palettes in a content-addressed store, tables and original verification.
DATA additionally contains full history/eligibility/probe/signed output streams,
all reduced raw measurements, source snapshot, and independent Python verifier.
FULL_FIELDS contains every primary and repeat complete signed checkpoint.
Extract DATA and FULL_FIELDS into the same directory for full re-verification:

    python -m venv .venv
    .venv/bin/python -m pip install -r requirements-analysis.txt
    .venv/bin/python -m analysis.audit_experiment_0007 data
    .venv/bin/python -m analysis.protocol_experiment_0007 data

To reproduce the engine (CPU, deterministic serial, ~one hour): build with
`cargo build --locked --release --bin experiment_0007`, then run train, evaluate,
refine, repeat in that order in a NEW root. See README for exact commands.
Run `.venv/bin/python -m analysis.review_experiment_0007 data` for an independent
reproduction of classification and feature margins from QUICK_REVIEW. To force
fresh full-data verification, move data/audit aside before running the auditor.
After extracting DATA and FULL_FIELDS together, validate all original data with
`cd data; sha256sum -c ../RAW_SHA256SUMS.txt`. Each archive-specific member
manifest remains separate when both archives are extracted to one directory.
Reduced review cannot independently recompute whole-field energy/refinement;
that requires FULL_FIELDS. Stored verdicts are distinguished from remeasurement.
Frozen legacy scientific files are source dependencies, not new experiment data.
"""
    receipts = []
    receipts.append(
        write_zip(
            output / "QR_Neural_Memory_Experiment_0007_Quick_Review.zip",
            quick,
            {"PORTABLE_README.md": instructions},
        )
    )
    receipts.append(
        write_zip(
            output / "QR_Neural_Memory_Experiment_0007_Data.zip",
            common + reduced + [(p, str(p)) for p in sources],
            {"PORTABLE_README.md": instructions},
        )
    )
    receipts.append(
        write_zip(
            output / "QR_Neural_Memory_Experiment_0007_Full_Fields.zip",
            fields,
            {"PORTABLE_README.md": instructions},
        )
    )
    if args.downloads:
        args.downloads.mkdir(exist_ok=True)
        for receipt in receipts:
            source = output / receipt["file"]
            target = args.downloads / receipt["file"]
            shutil.copy2(source, target)
            assert sha(target) == receipt["sha256"]
        for doc in docs[:2]:
            shutil.copy2(doc, args.downloads / doc.name)
    (root / "delivery.json").write_text(json.dumps(receipts, indent=2) + "\n")
    print(json.dumps(receipts, indent=2))


if __name__ == "__main__":
    main()
