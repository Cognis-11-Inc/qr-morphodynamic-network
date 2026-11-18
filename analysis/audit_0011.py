"""Independent QR11 local sensor, online trace, physical accounting and gate audit."""

import argparse
import json
import math
from pathlib import Path

import numpy as np

from analysis import experiment_0009 as q9
from analysis import experiment_0010 as q10
from analysis import io_0011 as io
from analysis.audit_coupling_0010 import coefficients, neuron_energy, seeded_palette
from analysis.experiment_0005 import fnv, require
from analysis.package_experiment_0007 import sha


def rows(path):
    return q9.rows(path)


def scalar_work(folder):
    return float(rows(Path(folder) / "metrics.csv")[-1]["work"])


def signature(folder, representation):
    s = io.stream(Path(folder) / "observations.q11o")
    frames = s["frames"]
    node = frames[-1]["nodes"][1]
    if representation == "INSTANT":
        return np.stack((node["u"], node["v"]), axis=1).ravel().copy()
    if representation == "QR10_STYLE":
        stride = round(0.2 / s["dt"])
        start = round(4 / s["dt"])
        end = round(24 / s["dt"])
        a = frames[start : end + 1 : stride]["nodes"][:, 1]
        return np.stack((a["u"], a["v"]), axis=-1).ravel().copy()
    z = node["z"].reshape(3, 135)
    if representation == "SIGNED":
        return z[:, [0, 1, 2, 3, 5, 6]].ravel().copy()
    if representation == "ENERGY":
        return z[:, 4].copy()
    if representation == "ALL_TRACE":
        return z.ravel().copy()
    raise ValueError(representation)


def phi(nodes):
    u = nodes["u"].reshape(-1, 8, 8)
    v = nodes["v"].reshape(-1, 8, 8)
    strain = np.zeros_like(u)
    degree = np.zeros((8, 8))
    for axis in (1, 2):
        a, b = [slice(None)] * 3, [slice(None)] * 3
        a[axis] = slice(1, None)
        b[axis] = slice(None, -1)
        d = (u[tuple(a)] - u[tuple(b)]) ** 2
        strain[tuple(a)] += d
        strain[tuple(b)] += d
        aa, bb = [slice(None)] * 2, [slice(None)] * 2
        aa[axis - 1] = slice(1, None)
        bb[axis - 1] = slice(None, -1)
        degree[tuple(aa)] += 1
        degree[tuple(bb)] += 1
    h = (v * v + 0.25 * strain / degree).reshape(-1, 64)
    corr = nodes["v"] * nodes["packet"][:, 0, None]
    packet = nodes["packet"]
    scales = np.array([0.01, 0.01, 0.01, 0.01, 0.0001, 0.0001, 0.01])
    return np.concatenate(
        (packet / (scales + abs(packet)), h / (1e-8 + abs(h)), corr / (1e-6 + abs(corr))), axis=1
    )


def neural_free(p, u, v, dt):
    constants = [coefficients(x) for x in p]
    omega = np.array([x[0] for x in constants])
    gamma = np.array([x[1] for x in constants])
    g = np.array([x[2] for x in constants])
    u = u.reshape(-1, 8, 8)
    v = v.reshape(-1, 8, 8)
    damping = np.exp(-gamma * dt / 2)

    def acceleration(a):
        result = -omega * a
        for axis in (1, 2):
            x, y = [slice(None)] * 3, [slice(None)] * 3
            x[axis] = slice(1, None)
            y[axis] = slice(None, -1)
            force = 0.15 * g[tuple(x)] * g[tuple(y)] * (a[tuple(x)] - a[tuple(y)])
            result[tuple(y)] += force
            result[tuple(x)] -= force
        return result

    first = v * damping
    loss = 0.5 * np.sum(v * v - first * first, axis=(1, 2))
    mid = first + 0.5 * dt * acceleration(u)
    nextu = u + dt * mid
    last = mid + 0.5 * dt * acceleration(nextu)
    nextv = last * damping
    loss += 0.5 * np.sum(last * last - nextv * nextv, axis=(1, 2))
    return nextu.reshape(-1, 64), nextv.reshape(-1, 64), loss


def force(signal, time):
    if signal == "ZERO":
        return 0.0
    if signal in ("REF", "REFNEG", "AB+", "AB-"):
        return (
            math.sin(2 * math.pi / 12 * time)
            * math.sin(math.pi * time / 12) ** 2
            * (-1 if signal == "REFNEG" else 1)
            if time <= 12
            else 0.0
        )
    if signal == "PROBE":
        return (
            math.sin(2 * math.pi / 8 * time) * math.sin(math.pi * time / 8) ** 2
            if time <= 8
            else 0.0
        )
    signs = {"STD": (1, 1, -1), "ORDER": (-1, 1, 1), "NEG": (-1, -1, 1), "SINGLE": (0, 0, -1)}[
        signal
    ]
    for sign, start in zip(signs, (0, 16, 32), strict=True):
        t = time - start
        if 0 <= t <= 12:
            return sign * math.sin(2 * math.pi / 8 * t) * math.sin(math.pi * t / 12) ** 2
    return 0.0


def audit_case(folder, fresh=False):
    folder = Path(folder)
    cache = folder / "audit.json"
    raw = [
        p
        for p in folder.iterdir()
        if p.is_file() and p.name not in ("audit.json", "audit-gates.csv")
    ]
    inputs = {p.name: sha(p) for p in sorted(raw)}
    sources = {str(p): sha(p) for p in map(Path, ("analysis/audit_0011.py", "analysis/io_0011.py"))}
    if cache.exists() and not fresh:
        old = json.loads(cache.read_text())
        if old["inputs"] == inputs and old["sources"] == sources:
            return old
    m = rows(folder / "metadata.csv")[0]
    data = io.stream(folder / "observations.q11o")
    frames = data["frames"]
    dt = data["dt"]
    ticks = data["ticks"]
    count = data["count"]
    require(
        (int(m["n"]), float(m["dt"]), round(float(m["horizon"]) / dt)) == (data["n"], dt, ticks),
        "QR11 metadata clock",
    )
    metrics = rows(folder / "metrics.csv")
    require(len(metrics) == ticks + 1, "QR11 every-tick metrics")
    scale = max(float(metrics[-1]["positive_work"]), 1e-30)
    gates = []

    def gate(name, value, limit=0):
        gates.append(
            dict(
                gate=name,
                value=float(value),
                limit=limit,
                verdict="PASS" if value <= limit else "FAIL",
            )
        )

    expected = np.zeros((count, 3, 135))
    trace_error = step_error = loss_error = 0.0
    for tick, frame in enumerate(frames):
        require(
            int(frame["tick"]) == tick and fnv(frame.tobytes()[:-8]) == int(frame["checksum"]),
            "QR11 frame clock/checksum",
        )
        node = frame["nodes"]
        io.valid_nodes(node)
        require((node["age"] == tick).all(), "QR11 own trace clock")
        require(all(math.isfinite(float(x)) for x in metrics[tick].values()), "QR11 finite metrics")
        require(
            int(metrics[tick]["tick"]) == tick and float(metrics[tick]["time"]) == tick * dt,
            "QR11 metric clock",
        )
        if tick:
            if m["mode"] not in ("Off", "SensorOff"):
                incoming = phi(node)
                a = np.exp(-dt / np.array([0.5, 2, 8]))[None, :, None]
                expected = a * expected + (1 - a) * incoming[:, None, :]
                if m["mode"] == "Scrambled" and abs((tick * dt) % 1) < 1e-12:
                    expected[:, :, 7:71] = np.roll(expected[:, :, 7:71], 1, axis=-1)
                    expected[:, :, 71:135] = np.roll(expected[:, :, 71:135], 1, axis=-1)
            trace_error = max(
                trace_error, float(np.max(abs(expected - node["z"].reshape(count, 3, 135))))
            )
            if m["mode"] == "SensorOff":
                require(
                    (node["packet"] == 0).all() and (node["previous"] == 0).all(),
                    "QR11 disabled sensor",
                )
            else:
                derivative = (node["packet"][:, 0] - frames[tick - 1]["nodes"]["previous"]) / dt
                require(
                    np.allclose(node["packet"][:, 6], derivative, rtol=1e-12, atol=1e-14),
                    "QR11 causal derivative",
                )
                require(
                    np.array_equal(node["previous"], node["packet"][:, 0]),
                    "QR11 own previous pressure",
                )
        else:
            require(
                (node["u"] == 0).all()
                and (node["v"] == 0).all()
                and (node["z"] == 0).all()
                and (node["packet"] == 0).all(),
                "QR11 exact clean start",
            )
        actual = math.fsum(neuron_energy(x["palette"], x["u"], x["v"]) for x in node)
        gate(
            f"neural_energy_{tick}",
            abs(actual - float(metrics[tick]["neural_energy"])) / scale,
            1e-12,
        )
    gate("causal_trace_reconstruction", trace_error, 1e-12)
    residual = (
        max(
            abs(
                float(r["fluid_energy"])
                + float(r["neural_energy"])
                + float(r["loss"])
                - float(r["work"])
            )
            for r in metrics
        )
        / scale
    )
    gate("actual_total_balance", residual, 0.01)
    kicks = rows(folder / "kicks.csv")
    exchange = rows(folder / "exchange.csv")
    bykick = [[] for _ in range(ticks + 1)]
    byexchange = [[] for _ in range(ticks + 1)]
    for r in kicks:
        bykick[int(r["tick"])].append(r)
    for r in exchange:
        byexchange[int(r["tick"])].append(r)
    cumulative_work = positive = negative = 0.0
    sum_exchange = np.zeros((count, 3))
    cancel = 0.0
    for tick in range(1, ticks + 1):
        before = frames[tick - 1]["nodes"]
        now = frames[tick]["nodes"]
        u = before["u"].copy()
        v = before["v"].copy()
        stepdelta = np.zeros(count)
        for half in (0, 1):
            if half == 1:
                u, v, loss = neural_free(before["palette"], u, v, dt)
                loss_error = max(
                    loss_error, float(np.max(abs(now["loss"] - before["loss"] - loss)))
                )
            if half == 1:
                for r in byexchange[tick]:
                    if int(r["half"]) != half:
                        continue
                    id, mod = int(r["neuron"]), int(r["module"])
                    require(
                        abs(v[id, mod] - float(r["v_before"])) <= 1e-12,
                        "QR11 reverse port causality",
                    )
                    v[id, mod] = float(r["v_after"])
            for r in bykick[tick]:
                if int(r["half"]) != half:
                    continue
                id, mod = int(r["neuron"]), int(r["module"])
                expected_force = float(m["amplitude"]) * force(m["signal"], (tick - 0.5) * dt)
                if id == 2 and m["signal"] == "AB-":
                    expected_force = -expected_force
                impulse = float(r["impulse"])
                require(abs(impulse - 0.5 * dt * expected_force) <= 1e-13, "QR11 actual force")
                require(
                    abs(v[id, mod] - float(r["before"])) <= 1e-12
                    and abs(float(r["after"]) - float(r["before"]) - impulse) <= 1e-13,
                    "QR11 kick causality",
                )
                v[id, mod] = float(r["after"])
                dw = 0.5 * (float(r["after"]) ** 2 - float(r["before"]) ** 2)
                cumulative_work += dw
                positive += max(dw, 0)
                negative += max(-dw, 0)
            if half == 0:
                for r in byexchange[tick]:
                    if int(r["half"]) != half:
                        continue
                    id, mod = int(r["neuron"]), int(r["module"])
                    require(
                        abs(v[id, mod] - float(r["v_before"])) <= 1e-12,
                        "QR11 forward port causality",
                    )
                    v[id, mod] = float(r["v_after"])
        step_error = max(
            step_error, float(np.max(abs(u - now["u"]))), float(np.max(abs(v - now["v"])))
        )
        for r in byexchange[tick]:
            id = int(r["neuron"])
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
                abs(df - 0.5 * (xa * xa - xb * xb)) <= 1e-12 * scale
                and abs(dn - 0.5 * (va * va - vb * vb)) <= 1e-12 * scale,
                "QR11 substep exchange energy",
            )
            stepdelta[id] += df
            sum_exchange[id] += [df, max(df, 0), max(-df, 0)]
            cancel += abs(df + dn)
        if m["mode"] != "SensorOff":
            require(
                np.allclose(now["packet"][:, 5], -stepdelta / dt, rtol=1e-12, atol=1e-13),
                "QR11 locally sensed transfer",
            )
        for actual, key in (
            (cumulative_work, "work"),
            (positive, "positive_work"),
            (negative, "negative_work"),
        ):
            require(
                abs(actual - float(metrics[tick][key])) <= 1e-12 * scale,
                "QR11 independent external work",
            )
        require(
            abs(
                float(np.sum(sum_exchange[[i for i in range(count) if i != 1], 0]))
                - float(metrics[tick]["source_net"])
            )
            <= 1e-12 * scale,
            "QR11 signed emission total",
        )
    gate("independent_neuron_step", step_error, 1e-12)
    gate("independent_neuron_loss", loss_error / scale, 1e-12)
    gate("exchange_cancellation", cancel / scale, 1e-12)
    initial = frames[0]["nodes"]["palette"]
    if not m["state_ref"]:
        for i, id in enumerate((2182, 2186, 2184)[:count]):
            require(
                np.array_equal(initial[i], seeded_palette(int(m["seed"]), id)),
                "QR11 initial independent palettes",
            )
    else:
        require(
            (frames[0]["nodes"]["age"] == 0).all()
            and (frames[0]["nodes"]["loss"] == 0).all()
            and (frames[0]["nodes"]["committed"] == 0).all(),
            "QR11 complete reset",
        )
        virgin = m["virgin_ref"].removeprefix("restore:")
        old = io.neurons(virgin)["nodes"]
        require(np.array_equal(initial[0], old[0]["palette"]), "QR11 source restored")
        retained = (
            io.neurons(m["state_ref"])["nodes"][1]["palette"]
            if not m["virgin_ref"].startswith("restore:")
            else old[1]["palette"]
        )
        require(np.array_equal(initial[1], retained), "QR11 only declared retained morphology")
    require(
        np.array_equal(
            frames["nodes"]["palette"], np.broadcast_to(initial, frames["nodes"]["palette"].shape)
        ),
        "QR11 physical stage palette frozen",
    )
    for path in sorted(folder.glob("*.q11")):
        f = io.fluid(path)
        tick = f["tick"]
        node = frames[tick]["nodes"]
        snapshot = io.neurons(folder / (path.stem + ".n11"))
        require(snapshot["nodes"].tobytes() == node.tobytes(), "QR11 actual bounded snapshot")
        e = q10.energy(f["fields"], 24 / f["n"])
        gate(f"fluid_energy_{tick}", abs(e - float(metrics[tick]["fluid_energy"])) / scale, 1e-12)
        positions = [
            (10.5, 12.5, 12.5),
            (10.5 + int(m["distance"]), 12.5, 12.5),
            (10.5, 14.5, 12.5),
        ]
        for id in range(count):
            if m["mode"] != "SensorOff" and tick:
                require(
                    np.allclose(
                        io.local(f["fields"], positions[id]),
                        node[id]["packet"][:5],
                        rtol=1e-12,
                        atol=1e-14,
                    ),
                    "QR11 strictly local sensor reconstruction",
                )
        for axis in range(3):
            sl = [slice(None)] * 3
            sl[2 - axis] = -1
            gate(f"wall_{axis}_{tick}", float(np.max(abs(f["fields"][axis + 1][tuple(sl)]))))
    work = float(metrics[-1]["work"])
    if m["amplitude_policy"].startswith("work1:"):
        gate("matched_external_work", abs(work - 1), 1e-10)
    result = dict(
        schema=1,
        case=folder.name,
        inputs=inputs,
        sources=sources,
        gates=gates,
        valid=all(g["verdict"] == "PASS" for g in gates),
        work=work,
        positive_work=float(metrics[-1]["positive_work"]),
        trace_error=trace_error,
        step_error=step_error,
        loss_error=loss_error,
        energy_residual=residual,
    )
    q9.csv_write(folder / "audit-gates.csv", gates)
    cache.write_text(json.dumps(result, indent=2) + "\n")
    return result


def audit_stage(root, fresh=False):
    root = Path(root)
    plan = rows(root / "plan.csv")
    ledger = rows(root / "ledger.csv")
    require(
        len(plan) == len(ledger) and {r["case"] for r in plan} == {r["case"] for r in ledger},
        "QR11 complete exact stage plan",
    )
    for row in plan:
        m = rows(root / row["case"] / "metadata.csv")[0]
        for key in ("seed", "n", "distance", "module", "signal", "horizon", "three", "coupled"):
            require(m[key] == row[key], "QR11 planned metadata " + key)
        require(
            float(m["dt"]) == float(row["dt"]) and m["amplitude_policy"] == row["policy"],
            "QR11 planned clock/amplitude",
        )
    results = []
    for entry in ledger:
        print("audit QR11", root.name, entry["case"], flush=True)
        results.append(audit_case(root / entry["case"], fresh))
    result = dict(
        schema=1,
        stage=root.name,
        executions=len(results),
        valid=all(r["valid"] for r in results),
        failures=[
            dict(case=r["case"], gate=g)
            for r in results
            for g in r["gates"]
            if g["verdict"] == "FAIL"
        ],
    )
    (root / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--fresh", action="store_true")
    a = p.parse_args()
    print(json.dumps(audit_stage(a.root, a.fresh), indent=2))


if __name__ == "__main__":
    main()
