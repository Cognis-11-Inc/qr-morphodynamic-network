"""Portable QR13 raw/model audit, frozen re-evaluation and rebuilt-Rust repeat."""

import argparse
import json
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

import numpy as np

from analysis.audit_0012 import stage
from analysis.audit_0013 import audit_dataset, audit_predictions
from analysis.collective_0012 import comparison
from analysis.dataset_0013 import TEST_SEEDS, save, sha
from analysis.evaluate_0013 import evaluate, gates
from analysis.events_0013 import analyze
from analysis.experiment_0005 import require
from analysis.experiment_0009 import csv_write
from analysis.latent_0013 import evaluate as latent_evaluate
from analysis.latent_0013 import gates as latent_gates
from analysis.observability_0013 import review as observation_diagnostic
from analysis.plan_0012 import condition
from analysis.prospective_0013 import verify_freeze


def restore_ancestry():
    folder = Path("ancestry")
    if not folder.exists():
        require(
            Path("results/experiment_0012/a/FIXED_P/observations.q12o").exists(),
            "QR13 historical raw evidence available",
        )
        return
    for archive in sorted(folder.glob("*.zip")):
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                require(
                    not Path(name).is_absolute() and ".." not in Path(name).parts,
                    "QR13 safe ancestry member",
                )
                if name.startswith("results/experiment_0012/"):
                    z.extract(name, ".")


def verify_manifests(root):
    root = Path(root)
    if Path("source-integrity.json").exists():
        for name, digest in json.loads(Path("source-integrity.json").read_text())[
            "sources"
        ].items():
            require(sha(name) == digest, "QR13 delivery source SHA")
    if (root / "RAW_SHA256SUMS.txt").exists():
        for line in (root / "RAW_SHA256SUMS.txt").read_text().splitlines():
            digest, name = line.split("  ", 1)
            require(sha(name) == digest, "QR13 delivery artifact SHA")
    for name, digest in json.loads((root / "ancestry-integrity.json").read_text()).items():
        path = Path("ancestry") / name
        if not path.exists():
            path = Path("results/experiment_0012/packages") / name
        require(sha(path) == digest, "QR13 unchanged original scientific archive")


def repeat_rust(root):
    root = Path(root)
    dest = root / "rebuilt-replay"
    dest.mkdir()
    case = condition("s431_FIXED_P", "P", seed=431, policy="FIXED", horizon=24)
    csv_write(dest / "plan.csv", [case])
    (dest / "PREREQUISITE").write_text("results/experiment_0012/a/gates.json\n")
    started = time.perf_counter()
    subprocess.run(["target/release/experiment_0012", "matrix", str(dest)], check=True)
    reference = root / "prospective/s431_FIXED_P"
    actual = dest / "s431_FIXED_P"
    names = [
        "observations.q12o",
        "metrics.csv",
        "kicks.csv",
        "exchange.csv",
        "events.csv",
        "scores.csv",
    ] + [p.name for p in reference.glob("*.q12")]
    for name in names:
        require(
            sha(reference / name) == sha(actual / name), "QR13 rebuilt Rust exact replay " + name
        )
    return dict(
        actual_replayed_trajectories=1,
        independent_samples=0,
        case="s431_FIXED_P",
        byte_identical_files=names,
        seconds=time.perf_counter() - started,
        scope="separate reproducibility execution, not an added independent scientific case",
    )


def validate(root, replay_rust=True):
    root = Path(root)
    begun = time.perf_counter()
    verify_manifests(root)
    restore_ancestry()
    verify_freeze(root)
    dataset = audit_dataset(root)
    physical = stage(root / "prospective", True)
    require(physical["valid"], "QR13 fresh physical audits valid")
    numerical = [
        comparison((root / "prospective" / f"s{s}_{p}_P", root / "prospective" / f"s{s}_{p}_F"))
        for s in TEST_SEEDS
        for p in ("FIXED", "ADAPTIVE")
    ]
    old_numerical = (root / "prospective-numerical.csv").read_bytes()
    csv_write(root / "prospective-numerical.csv", numerical)
    require(
        (root / "prospective-numerical.csv").read_bytes() == old_numerical,
        "QR13 exact numerical ledger reconstruction",
    )
    old = {
        name: json.loads((root / name).read_text())
        for name in ("forecast-verdicts.json", "latent-verdicts.json")
    }
    predictions = {}
    for partition in ("retrospective_test", "prospective_test"):
        dest = root / ("predictions_" + partition)
        original = root / ("sealed_predictions_" + partition)
        require(not original.exists(), "QR13 preserve first prediction replay source")
        dest.rename(original)
        cost_path = root / (partition + "-evaluation.json")
        original_cost = cost_path.read_bytes()
        evaluate(root, partition, force=True)
        maximum = 0.0
        exact = True
        count = 0
        for path in sorted(original.glob("*.npz")):
            with np.load(path) as a, np.load(dest / path.name) as b:
                for key in a.files:
                    require(key in b.files, "QR13 prediction replay fields")
                    exact &= np.array_equal(a[key], b[key])
                    if a[key].size:
                        err = float(
                            np.linalg.norm(a[key] - b[key])
                            / max(float(np.linalg.norm(a[key])), 1e-30)
                        )
                        maximum = max(maximum, err)
                    require(
                        np.allclose(a[key], b[key], rtol=1e-6, atol=1e-12),
                        "QR13 quantified CPU prediction replay",
                    )
            count += 1
        predictions[partition] = dict(
            files=count, bitwise_numeric_equal=bool(exact), maximum_relative_l2=maximum
        )
        audit_predictions(root, partition)
        latent_evaluate(root, partition)
        # Keep sealed artifact bytes; discard only this validator's duplicate arrays.
        shutil.rmtree(dest)
        original.rename(dest)
        cost_path.write_bytes(original_cost)
    forecast = gates(root)
    latent = latent_gates(root)
    require(
        forecast == old["forecast-verdicts.json"] and latent == old["latent-verdicts.json"],
        "QR13 exact verdict/statistical reconstruction",
    )
    analyze(root)
    old_diagnostic = json.loads((root / "post-outcome-observability.json").read_text())
    observation_diagnostic(root)
    require(
        json.loads((root / "post-outcome-observability.json").read_text()) == old_diagnostic,
        "QR13 post-outcome observer diagnostic reconstruction",
    )
    result = dict(
        dataset=dataset["G1"],
        physical=physical,
        numerical_ledger_exact=True,
        frozen_verdicts_exact=True,
        prediction_replay=predictions,
        rebuilt_rust=repeat_rust(root) if replay_rust else None,
        seconds=time.perf_counter() - begun,
    )
    save(root / "portable-validation.json", result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--no-rust-repeat", action="store_true")
    a = p.parse_args()
    print(json.dumps(validate(a.root, not a.no_rust_repeat), indent=2))


if __name__ == "__main__":
    main()
