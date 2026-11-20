"""Separate eligibility, acceptance and switching-work oracles before event consequences."""

import argparse
import json
import struct
from pathlib import Path

import numpy as np

from analysis import io_0012
from analysis.audit_0012 import node_energy, proposal
from analysis.experiment_0005 import require
from analysis.experiment_0009 import csv_write, rows


def owned(path):
    with Path(path).open("rb") as f:
        header = f.read(80)
    require(header[:8] == b"QR12FUL1", "QR13 complete pre-event source")
    _, n, _, _, _, count, _, _, _ = struct.unpack_from("<3Qd5Q", header, 8)
    return np.memmap(
        path, dtype=io_0012.NODE, mode="r", offset=80 + 24 * count + 32 * n**3, shape=(count,)
    ).copy()


def analyze(root):
    root = Path(root)
    inventory = json.loads((root / "inventory.json").read_text())
    if (root / "prospective-inventory.json").exists():
        inventory += json.loads((root / "prospective-inventory.json").read_text())
    result = []
    for case in inventory:
        if not (case["model_eligible"] or case.get("prediction_eligible", False)):
            continue
        folder = Path(case["source"])
        s = io_0012.stream(folder)
        m = case["metadata"]
        frames = s["frames"]
        cache = {}
        for e in rows(folder / "events.csv"):
            tick, node = int(e["tick"]), int(e["neuron"])
            if tick not in cache:
                path = folder / f"pre-{tick:06}.q12"
                if path.exists():
                    cache[tick] = owned(path)
                elif tick == s["start"] and (folder / "branch-before.q12").exists():
                    cache[tick] = owned(folder / "branch-before.q12")
                else:
                    require(e["accepted"] == "0", "QR13 accepted event needs real pre-event state")
                    cache[tick] = frames[tick - s["start"]]["nodes"].copy()
            pre = cache[tick][node].copy()
            h = pre["z"][277:341].max()
            latch = h >= 0.02 or (h >= 0.005 and bool(pre["latch"]))
            local = (
                proposal(pre, latch, int(pre["last"]), s["dt"]) if int(pre["budget"]) < 3 else None
            )
            pair = local
            if e["cause"] == "EXTERNAL":
                p = pre["palette"]
                pair = next(
                    (
                        (i, j)
                        for i in range(64)
                        for j in range(i + 1, 64)
                        if abs(i // 8 - j // 8) + abs(i % 8 - j % 8) == 1 and p[i] != p[j]
                    ),
                    None,
                )
            actual = None if int(e["a"]) < 0 else (int(e["a"]), int(e["b"]))
            require(pair == actual, "QR13 event eligibility predicted by known local rule")
            permitted = (
                m["policy"] in ("ADAPTIVE", "NONADAPTIVE", "TRACE_OFF") and s["start"] == 0
            ) or (
                m["policy"] in ("PERMIT", "ISOLATED_PERMIT", "EXTERNAL")
                and tick == s["start"]
                and node == 0
            )
            expected = pair is not None and int(pre["budget"]) < 3 and permitted
            require(
                expected == bool(int(e["accepted"])),
                "QR13 event occurrence apparatus permission baseline",
            )
            predicted_work = 0.0
            if expected:
                before = node_energy(pre)
                post = pre.copy()
                post["palette"][list(pair)] = post["palette"][list(pair[::-1])]
                predicted_work = node_energy(post) - before
            actual_work = float(e["work"])
            require(
                abs(predicted_work - actual_work) <= 1e-12 * max(node_energy(pre), 1e-30),
                "QR13 exact structural work baseline",
            )
            result.append(
                dict(
                    case=case["id"],
                    seed=case["seed"],
                    partition=case["partition"],
                    grid=m["n"],
                    time=tick * s["dt"],
                    node=node,
                    numerical_valid=case["numerical_valid"],
                    local_trace_eligible=local is not None,
                    proposal_exists=pair is not None,
                    accepted=expected,
                    work_prediction=predicted_work,
                    work_actual=actual_work,
                    absolute_error=abs(predicted_work - actual_work),
                )
            )
    csv_write(root / "event-oracles.csv", result)
    from analysis.dataset_0013 import save

    save(
        root / "event-oracles.json",
        dict(
            opportunities=len(result),
            max_work_error=max(r["absolute_error"] for r in result),
            eligibility="exact known-rule baseline",
            occurrence="eligibility plus known external permission",
            switch_work="E(new palette, same u/v)-E(old palette,same u/v)",
            learner_scalar_classifiers="NOT RUN: no extra fits registered; "
            "exact deterministic baseline already explains labels",
            consequences="Separate palette ablation and prior single-event causal branches; "
            "new policy contrast changes all eligible nodes.",
        ),
    )
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    a = p.parse_args()
    analyze(a.root)


if __name__ == "__main__":
    main()
