"""Independent QR10 stationary pilot reconstruction and conditional extension gates."""

import argparse
import json
import math
from pathlib import Path

import numpy as np

from analysis import experiment_0009 as old
from analysis import experiment_0010 as fluid
from analysis.experiment_0005 import require


def coefficients(palette):
    p = np.asarray(palette).reshape(8, 8)
    occupied = np.zeros((8, 8), dtype=int)
    degree = np.zeros((8, 8), dtype=int)
    for axis in (0, 1):
        a, b = [slice(None)] * 2, [slice(None)] * 2
        a[axis] = slice(1, None)
        b[axis] = slice(None, -1)
        occupied[tuple(a)] += p[tuple(b)] != 0
        occupied[tuple(b)] += p[tuple(a)] != 0
        degree[tuple(a)] += 1
        degree[tuple(b)] += 1
    omega = (0.8 + 0.08 * p + 0.04 * occupied + 0.12 * (p == 1)) ** 2
    gamma = 0.08 + 0.01 * (degree - occupied) + 0.02 * (p != 1)
    g = np.where(p == 0, 0.5, np.where(p == 1, 1.0, 0.75))
    return omega, gamma, g


def neuron_energy(palette, u, v):
    omega, _, g = coefficients(palette)
    u = np.asarray(u).reshape(8, 8)
    v = np.asarray(v).reshape(8, 8)
    terms = list((0.5 * v * v + 0.5 * omega * u * u).ravel())
    for axis in (0, 1):
        a, b = [slice(None)] * 2, [slice(None)] * 2
        a[axis] = slice(1, None)
        b[axis] = slice(None, -1)
        terms.extend((0.075 * g[tuple(a)] * g[tuple(b)] * (u[tuple(a)] - u[tuple(b)]) ** 2).ravel())
    return math.fsum(float(x) for x in terms)


def neural(path):
    rows = old.rows(path)
    require(len(rows) in (128, 192), "actual64-module neurons")
    for i, r in enumerate(rows):
        require(int(r["neuron"]) == i // 64 and int(r["module"]) == i % 64, "neuron order")
    p = np.array([int(r["palette"]) for r in rows]).reshape(-1, 64)
    u = np.array([float(r["u"]) for r in rows]).reshape(-1, 64)
    v = np.array([float(r["v"]) for r in rows]).reshape(-1, 64)
    require(
        ((p >= 0) & (p <= 4)).all() and np.isfinite(u).all() and np.isfinite(v).all(),
        "finite actual neuron state",
    )
    return p, u, v


def history(folder):
    rows = old.rows(folder / "history.csv")
    require(len(rows) == 241 * 64, "remote history coverage")
    m = old.rows(folder / "metadata.csv")[0]
    stride = round(0.1 / float(m["dt"]))
    for i, r in enumerate(rows):
        require(
            int(r["tick"]) == (i // 64) * stride and int(r["module"]) == i % 64,
            "remote clock/order",
        )
    return np.array([[float(r["u"]), float(r["v"])] for r in rows]).reshape(241, 64, 2)


def audit(root, extended=False):
    gates = []
    summaries = []
    histories = {}
    metadata = {}

    def gate(question, case, name, value, limit=0, lower=0):
        gates.append(
            dict(
                question=question,
                case=case,
                gate=name,
                value=float(value),
                limit=limit,
                lower=lower,
                verdict="PASS" if lower <= value <= limit else "FAIL",
            )
        )

    ledger = old.rows(root / "ledger.csv")
    plan = old.rows(root / "plan.csv")
    expected = (
        {"train": 34, "evaluate": 72, "interference": 8}.get(root.name, 19) if extended else 19
    )
    require(
        len(plan) == len(ledger) == expected
        and {r["case"] for r in plan} == {r["case"] for r in ledger},
        "exact frozen cases",
    )
    require(all(r["status"] == "COMPLETE" for r in ledger), "pilot complete")
    for entry in ledger:
        name = entry["case"]
        folder = root / name
        print("audit pilot", name, flush=True)
        m = old.rows(folder / "metadata.csv")[0]
        metadata[name] = m
        dt = float(m["dt"])
        n = int(m["n"])
        module = int(m["module"])
        control = m["control"]
        rows = old.rows(folder / "metrics.csv")
        ticks = round(24 / dt)
        require(len(rows) == ticks + 1, "all ticks")
        for i, r in enumerate(rows):
            require(int(r["tick"]) == i and float(r["time"]) == i * dt, "metric clock")
            require(all(math.isfinite(float(x)) for x in r.values()), "finite metrics")
        h = history(folder)
        histories[name] = h
        work = float(rows[-1]["work"])
        positive = float(rows[-1]["positive_work"])
        scale = max(positive, 1e-30)
        residual = (
            max(
                abs(
                    sum(
                        float(r[k])
                        for k in (
                            "fluid_energy",
                            "source_energy",
                            "receiver_energy",
                            "loss",
                            "direct_energy",
                        )
                    )
                    - float(r["work"])
                )
                for r in rows
            )
            / scale
        )
        gate("C3", name, "total_balance", residual, 0.01)
        gate(
            "C3",
            name,
            "exchange_cancellation",
            float(rows[-1]["exchange_cancellation"]) / scale,
            1e-12,
        )
        kicks = old.rows(folder / "kicks.csv")
        drives = {
            "IA": ((0, 1), (2, 0)),
            "IB": ((0, 0), (2, 1)),
            "IAB+": ((0, 1), (2, 1)),
            "IAB-": ((0, 1), (2, -1)),
        }.get(control, ((0, 1),))
        count = len(drives)
        require(len(kicks) == 2 * ticks * count, "kick coverage")
        kick_work = np.zeros(ticks + 1)
        kick_positive = np.zeros(ticks + 1)
        for i, r in enumerate(kicks):
            tick = i // (2 * count) + 1
            require(int(r["tick"]) == tick and int(r["half"]) == (i // count) % 2, "kick clock")
            time = (tick - 0.5) * dt
            force = (
                math.sin(2 * math.pi / [12, 8, 6][int(m["band"])] * time)
                * math.sin(math.pi * time / 12) ** 2
                if time <= 12 and control not in ("ZERO", "FROZEN")
                else 0
            )
            id, sign = drives[i % count]
            require(int(r.get("neuron", 0)) == id, "kick source identity")
            force *= sign
            before, after, impulse = (float(r[k]) for k in ("before", "after", "impulse"))
            require(abs(impulse - 0.5 * dt * force) <= 1e-14, "registered forcing")
            require(abs(after - before - impulse) <= 1e-14, "actual kick update")
            dw = 0.5 * (after * after - before * before)
            kick_work[tick] += dw
            kick_positive[tick] += max(dw, 0)
        require(
            np.allclose(
                np.cumsum(kick_work), [float(r["work"]) for r in rows], rtol=1e-12, atol=1e-15
            ),
            "independent external work",
        )
        require(
            np.allclose(
                np.cumsum(kick_positive),
                [float(r["positive_work"]) for r in rows],
                rtol=1e-12,
                atol=1e-15,
            ),
            "independent positive work",
        )
        exchange = old.rows(folder / "exchange.csv")
        for r in exchange:
            xb, xa, vb, va, df, dn = (
                float(r[k])
                for k in (
                    "x_before",
                    "x_after",
                    "v_before",
                    "v_after",
                    "fluid_delta",
                    "neural_delta",
                )
            )
            require(
                abs(dn - 0.5 * (va * va - vb * vb)) <= 1e-14 * scale,
                "neural exchange reconstruction",
            )
            require(
                abs(df - 0.5 * (xa * xa - xb * xb)) <= 1e-12 * scale,
                "fluid projection exchange reconstruction",
            )
        for port in old.rows(folder / "ports.csv"):
            selected = [
                r
                for r in exchange
                if r["neuron"] == port["neuron"] and r["module"] == port["module"]
            ]
            require(len(selected) == 2 * ticks, "port substep coverage")
            for key, ref in (
                ("fluid_net", math.fsum(float(r["fluid_delta"]) for r in selected)),
                ("neural_net", math.fsum(float(r["neural_delta"]) for r in selected)),
                ("positive", math.fsum(max(float(r["fluid_delta"]), 0) for r in selected)),
                ("backflow", math.fsum(max(-float(r["fluid_delta"]), 0) for r in selected)),
            ):
                require(
                    abs(float(port[key]) - ref) <= 1e-12 * scale,
                    "independent signed exchange totals",
                )
        initial_palette = None
        for tick in (0, ticks // 2, ticks):
            field = fluid.decode(folder / f"{tick:06}.q10")
            require((field["n"], field["dt"], field["tick"]) == (n, dt, tick), "fluid clock")
            p, u, v = neural(folder / f"{tick:06}.neuron.csv")
            if initial_palette is None:
                initial_palette = p.copy()
            gate("C7", name, f"frozen_palette_t{tick}", float(np.max(abs(p - initial_palette))))
            for id in (0, 1):
                actual = (
                    neuron_energy(p[1], u[1], v[1])
                    if id == 1
                    else math.fsum(neuron_energy(p[j], u[j], v[j]) for j in range(len(p)) if j != 1)
                )
                reported = float(rows[tick]["receiver_energy" if id == 1 else "source_energy"])
                gate(
                    "C3", name, f"neural_energy{id}_t{tick}", abs(actual - reported) / scale, 1e-12
                )
            actual = fluid.energy(field["fields"], 24 / n)
            gate(
                "C3",
                name,
                f"fluid_energy_t{tick}",
                abs(actual - float(rows[tick]["fluid_energy"])) / scale,
                1e-12,
            )
            require(
                np.array_equal(h[round(tick * dt / 0.1), :, 0], u[1])
                and np.array_equal(h[round(tick * dt / 0.1), :, 1], v[1]),
                "remote raw reconstruction",
            )
            for axis in (0, 1, 2):
                wall = [slice(None)] * 3
                wall[2 - axis] = -1
                gate(
                    "C7",
                    name,
                    f"wall{axis}_t{tick}",
                    float(np.max(abs(field["fields"][axis + 1][tuple(wall)]))),
                )
            if control in ("ZERO", "OFF", "FROZEN", "DIRECT", "RECEIVER_ONLY"):
                gate("C7", name, f"zero_fluid_t{tick}", float(np.max(abs(field["fields"]))))
            if control == "FROZEN":
                gate(
                    "C7",
                    name,
                    f"frozen_source_t{tick}",
                    float(np.max(abs(u[0]))) + float(np.max(abs(v[0]))),
                )
        if control in ("OFF", "ZERO", "FROZEN", "SOURCE_ONLY", "RECEIVER_ONLY"):
            gate("C7", name, "zero_receiver_every_sample", float(np.max(abs(h))))
        peak_fluid = max(float(r["fluid_energy"]) for r in rows)
        peak_receiver = max(float(r["receiver_energy"]) for r in rows)
        emitted = float(rows[-1]["source_positive"])
        if control == "FLUID":
            gate("C1", name, "positive_source_work", work, 1e100, 1e-30)
            gate("C1", name, "emission_fraction", peak_fluid / max(work, 1e-30), 1e100, 1e-10)
            gate("C1", name, "source_transfer", emitted / max(work, 1e-30), 1e100, 1e-10)
            gate("C2", name, "remote_response", peak_receiver / max(work, 1e-30), 1e100, 1e-10)
        summaries.append(
            dict(
                case=name,
                work=work,
                positive_work=positive,
                emitted_positive=emitted,
                source_backflow=float(rows[-1]["source_backflow"]),
                receiver_to_fluid_net=float(rows[-1]["receiver_net"]),
                peak_fluid=peak_fluid,
                peak_receiver=peak_receiver,
                receiver_per_work=peak_receiver / max(work, 1e-30),
                balance=residual,
            )
        )
    refinements = []
    if not extended:
        refinements = []
        for module in (9, 27):
            prefix = f"s211_m{module}_b0_d2_"
            a = prefix + "n48_dt0.05_FLUID"
            base = histories[a]
            for label, b in (
                ("temporal", prefix + "n48_dt0.025_FLUID"),
                ("spatial", prefix + "n96_dt0.025_FLUID"),
            ):
                relative = old.relative(base, histories[b])
                ra = next(r for r in summaries if r["case"] == a)
                rb = next(r for r in summaries if r["case"] == b)
                workdiff = abs(ra["work"] - rb["work"]) / max(abs(rb["work"]), 1e-30)
                gate("EXTENSION", a, label + "_remote_refinement", relative, 0.1)
                gate("EXTENSION", a, label + "_source_work", workdiff, 0.02)
                refinements.append(
                    dict(
                        module=module,
                        test=label,
                        remote_relative=relative,
                        source_work_relative=workdiff,
                    )
                )
        original = root / "s211_m9_b0_d2_n48_dt0.05_FLUID"
        repeat = root / "s211_m9_b0_d2_n48_dt0.05_REPEAT"
        require(
            sorted(p.name for p in original.iterdir()) == sorted(p.name for p in repeat.iterdir()),
            "repeat coverage",
        )
        gate(
            "C7",
            "repeat",
            "all_case_bytes",
            sum(p.read_bytes() != (repeat / p.name).read_bytes() for p in original.iterdir()),
        )
    verdicts = {
        q: "FAIL" if any(g["verdict"] == "FAIL" for g in gates if g["question"] == q) else "PASS"
        for q in ("C1", "C2", "C3", "C7", "EXTENSION")
    }
    result = dict(
        schema=1,
        executions=expected,
        verdicts=verdicts,
        extended_authorized=all(v == "PASS" for v in verdicts.values()),
        failures=[g for g in gates if g["verdict"] == "FAIL"],
        C4="INDETERMINATE",
        C4_execution="NOT RUN (pilot has no held-out seeds)",
        C5="INDETERMINATE",
        C6="INDETERMINATE",
    )
    for name, records in (
        ("gates.csv", gates),
        ("summary.csv", summaries),
        ("refinement.csv", refinements),
    ):
        old.csv_write(root / name, records)
    (root / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--extended", action="store_true")
    args = parser.parse_args()
    audit(args.root, args.extended)


if __name__ == "__main__":
    main()
