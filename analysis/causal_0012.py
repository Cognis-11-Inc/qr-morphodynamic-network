"""QR12 exact-fork and remote-response causal verification, no new physics."""

import argparse
import json
from pathlib import Path

import numpy as np

from analysis import io_0012 as io
from analysis.audit_0012 import node_energy, proposal, stage
from analysis.experiment_0005 import require
from analysis.experiment_0009 import csv_write, rows
from analysis.gates_0012 import uv


def relative_delta(delta, reference):
    """Magnitude of an already formed difference divided by reference magnitude."""
    return float(np.linalg.norm(delta) / max(float(np.linalg.norm(reference)), 1e-30))


def boundary(folder):
    folder = Path(folder)
    m = rows(folder / "metadata.csv")[0]
    pre = io.snapshot(folder / "branch-before.q12")
    post = io.snapshot(folder / "branch-after.q12")
    require(
        (folder / "branch-before.q12").read_bytes() == Path(m["checkpoint"]).read_bytes(),
        "QR12 fork exact ancestor",
    )
    require(np.array_equal(pre["fields"], post["fields"]), "QR12 no instantaneous fluid mutation")
    require(
        np.array_equal(pre["ports"], post["ports"])
        and np.array_equal(pre["accounts"][:2], post["accounts"][:2]),
        "QR12 fork preserves port and forcing history",
    )
    for i in range(pre["count"]):
        for k in ("u", "v", "packet", "previous", "age", "z", "loss"):
            if i == 0 and k == "v" and m["policy"] == "SHAM":
                continue
            require(
                np.array_equal(pre["nodes"][i][k], post["nodes"][i][k]),
                "QR12 no unregistered transient fork change",
            )
        if i:
            require(
                np.array_equal(pre["nodes"][i]["palette"], post["nodes"][i]["palette"]),
                "QR12 no direct remote palette intervention",
            )
    n = pre["nodes"][0]
    h = max(n["z"][277:341])
    latch = h >= 0.02 or (h >= 0.005 and bool(n["latch"]))
    pair = proposal(n, latch, int(n["last"]), pre["dt"])
    require(pair is not None, "QR12 registered eligible target")
    p = n["palette"].copy()
    if m["policy"] == "EXTERNAL":
        pair = next(
            (a, b)
            for a in range(64)
            for b in range(a + 1, 64)
            if abs(a // 8 - b // 8) + abs(a % 8 - b % 8) == 1 and p[a] != p[b]
        )
    if m["policy"] in ("PERMIT", "ISOLATED_PERMIT", "EXTERNAL"):
        p[list(pair)] = p[list(pair[::-1])]
    require(np.array_equal(p, post["nodes"][0]["palette"]), "QR12 declared target-only morphology")
    require(
        post["mask"] == (1 if m["policy"].startswith("ISOLATED") else 15),
        "QR12 declared coupling intervention",
    )
    delta = node_energy(post["nodes"][0]) - node_energy(pre["nodes"][0])
    work = (post["accounts"][6] + post["accounts"][7]) - (pre["accounts"][6] + pre["accounts"][7])
    require(
        abs(delta - work) <= 1e-12 * max(node_energy(pre["nodes"][0]), abs(work), 1e-30),
        "QR12 actual fork switching/sham work",
    )
    if m["policy"] == "SHAM":
        expected = n.copy()
        p = expected["palette"].copy()
        p[list(pair)] = p[list(pair[::-1])]
        expected["palette"] = p
        dw = node_energy(expected) - node_energy(n)
        require(
            abs(delta - dw) <= 1e-12 * max(node_energy(n), 1e-30),
            "QR12 sham matches total intervention energy",
        )
    return dict(case=folder.name, valid=True, work=work, ancestry=m["checkpoint"])


def review(root):
    root = Path(root)
    d = root / "c"
    receipt = stage(d)
    boundaries = [boundary(d / r["case"]) for r in rows(d / "ledger.csv")]
    effects = []
    for label in ("PERMIT", "SHAM", "EXTERNAL"):
        p = uv(d / (label + "_P")) - uv(d / "VETO_P")
        f = uv(d / (label + "_F"))[::2] - uv(d / "VETO_F")[::2]
        vP = uv(d / "VETO_P")
        vF = uv(d / "VETO_F")[::2]
        for node in range(4):
            norm = float(np.linalg.norm(f[:, node]))
            error = float(np.linalg.norm(p[:, node] - f[:, node]))
            relp = relative_delta(p[:, node], vP[:, node])
            relf = relative_delta(f[:, node], vF[:, node])
            series = np.linalg.norm(f[:, node].reshape(len(f), -1), axis=1)
            indices = np.flatnonzero(series > 1e-4 * max(float(series.max()), 1e-30))
            onset = 16 + 0.05 * int(indices[0]) if len(indices) else None
            passed = (
                receipt["valid"] and norm > 1e-8 and norm >= 5 * error and min(relp, relf) >= 0.001
            )
            effects.append(
                dict(
                    intervention=label,
                    node=node,
                    norm=norm,
                    grid_error=error,
                    relative_P=relp,
                    relative_F=relf,
                    onset=onset,
                    verdict="PASS"
                    if passed
                    else "INDETERMINATE"
                    if norm > 1e-8 and norm < 5 * error
                    else "FAIL",
                )
            )
    isolated = []
    for grid in "PF":
        a = uv(d / ("ISOLATED_PERMIT_" + grid))
        b = uv(d / ("ISOLATED_VETO_" + grid))
        equal = np.array_equal(a[:, 1:], b[:, 1:])
        require(equal, "QR12 isolated remote exact neural equality")
        isolated.append(dict(grid=grid, remote_equal=equal))
    rem = [r for r in effects if r["intervention"] == "PERMIT" and r["node"] > 0]
    local = next(r for r in effects if r["intervention"] == "PERMIT" and r["node"] == 0)
    sham = []
    for grid in "PF":
        sham.append(uv(d / ("PERMIT_" + grid)) - uv(d / ("SHAM_" + grid)))
    delta = float(np.linalg.norm(sham[1][::2]))
    error = float(np.linalg.norm(sham[0] - sham[1][::2]))
    r = dict(
        M2_local=local["verdict"],
        M2_remote="PASS"
        if any(x["verdict"] == "PASS" for x in rem)
        else "INDETERMINATE"
        if any(x["verdict"] == "INDETERMINATE" for x in rem)
        else "FAIL",
        M2_activity_to_morphology=None,
        M2_permit_vs_energy_sham="PASS" if delta > 1e-8 and delta >= 5 * error else "INDETERMINATE",
        sham_contrast_norm=delta,
        sham_contrast_grid_error=error,
        energy_attribution_limit=(
            "Sham matches total energy, not modal distribution; "
            "a residual does not alone isolate coefficients from every state perturbation."
        ),
        boundaries=boundaries,
        effects=effects,
        isolated=isolated,
    )
    b = json.loads((root / "b/gates.json").read_text())
    remote = all(any(x > 0 for x in c[1:]) for c in b["event_counts"])
    r["M2_activity_to_morphology"] = "PASS" if remote else "FAIL"
    csv_write(root / "causal-effects.csv", effects)
    (root / "causal-verification.json").write_text(json.dumps(r, indent=2) + "\n")
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    a = p.parse_args()
    print(json.dumps(review(a.root), indent=2))


if __name__ == "__main__":
    main()
