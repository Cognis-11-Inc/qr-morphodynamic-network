"""Frozen QR12 numerical, local-event and causal prerequisite decisions."""

import argparse
import json
from pathlib import Path

import numpy as np

from analysis import io_0011 as oldio
from analysis import io_0012 as io
from analysis.audit_0012 import proposal, stage
from analysis.experiment_0009 import csv_write, relative, rows


def uv(folder):
    s = io.stream(folder)
    a = s["frames"]["nodes"]
    return np.stack((a["u"], a["v"]), axis=-1)


def checkpoints(folder):
    folder = Path(folder)
    if (folder / "observations.q11o").exists():
        return {int(p.stem): oldio.fluid(p) for p in folder.glob("*.q11")}
    return {int(p.stem): io.snapshot(p) for p in folder.glob("*.q12") if p.stem.isdigit()}


def compare(a, b):
    sa, sb = io.stream(a), io.stream(b)
    stride = round(sa["dt"] / sb["dt"])
    x = sa["frames"]["nodes"]
    y = sb["frames"][::stride]["nodes"]
    assert len(x) == len(y)
    r = {k: relative(x[k], y[k]) for k in ("u", "v", "packet", "z")}
    r["palette_positions_disagree"] = float(np.mean(x["palette"] != y["palette"]))
    ca, cb = checkpoints(a), checkpoints(b)
    f = []
    for tick, s in ca.items():
        if tick == 0 or round(tick * sa["dt"] / sb["dt"]) not in cb:
            continue
        other = cb[round(tick * sa["dt"] / sb["dt"])]
        fields = oldio.restrict(other["fields"]) if s["n"] != other["n"] else other["fields"]
        f.append(relative(s["fields"], fields))
    r["full_fluid"] = max(f, default=0.0)
    return r


def write(root, stage_name, gates, extra):
    r = dict(
        stage=stage_name,
        prerequisite_pass=all(x["verdict"] == "PASS" for x in gates),
        gates=gates,
        **extra,
    )
    (root / stage_name / "gates.json").write_text(json.dumps(r, indent=2) + "\n")
    csv_write(root / stage_name / "gates.csv", gates)
    print(json.dumps(r, indent=2))
    return r


def gate_builder():
    gates = []

    def g(name, value, limit=0):
        gates.append(
            dict(
                gate=name,
                value=float(value),
                limit=limit,
                verdict="PASS" if value <= limit else "FAIL",
            )
        )

    return gates, g


def a(root):
    root = Path(root)
    d = root / "a"
    receipt = stage(d)
    gates, g = gate_builder()
    g("independent_physics", not receipt["valid"])
    for grid in "TF":
        for name, value in compare(d / "FIXED_P", d / ("FIXED_" + grid)).items():
            g(grid + "_" + name, value, 0 if name == "palette_positions_disagree" else 0.1)
    for label in ("QUIET", "OFF"):
        for grid in "PF":
            x = io.stream(d / (label + "_" + grid))["frames"]["nodes"]
            g(label + "_fluid_packet_" + grid, np.max(abs(x["packet"])))
            g(
                label + "_unforced_motion_" + grid,
                np.max(abs(x[1:]["v"])) if False else np.max(abs(x["v"][:, 1:])),
            )
    for path in (d / "FIXED_P").glob("*.q12"):
        if path.stem.isdigit():
            before = io.snapshot(path)
            after = io.snapshot(d / "SENSOR_OFF_P" / path.name)
            g("passive_sensing_" + path.stem, not np.array_equal(before["fields"], after["fields"]))
    for field in ("u", "v"):
        g(
            "passive_" + field,
            not np.array_equal(
                io.stream(d / "FIXED_P")["frames"]["nodes"][field],
                io.stream(d / "SENSOR_OFF_P")["frames"]["nodes"][field],
            ),
        )
    for file in (
        "observations.q12o",
        "metrics.csv",
        "kicks.csv",
        "exchange.csv",
        "events.csv",
        "scores.csv",
    ):
        g(
            "actual_repeat_" + file,
            (d / "FIXED_P" / file).read_bytes() != (d / "REPEAT_P" / file).read_bytes(),
        )
    for grid in "PF":
        for name, value in compare(d / ("NEW_LEGACY_" + grid), d / ("ORACLE_" + grid)).items():
            g("original_QR11_" + grid + "_" + name, value, 1e-12)
    return write(
        root,
        "a",
        gates,
        dict(A="PASS" if all(x["verdict"] == "PASS" for x in gates) else "INDETERMINATE"),
    )


def b(root):
    root = Path(root)
    d = root / "b"
    receipt = stage(d)
    gates, g = gate_builder()
    g("independent_physics", not receipt["valid"])
    for grid in "TF":
        for name, value in compare(d / "ADAPTIVE_P", d / ("ADAPTIVE_" + grid)).items():
            g(grid + "_" + name, value, 0 if name == "palette_positions_disagree" else 0.1)

        def events(folder):
            return [
                (r["tick"], r["neuron"], r["a"], r["b"], r["accepted"])
                for r in rows(folder / "events.csv")
            ]

        ep = events(d / "ADAPTIVE_P")
        ef = events(d / ("ADAPTIVE_" + grid))
        ef = [
            (str(round(int(t) * io.stream(d / ("ADAPTIVE_" + grid))["dt"] / 0.05)), i, a, b, k)
            for t, i, a, b, k in ef
        ]
        g("exact_refined_events_" + grid, ep != ef)
    for file in (
        "observations.q12o",
        "metrics.csv",
        "kicks.csv",
        "exchange.csv",
        "events.csv",
        "scores.csv",
    ):
        g(
            "actual_repeat_" + file,
            (d / "ADAPTIVE_P" / file).read_bytes() != (d / "REPEAT_P" / file).read_bytes(),
        )
    counts = []
    for grid in "PF":
        x = io.stream(d / ("ADAPTIVE_" + grid))["frames"]["nodes"][-1]
        counts.append([int(v) for v in x["events"]])
        for label in ("QUIET", "TRACE_OFF", "VETO_ALL"):
            y = io.stream(d / (label + "_" + grid))["frames"]["nodes"][-1]
            g(label + "_changes_" + grid, np.max(y["events"]))
        g(
            "OFF_remote_events_" + grid,
            np.max(io.stream(d / ("OFF_" + grid))["frames"]["nodes"][-1]["events"][1:]),
        )
    activity = all(sum(v >= 2 for v in c) >= 2 for c in counts)
    target = {}
    for grid in "PF":
        dt = 0.05 if grid == "P" else 0.025
        x = io.snapshot(
            d / ("ADAPTIVE_" + grid) / ("pre-" + ("000320" if grid == "P" else "000640") + ".q12")
        )["nodes"][0]
        hmax = float(max(x["z"][277:341]))
        latch = hmax >= 0.02 or (hmax >= 0.005 and bool(x["latch"]))
        target[grid] = proposal(x, latch, int(x["last"]), dt) is not None
    deltaP = (uv(d / "ADAPTIVE_P") - uv(d / "VETO_ALL_P")).ravel()
    deltaF = (uv(d / "ADAPTIVE_F")[::2] - uv(d / "VETO_ALL_F")[::2]).ravel()
    norm = float(np.linalg.norm(deltaF))
    err = float(np.linalg.norm(deltaP - deltaF))
    consequence = (
        "PASS" if norm > 1e-8 and norm >= 5 * err else "INDETERMINATE" if norm > 1e-8 else "FAIL"
    )
    return write(
        root,
        "b",
        gates,
        dict(
            M1_activity="PASS" if activity else "FAIL",
            M1_validity="PASS" if all(x["verdict"] == "PASS" for x in gates) else "INDETERMINATE",
            M1_consequence=consequence,
            event_counts=counts,
            target_eligible=target,
            consequence_norm=norm,
            consequence_grid_error=err,
        ),
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=["a", "b"])
    p.add_argument("root", type=Path)
    x = p.parse_args()
    {"a": a, "b": b}[x.stage](x.root)


if __name__ == "__main__":
    main()
