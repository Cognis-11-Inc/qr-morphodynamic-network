"""Read-only QR13 observation extraction, provenance, family splits and alignment."""

import argparse
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path

import numpy as np

from analysis import io_0012 as io
from analysis.audit_0012 import node_energy
from analysis.experiment_0005 import fnv, require
from analysis.experiment_0009 import rows

TEST_SEEDS = (431, 433, 439, 443, 449, 457, 461, 463)
HORIZONS = (0.2, 1.0, 2.0)
TRACE = np.array([i * 135 + j for i in range(3) for j in range(6)])
METRICS = (
    "fluid",
    "neural",
    "loss",
    "force_work",
    "switch_work",
    "positive",
    "negative",
    "port_net",
    "cancellation",
)


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def partition(seed):
    if seed == 401:
        return "train"
    if seed == 409:
        return "validation"
    if seed in (419, 427):
        return "retrospective_test"
    require(seed in TEST_SEEDS, "QR13 reserved physical seed")
    return "prospective_test"


def extract_case(folder, target):
    """Preserve actual observations; no fitting, smoothing or future features."""
    folder = Path(folder)
    s = io.stream(folder)
    a = s["frames"]
    for i, frame in enumerate(a):
        require(int(frame["tick"]) == s["start"] + i, "QR13 exact tick order")
        require(fnv(frame.tobytes()[:-8]) == int(frame["checksum"]), "QR13 frame integrity")
    stride = round(0.2 / s["dt"])
    require(abs(stride * s["dt"] - 0.2) < 1e-14, "QR13 physical cadence")
    nodes = a[::stride]["nodes"]
    io.valid(nodes) if not s["oracle"] else io.old.valid_nodes(nodes)
    t = a[::stride]["tick"].astype(float) * s["dt"]
    require(np.all(np.diff(t) > 0), "QR13 strictly increasing observation time")
    metrics = rows(folder / "metrics.csv")[::stride]
    require(len(metrics) == len(t), "QR13 metrics/frame alignment")
    require(
        np.allclose([float(r["time"]) for r in metrics], t, rtol=0, atol=1e-13),
        "QR13 exact physical time",
    )
    scalar = bool(int(rows(folder / "metadata.csv")[0]["scalar"]))
    energy = np.array([[node_energy(n, scalar) for n in frame] for frame in nodes])
    accounted = np.array([[float(r[f"e{i}"]) for i in range(s["count"])] for r in metrics])
    require(
        np.allclose(energy, accounted, rtol=1e-12, atol=1e-25),
        "QR13 independently reconstructed node energies",
    )
    controller = np.zeros((*nodes.shape, 4))
    if not s["oracle"]:
        controller[..., :3] = np.stack([nodes[k] for k in ("latch", "events", "attempts")], axis=-1)
        controller[..., 3] = (nodes["age"] - nodes["last"]) * s["dt"]
    values = dict(
        time=t,
        ticks=a[::stride]["tick"],
        u=nodes["u"],
        v=nodes["v"],
        packet=nodes["packet"],
        z=nodes["z"],
        palette=nodes["palette"],
        controller=controller,
        energy=energy,
        global_metrics=np.array([[float(r[k]) for k in METRICS] for r in metrics]),
    )
    require(
        all(np.isfinite(v).all() for v in values.values()), "QR13 finite extracted observations"
    )
    np.savez_compressed(target, **values)
    return len(t)


def inventory(historical, root):
    historical, root = Path(historical), Path(root)
    require(not (root / "inventory.json").exists(), "QR13 immutable extraction destination")
    (root / "data").mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    receipts = json.loads((historical / "delivery.json").read_text())
    for r in receipts:
        require(
            sha(historical / "packages" / r["file"]) == r["sha256"], "QR13 original archive SHA"
        )
    prior = json.loads((historical / "archive-validation.json").read_text())
    require(
        prior["fresh_independent_scientific_audit"],
        "QR13 historical independent reconstruction receipt",
    )
    numerical = {
        r["case"][:-2]: all(
            float(v)
            <= (0 if k in ("palette_positions_disagree", "event_pattern_disagree") else 0.1)
            for k, v in r.items()
            if k != "case"
        )
        for r in rows(historical / "collective-numerical.csv")
    }
    ledger = rows(historical / "EXECUTION_LEDGER.csv")
    result, seen = [], set()
    for row in ledger:
        folder = historical / row["stage"] / row["case"]
        m = rows(folder / "metadata.csv")[0]
        s = io.stream(folder)
        seed = int(m["seed"])
        protocol = row["condition_status"] != "PROTOCOL_INVALID"
        valid = numerical.get(row["case"][:-2], True) if row["stage"] == "d" else True
        audit = json.loads((folder / "audit.json").read_text())
        require(audit["valid"], "QR13 historical mechanical audit")
        for name, digest in audit["raw"].items():
            require(sha(folder / name) == digest, "QR13 raw binding to audited physical execution")
        name = row["stage"] + "__" + row["case"]
        stream_name = "observations.q11o" if s["oracle"] else "observations.q12o"
        digest = sha(folder / stream_name)
        duplicate = (seed, digest) in seen
        seen.add((seed, digest))
        usable = (
            protocol
            and valid
            and not duplicate
            and s["count"] == 4
            and not int(m["scalar"])
            and not s["oracle"]
        )
        item = dict(
            id=name,
            experiment="0012",
            metadata=m,
            seed=seed,
            family=f"seed:{seed}",
            partition=partition(seed),
            physical_valid=bool(audit["valid"]),
            numerical_valid=bool(valid),
            protocol_valid=protocol,
            duplicate=duplicate,
            model_eligible=usable,
            development_grid=m["n"] == "48" and m["dt"] == "0.05",
            source=str(folder),
            stream_sha256=digest,
            source_archive=receipts[1],
            source_audit_sha256=sha(folder / "audit.json"),
            ancestry=m["checkpoint"] or f"initial:QR12:{seed}",
            checkpoints=[
                str(p.relative_to(historical.parent.parent)) for p in sorted(folder.glob("*.q12"))
            ],
            raw=audit["raw"],
            diagnostic=row["stage"] == "diagnostic_nonadaptive",
        )
        item["observations"] = extract_case(folder, root / "data" / (name + ".npz"))
        item["data_sha256"] = sha(root / "data" / (name + ".npz"))
        result.append(item)
        print("QR13 extracted", name, "eligible", usable, flush=True)
    require(
        len(result) == 82 and sum(not r["protocol_valid"] for r in result) == 2,
        "QR13 complete historical coverage",
    )
    save(root / "inventory.json", result)
    save(
        root / "splits.json",
        dict(
            rule="complete physical seed families including repeats/refinements/branches",
            train=[401],
            validation=[409],
            retrospective_test=[419, 427],
            prospective_test=list(TEST_SEEDS),
            independent_units="seed families, not observations",
            historical_outcomes_known=True,
        ),
    )
    save(
        root / "extraction.json",
        dict(
            seconds=time.perf_counter() - started,
            executions=len(result),
            archives=receipts,
            source_head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            python=platform.python_version(),
        ),
    )
    return result


def arrays(root, record, observer="global", morphology=True):
    """History and target alignment; only actual past/current state forms inputs."""
    with np.load(Path(root) / "data" / (record["id"] + ".npz")) as a:
        if a["u"].shape[1] != 4:
            raise ValueError("QR13 model requires four genuine nodes")
        target = np.concatenate(
            (a["u"], a["v"], a["packet"][..., :1], a["energy"][..., None]), axis=-1
        )
        base = np.concatenate(
            (
                a["u"],
                a["v"],
                a["packet"],
                a["energy"][..., None],
                a["z"][..., TRACE],
                a["controller"],
                np.broadcast_to(a["time"][:, None, None], (len(a["time"]), 4, 1)),
            ),
            axis=-1,
        )
        origins = np.arange(2, len(target) - 10)
        history = origins[:, None] + np.array((-2, -1, 0))
        y = np.stack([target[origins + h] for h in (1, 5, 10)], axis=1)
        current = target[origins]
        pal = np.eye(5)[a["palette"][origins]].reshape(len(origins), 4, 320)
        event = np.stack(
            [
                np.any(a["controller"][origins + h, :, 1] != a["controller"][origins, :, 1], axis=1)
                for h in (1, 5, 10)
            ],
            axis=1,
        )
        # A crossing is opportunity crossing, even if veto/abstention: eval only.
        times = a["time"][origins]
        crossing = np.array(
            [[any(t < e <= t + h + 1e-12 for e in (16, 24, 32)) for h in HORIZONS] for t in times]
        )
        x = base[history]
        if observer == "global":
            globals_ = a["global_metrics"][history]
            kind = record["metadata"]["forcing"]
            force = np.broadcast_to(
                np.array(
                    [kind == k for k in ("PULSE", "COMMON", "QUIET", "SUSTAINED_FIXED")], float
                ),
                (*history.shape, 4),
            )
            x = np.concatenate((x.reshape(len(x), 3, -1), globals_, force), axis=-1)
            palette = pal.reshape(len(pal), -1)
            y, current = y.reshape(len(y), 3, -1), current.reshape(len(current), -1)
            node = np.full(len(x), -1)
        else:
            x = x.transpose(0, 2, 1, 3).reshape(-1, 3, base.shape[-1])
            palette = pal.reshape(-1, 320)
            y = y.transpose(0, 2, 1, 3).reshape(-1, 3, 130)
            current = current.reshape(-1, 130)
            times, crossing, event = (
                np.repeat(times, 4),
                np.repeat(crossing, 4, axis=0),
                np.repeat(event, 4, axis=0),
            )
            node = np.tile(np.arange(4), len(origins))
        if not morphology:
            palette = palette[:, :0]
        return dict(
            x=x.astype(np.float32),
            palette=palette.astype(np.float32),
            y=y.astype(np.float64),
            current=current.astype(np.float64),
            time=times,
            crossing=crossing,
            accepted=event,
            node=node,
        )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("historical", type=Path)
    p.add_argument("root", type=Path)
    a = p.parse_args()
    inventory(a.historical, a.root)


if __name__ == "__main__":
    main()
