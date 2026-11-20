"""Reserved QR13 physical executions through unchanged serial Rust QR12 authority."""

import argparse
import json
import resource
import shutil
import subprocess
import time
from pathlib import Path

from analysis.audit_0012 import stage
from analysis.collective_0012 import comparison
from analysis.dataset_0013 import TEST_SEEDS, extract_case, save, sha
from analysis.experiment_0005 import require
from analysis.experiment_0009 import csv_write, rows
from analysis.plan_0012 import condition


def freeze(root):
    root = Path(root)
    require(not (root / "freeze.json").exists(), "QR13 one immutable freeze")
    require(
        (root / "candidate-registry.json").exists() and (root / "latent-selection.json").exists(),
        "QR13 complete development freeze",
    )
    shutil.copy2("target/release/experiment_0012", root / "registered-runner")
    files = [
        *sorted((root / "models").iterdir()),
        *[
            root / n
            for n in (
                "inventory.json",
                "splits.json",
                "selection.json",
                "baselines.json",
                "training.json",
                "latent-models.json",
                "latent-selection.json",
                "candidate-registry.json",
            )
        ],
    ]
    save(
        root / "freeze.json",
        dict(
            files={str(p.relative_to(root)): sha(p) for p in files},
            created_before_new_physics=True,
            source_head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            compiler=subprocess.check_output(["rustc", "--version"], text=True).strip(),
            executable_sha256=sha(root / "registered-runner"),
            physics_source_sha256={str(p): sha(p) for p in sorted(Path("src").rglob("*.rs"))},
            forecast_physics=dict(
                trajectories=32,
                estimated_case_seconds=360,
                estimated_raw_bytes=4_000_000_000,
                ceiling_case_seconds=1800,
                ceiling_raw_bytes=10_000_000_000,
            ),
        ),
    )


def verify_freeze(root):
    root = Path(root)
    frozen = json.loads((root / "freeze.json").read_text())
    for name, digest in frozen["files"].items():
        require(sha(root / name) == digest, "QR13 sealed model/split/candidate")
    for name, digest in frozen["physics_source_sha256"].items():
        require(sha(name) == digest, "QR13 unchanged authoritative Rust")
    require(
        sha(root / "registered-runner") == frozen["executable_sha256"],
        "QR13 actual registered executable",
    )
    return frozen


def execute(root, historical):
    root = Path(root)
    verify_freeze(root)
    dest = root / "prospective"
    dest.mkdir()
    cases = [
        condition(f"s{seed}_{policy}_{grid}", grid, seed=seed, policy=policy, horizon=24)
        for seed in TEST_SEEDS
        for policy in ("FIXED", "ADAPTIVE")
        for grid in "PF"
    ]
    csv_write(dest / "plan.csv", cases)
    csv_write(dest / "initial-status.csv", [dict(case=r["case"], status="NOT RUN") for r in cases])
    (dest / "PREREQUISITE").write_text(str(Path(historical) / "a/gates.json") + "\n")
    require(
        json.loads((Path(historical) / "a/gates.json").read_text())["prerequisite_pass"],
        "QR13 physical prerequisite",
    )
    begun = time.perf_counter()
    result = subprocess.run(
        [str(root / "registered-runner"), "matrix", str(dest)], timeout=1800, check=False
    )
    ledger = rows(dest / "ledger.csv")
    seconds = sum(float(r["elapsed_seconds"]) for r in ledger)
    raw = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
    save(
        root / "physical-execution.json",
        dict(
            returncode=result.returncode,
            trajectories=len(ledger),
            case_seconds=seconds,
            wall_seconds=time.perf_counter() - begun,
            raw_bytes=raw,
            peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        ),
    )
    require(
        result.returncode == 0 and len(ledger) == 32 and seconds <= 1800 and raw <= 10_000_000_000,
        "QR13 actual physical/resource completion",
    )


def extract(root):
    root = Path(root)
    verify_freeze(root)
    folder = root / "prospective"
    physical = stage(folder)
    require(physical["valid"], "QR13 independent new physical audits")
    numerical = []
    for seed in TEST_SEEDS:
        for policy in ("FIXED", "ADAPTIVE"):
            numerical.append(
                comparison((folder / f"s{seed}_{policy}_P", folder / f"s{seed}_{policy}_F"))
            )
    csv_write(root / "prospective-numerical.csv", numerical)
    valid = {
        r["case"][:-2]: all(
            float(v)
            <= (0 if k in ("palette_positions_disagree", "event_pattern_disagree") else 0.1)
            for k, v in r.items()
            if k != "case"
        )
        for r in numerical
    }
    inv = []
    for row in rows(folder / "ledger.csv"):
        path = folder / row["case"]
        m = rows(path / "metadata.csv")[0]
        name = "QR13__" + row["case"]
        good = valid[row["case"][:-2]]
        item = dict(
            id=name,
            experiment="0013",
            metadata=m,
            seed=int(m["seed"]),
            family="seed:" + m["seed"],
            partition="prospective_test",
            physical_valid=True,
            numerical_valid=bool(good),
            protocol_valid=True,
            duplicate=False,
            model_eligible=bool(good),
            prediction_eligible=True,
            development_grid=m["n"] == "48",
            source=str(path),
            stream_sha256=sha(path / "observations.q12o"),
            source_archive="new QR13 raw; archive SHA added at final packaging",
            source_audit_sha256=sha(path / "audit.json"),
            ancestry="initial:QR13:" + m["seed"],
            checkpoints=[str(p) for p in path.glob("*.q12")],
            raw=json.loads((path / "audit.json").read_text())["raw"],
            diagnostic=False,
        )
        item["observations"] = extract_case(path, root / "data" / (name + ".npz"))
        item["data_sha256"] = sha(root / "data" / (name + ".npz"))
        inv.append(item)
    save(root / "prospective-inventory.json", inv)
    return inv


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("freeze", "execute", "extract"))
    p.add_argument("root", type=Path)
    p.add_argument("--historical", default="results/experiment_0012", type=Path)
    a = p.parse_args()
    if a.stage == "freeze":
        freeze(a.root)
    elif a.stage == "execute":
        execute(a.root, a.historical)
    else:
        extract(a.root)


if __name__ == "__main__":
    main()
