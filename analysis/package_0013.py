"""Portable QR13 source/models/observations and immutable QR12 ancestry archives."""

import argparse
import hashlib
import json
import os
import shutil
import zipfile
from pathlib import Path

from analysis.dataset_0013 import save, sha
from analysis.experiment_0005 import require
from analysis.package_experiment_0007 import source_metadata

INSTRUCTIONS = """# QR Morphodynamic Network — Experiment0013

Read EXPERIMENT_0013.md, docs/EXPERIMENT_0013_RESULTS.md, the exploitation report,
and CODEX_INDEPENDENT_PROPOSAL. There is no global success score. PyTorch is an
external instrument, never the physical authority. Preserve original failures,
invalid controls, reserved-family classifications and rejected candidate registry.

Extract BOTH archives into ONE empty directory. Full Evidence contains the original
unchanged QR12 archives under ancestry/; validation selectively restores only their
results/experiment_0012 paths, never overwrites current Rust/Python source. Original
registrations/results remain unchanged. Quick Review alone supports compact/model
inspection, not full raw-physics verification. Full fields are sparse, not dense.

Create a CPU environment (Python3.13 was used for original execution):

    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements-dev.txt -r requirements-analysis.txt
    .venv/bin/python -m pip install -r requirements-plot.txt -r requirements-learn.txt
    cargo test --locked --all-targets --all-features
    cargo build --locked --release --bin experiment_0012
    .venv/bin/python -m ruff check analysis
    .venv/bin/python -W error -m unittest discover -s analysis -t . -v
    export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
    .venv/bin/python -m analysis.validate_0013 results/experiment_0013

Validation verifies source/raw/archive SHA, restores original ancestry, checks all
114 compact/raw origins, independently audits all32 new cases and numerical pairs,
re-executes every sealed held-out forecast and latent evaluation without refitting,
reconstructs all statistical verdicts, and runs ONE separately labelled rebuilt-Rust
P-grid repeat against actual raw bytes. That repeat is not an independent sample.
Original test outcomes remain sealed; a replay never trains on them. Observe limits
on nondeterminism; do not silently modify thresholds if another platform differs.

Models/training/checkpoint hashes, all historical/prospective condition metrics,
per-window predictions, every invalid/failure/rejection and source-freeze archives
are retained. Training can be reproduced in a DIFFERENT root using only registered
TRAIN/VALIDATION families; do not invoke training over the sealed final directory.
Original source/executable commits distinguish physics, fitting, selection and
final reporting. No GPU, native viewer, memory/learning or new-law claim follows.

ZIP/member/raw SHA manifests bind integrity, not external authenticity. Final
archive/fresh-rebuild/push/hosted-CI receipts are separate sidecars created after
sealing; absence means pending verification, not a scientific success.
"""


def write_archive(path, members):
    manifest = []
    with zipfile.ZipFile(
        path, "w", zipfile.ZIP_DEFLATED, compresslevel=3, allowZip64=True
    ) as archive:
        for source, name in sorted(members, key=lambda pair: pair[1]):
            archive.write(
                source,
                name,
                compress_type=zipfile.ZIP_STORED
                if source.suffix in (".zip", ".gz", ".npz")
                else zipfile.ZIP_DEFLATED,
            )
            manifest.append(f"{sha(source)}  {name}\n")
        archive.writestr("PORTABLE_README.md", INSTRUCTIONS)
        manifest.append(
            f"{hashlib.sha256(INSTRUCTIONS.encode()).hexdigest()}  PORTABLE_README.md\n"
        )
        archive.writestr(path.stem + "_SHA256SUMS.txt", "".join(manifest))
    with zipfile.ZipFile(path) as archive:
        require(archive.testzip() is None, "QR13 archive CRC")
        for line in manifest:
            digest, name = line.rstrip("\n").split("  ", 1)
            with archive.open(name) as stream:
                require(
                    hashlib.file_digest(stream, "sha256").hexdigest() == digest,
                    "QR13 member SHA " + name,
                )
    return dict(file=path.name, bytes=path.stat().st_size, sha256=sha(path), members=len(manifest))


def package(root, downloads=None):
    root = Path(root)
    require(not root.is_absolute(), "QR13 project-relative archive paths")
    files, head = source_metadata()
    sources = [Path(name) for name in files if name]
    integrity = dict(head=head, sources={str(p): sha(p) for p in sources})
    save(root / "source-integrity.json", integrity)
    old = Path("results/experiment_0012")
    ancestry = json.loads((old / "delivery.json").read_text())
    save(root / "ancestry-integrity.json", {r["file"]: r["sha256"] for r in ancestry})
    small = []
    full = []
    raw = []
    excludes = {
        "delivery.json",
        "source-integrity.json",
        "RAW_SHA256SUMS.txt",
        "package.log",
        "delivery-status.json",
        "archive-validation.json",
        "hosted-ci.json",
    }
    for p in sorted(root.rglob("*")):
        if not p.is_file() or "packages" in p.relative_to(root).parts or p.name in excludes:
            continue
        parts = p.relative_to(root).parts
        raw.append(f"{sha(p)}  {p}\n")
        large = (
            parts[0].startswith("predictions_")
            or p.name == "registered-runner"
            or (parts[0] == "prospective" and p.suffix in (".q12", ".q12o"))
            or (
                parts[0] == "prospective"
                and p.name in ("kicks.csv", "exchange.csv", "audit-gates.csv", "audit.json")
            )
        )
        (full if large else small).append((p, str(p)))
    (root / "RAW_SHA256SUMS.txt").write_text("".join(raw))
    common = [(p, str(p)) for p in sources] + [
        (root / "source-integrity.json", "source-integrity.json"),
        (root / "RAW_SHA256SUMS.txt", str(root / "RAW_SHA256SUMS.txt")),
    ]
    full += [(old / "packages" / r["file"], "ancestry/" + r["file"]) for r in ancestry]
    dest = root / "packages"
    dest.mkdir(exist_ok=True)
    receipts = [
        write_archive(
            dest / "QR_Morphodynamic_Network_Experiment_0013_Quick_Review.zip", common + small
        ),
        write_archive(
            dest / "QR_Morphodynamic_Network_Experiment_0013_Full_Evidence_Reproducibility.zip",
            full,
        ),
    ]
    save(root / "delivery.json", receipts)
    inventory = json.loads((root / "inventory.json").read_text())
    inventory += json.loads((root / "prospective-inventory.json").read_text())
    lineage = dict(
        archives=receipts,
        historical_archives=ancestry,
        sample_archive_binding=[
            dict(
                id=r["id"],
                archives=ancestry if r["experiment"] == "0012" else receipts,
                stream_sha256=r["stream_sha256"],
                data_sha256=r["data_sha256"],
            )
            for r in inventory
        ],
        scope="External sidecar avoids a self-referential archive hash.",
    )
    save(root / "archive-lineage.json", lineage)
    if downloads:
        downloads = Path(downloads)
        downloads.mkdir(exist_ok=True)
        for r in receipts:
            source = dest / r["file"]
            target = downloads / r["file"]
            require(not target.exists(), "QR13 no overwrite of existing delivery archive")
            # Same filesystem: preserve storage ceiling while exposing normal Download files.
            os.link(source, target)
            require(sha(target) == r["sha256"], "QR13 downloadable archive bytes")
        save(downloads / "QR_Morphodynamic_Network_Experiment_0013_Archive_Lineage.json", lineage)
        for name in (
            "EXPERIMENT_0013_RESULTS.md",
            "EXPERIMENT_0013_EXPLOITATION.md",
            "EXPERIMENT_0013_CODEX_INDEPENDENT_PROPOSAL.md",
        ):
            shutil.copy2(Path("docs") / name, downloads / name)
        (downloads / "QR_Morphodynamic_Network_Experiment_0013_SHA256SUMS.txt").write_text(
            "".join(f"{r['sha256']}  {r['file']}\n" for r in receipts)
        )
    return receipts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--downloads", type=Path)
    a = p.parse_args()
    print(json.dumps(package(a.root, a.downloads), indent=2))


if __name__ == "__main__":
    main()
