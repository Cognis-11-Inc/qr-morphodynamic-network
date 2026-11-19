"""Independent QR12 event, every-tick mechanical/trace and full-checkpoint audit."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from analysis import io_0011 as io11
from analysis import io_0012 as io
from analysis.audit_0011 import neural_free, phi
from analysis.audit_coupling_0010 import neuron_energy, seeded_palette
from analysis.experiment_0005 import fnv, require
from analysis.experiment_0009 import csv_write, rows
from analysis.experiment_0010 import energy


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def proposal(node, latch, last, dt):
    h = node["z"][277:341]
    s = h + 0.5 * abs(node["z"][341:405] - node["z"][71:135])
    if not latch or (int(node["age"]) - last) * dt < 8:
        return None
    pairs = []
    for m in range(64):
        for n in range(m + 1, 64):
            if abs(m // 8 - n // 8) + abs(m % 8 - n % 8) != 1:
                continue
            if (
                node["palette"][m] != node["palette"][n]
                and h[m] >= 0.01
                and h[n] >= 0.01
                and s[m] >= 0.01
                and s[n] >= 0.01
                and max(s[m], s[n]) >= 0.05 * max(s)
            ):
                pairs.append((m, n))
    pairs.sort(key=lambda p: (-float(s[p[0]] + s[p[1]]), *p))
    return pairs[0] if pairs else None


def source(kind, time):
    if kind == "QUIET":
        return 0.0
    if kind.startswith("SUSTAINED"):
        return math.sin(2 * math.pi * time / 8) * (
            math.sin(math.pi * time / 8) ** 2 if time < 4 else 1
        )
    return (
        math.sin(2 * math.pi * time / 8) * math.sin(math.pi * time / 12) ** 2 if time <= 12 else 0.0
    )


def free(p, u, v, dt, scalar):
    if not scalar:
        return neural_free(p, u, v, dt)
    u = u.copy()
    v = v.copy()
    loss = np.zeros(len(u))
    d = math.exp(-0.1 * dt * 0.5)
    for m in (9, 27):
        before = v[:, m].copy()
        v[:, m] *= d
        loss += 0.5 * (before**2 - v[:, m] ** 2)
        v[:, m] -= 0.5 * dt * u[:, m]
        u[:, m] += dt * v[:, m]
        v[:, m] -= 0.5 * dt * u[:, m]
        before = v[:, m].copy()
        v[:, m] *= d
        loss += 0.5 * (before**2 - v[:, m] ** 2)
    return u, v, loss


def node_energy(node, scalar=False):
    if scalar:
        return 0.5 * math.fsum(float(node[k][m]) ** 2 for k in ("u", "v") for m in (9, 27))
    return neuron_energy(node["palette"], node["u"], node["v"])


def _audit_case(folder, fresh=False):
    folder = Path(folder)
    cache = folder / "audit.json"
    raw = {
        p.name: sha(p)
        for p in sorted(folder.iterdir())
        if p.is_file() and p.name not in ("audit.json", "audit-gates.csv")
    }
    sources = {p: sha(p) for p in ("analysis/audit_0012.py", "analysis/io_0012.py")}
    if cache.exists() and not fresh:
        a = json.loads(cache.read_text())
        if a["raw"] == raw and a["sources"] == sources:
            return a
    m = rows(folder / "metadata.csv")[0]
    s = io.stream(folder)
    a = s["frames"]
    dt = s["dt"]
    count = s["count"]
    start = s["start"]
    scalar = bool(int(m["scalar"]))
    gates = []
    metrics = rows(folder / "metrics.csv")
    require(len(metrics) == len(a), "QR12 actual tick coverage")
    scale = max(float(metrics[-1]["positive"]), 1e-30)

    def gate(name, value, limit=0):
        gates.append(
            dict(
                gate=name,
                value=float(value),
                limit=limit,
                verdict="PASS" if value <= limit else "FAIL",
            )
        )

    norms = [
        float(np.linalg.norm(io11.kernel(s["n"], p)[1])) for p in io.positions(int(m["geometry"]))
    ]
    if start == 0:
        ids = [2182, 2186, 2184, 2188]
        geom = int(m["geometry"])
        indices = (
            [geom - 10]
            if 10 <= geom <= 13
            else [0, 1]
            if geom in (2, 20)
            else [2, 3]
            if geom == 21
            else list(range(count))
        )
        for index, id in enumerate(indices):
            require(
                np.array_equal(
                    a[0]["nodes"][index]["palette"], seeded_palette(int(m["seed"]), ids[id])
                ),
                "QR12 independent palette initialization",
            )
    bykick = {}
    byport = {}
    byevent = {}
    for label, dest in (("kicks.csv", bykick), ("exchange.csv", byport), ("events.csv", byevent)):
        for row in rows(folder / label):
            dest.setdefault(int(row["tick"]), []).append(row)
    expected = a[0]["nodes"]["z"].reshape(count, 3, 135).copy()
    trace_error = step_error = loss_error = 0.0
    switch = 0.0
    cumulative = float(metrics[0]["force_work"])
    positive = float(metrics[0]["positive"])
    negative = float(metrics[0]["negative"])
    port_net = float(metrics[0]["port_net"])
    cancel = float(metrics[0]["cancellation"])
    for index, frame in enumerate(a):
        tick = start + index
        node = frame["nodes"]
        require(
            int(frame["tick"]) == tick and fnv(frame.tobytes()[:-8]) == int(frame["checksum"]),
            "QR12 frame checksum/clock",
        )
        io11.valid_nodes(node)
        require((node["age"] == tick).all(), "QR12 local age")
        require(
            all(math.isfinite(float(x)) for x in metrics[index].values()), "QR12 finite metrics"
        )
        gate(
            f"node_energy_{tick}",
            abs(math.fsum(node_energy(x, scalar) for x in node) - float(metrics[index]["neural"]))
            / scale,
            1e-12,
        )
        if index == 0:
            if start == 0:
                require(
                    all(
                        np.count_nonzero(node[k]) == 0
                        for k in ("u", "v", "packet", "previous", "z", "loss")
                    ),
                    "QR12 exact initial zero",
                )
            continue
        old = a[index - 1]["nodes"]
        u = old["u"].copy()
        v = old["v"].copy()
        delta = np.zeros(count)
        kicks = bykick.get(tick, [])
        ports = byport.get(tick, [])
        for half in (0, 1):
            if half == 1:
                u, v, loss = free(old["palette"], u, v, dt, scalar)
                loss_error = max(loss_error, float(np.max(abs(node["loss"] - old["loss"] - loss))))
            if half == 1:
                for r in ports:
                    if int(r["half"]) == half:
                        i, j = int(r["neuron"]), int(r["module"])
                        require(
                            abs(v[i, j] - float(r["v_before"])) <= 1e-12,
                            "QR12 reverse local rotation chronology",
                        )
                        v[i, j] = float(r["v_after"])
            for r in kicks:
                if int(r["half"]) != half:
                    continue
                i, j = int(r["neuron"]), int(r["module"])
                f = source(m["forcing"], (tick - 0.5) * dt)
                f *= 0.5 if m["forcing"] == "COMMON" or m["forcing"].startswith("IND") else 1
                require(abs(float(r["impulse"]) - 0.5 * dt * f) < 1e-13, "QR12 declared forcing")
                require(
                    abs(v[i, j] - float(r["before"])) < 1e-12
                    and abs(float(r["after"]) - float(r["before"]) - float(r["impulse"])) < 1e-13,
                    "QR12 exact external impulse",
                )
                v[i, j] = float(r["after"])
                dw = 0.5 * (float(r["after"]) ** 2 - float(r["before"]) ** 2)
                cumulative += dw
                positive += max(dw, 0)
                negative += max(-dw, 0)
            if half == 0:
                for r in ports:
                    if int(r["half"]) == half:
                        i, j = int(r["neuron"]), int(r["module"])
                        require(
                            abs(v[i, j] - float(r["v_before"])) <= 1e-12,
                            "QR12 forward local rotation chronology",
                        )
                        v[i, j] = float(r["v_after"])
        # Perturbations occur after local event work, and therefore after trace sampling.
        trace_node = node.copy()
        trace_node["u"] = u
        trace_node["v"] = v
        for r in ports:
            i = int(r["neuron"])
            j = int(r["module"])
            xb, xa, vb, va, df, dn = [
                float(r[k])
                for k in (
                    "x_before",
                    "x_after",
                    "v_before",
                    "v_after",
                    "fluid_delta",
                    "neural_delta",
                )
            ]
            kernel_norm = norms[i]
            angle = 0.1 * kernel_norm / (24 / s["n"]) ** 1.5 * dt * 0.5
            require(
                abs(xa - (math.cos(angle) * xb + math.sin(angle) * vb)) < 1e-12
                and abs(va - (math.cos(angle) * vb - math.sin(angle) * xb)) < 1e-12,
                "QR12 independently reconstructed reciprocal rotation",
            )
            require(
                abs(df - 0.5 * (xa * xa - xb * xb)) <= 1e-12 * scale
                and abs(dn - 0.5 * (va * va - vb * vb)) <= 1e-12 * scale,
                "QR12 exact port exchange work",
            )
            delta[i] += df
            port_net += df if not s["oracle"] or i != 1 else 0.0
            cancel += abs(df + dn)
        if m["policy"] not in ("SENSOR_OFF", "TRACE_OFF"):
            x = phi(trace_node)
            decay = np.exp(-dt / np.array((0.5, 2, 8)))[None, :, None]
            expected = decay * expected + (1 - decay) * x[:, None, :]
        trace_error = max(
            trace_error, float(np.max(abs(expected - node["z"].reshape(count, 3, 135))))
        )
        if m["policy"] != "SENSOR_OFF":
            require(
                np.allclose(node["packet"][:, 5], -delta / dt, rtol=1e-12, atol=1e-13),
                "QR12 local transfer sensing",
            )
            require(
                np.allclose(
                    node["packet"][:, 6],
                    (node["packet"][:, 0] - old["previous"]) / dt,
                    rtol=1e-12,
                    atol=1e-13,
                ),
                "QR12 own causal derivative",
            )
        p = old["palette"].copy()
        ev = byevent.get(tick, [])
        for e in ev:
            i = int(e["neuron"])
            hmax = float(node[i]["z"][277:341].max())
            latch = hmax >= 0.02 or (hmax >= 0.005 and bool(old[i]["latch"]))
            require(int(e["latch"]) == int(latch), "QR12 local hysteresis")
            pair = (
                proposal(node[i], latch, int(old[i]["last"]), dt)
                if int(old[i]["budget"]) < 3
                else None
            )
            if e["cause"] == "EXTERNAL":
                pair = next(
                    (
                        (x, y)
                        for x in range(64)
                        for y in range(x + 1, 64)
                        if abs(x // 8 - y // 8) + abs(x % 8 - y % 8) == 1 and p[i, x] != p[i, y]
                    ),
                    None,
                )
            actual = None if int(e["a"]) < 0 else (int(e["a"]), int(e["b"]))
            # Candidate palettes are the pre-event palette; trace arrays are unchanged by swaps.
            if e["cause"] == "LOCAL":
                pre = node[i].copy()
                pre["palette"] = p[i]
                pair = (
                    proposal(pre, latch, int(old[i]["last"]), dt)
                    if int(old[i]["budget"]) < 3
                    else None
                )
            require(pair == actual, "QR12 independent local candidate ranking")
            if int(e["accepted"]):
                require(pair is not None, "QR12 no forced event")
                before = node_energy(dict(palette=p[i], u=u[i], v=v[i]), False)
                p[i, list(pair)] = p[i, list(pair[::-1])]
                after = node_energy(dict(palette=p[i], u=u[i], v=v[i]), False)
                dw = after - before
                require(
                    abs(dw - float(e["work"])) <= 1e-12 * max(before, after, 1e-30),
                    "QR12 actual switching work",
                )
                switch += dw
                positive += max(dw, 0)
                negative += max(-dw, 0)
            else:
                require(float(e["work"]) == 0, "QR12 veto is zero structural work")
        require(np.array_equal(p, node["palette"]), "QR12 only declared lawful swaps")
        for r in kicks:
            if int(r["half"]) == 2:
                i, j = int(r["neuron"]), int(r["module"])
                require(
                    m["forcing"].startswith("PERTURB")
                    and tick * dt == 24
                    and i == 1
                    and j == 9
                    and float(r["impulse"]) == 0.01,
                    "QR12 registered perturbation",
                )
                require(abs(v[i, j] - float(r["before"])) < 1e-12, "QR12 perturbation chronology")
                v[i, j] = float(r["after"])
                dw = 0.5 * (float(r["after"]) ** 2 - float(r["before"]) ** 2)
                cumulative += dw
                positive += max(dw, 0)
                negative += max(-dw, 0)
        step_error = max(
            step_error, float(np.max(abs(u - node["u"]))), float(np.max(abs(v - node["v"])))
        )
        for value, key in (
            (cumulative, "force_work"),
            (float(metrics[0]["switch_work"]) + switch, "switch_work"),
            (positive, "positive"),
            (negative, "negative"),
            (port_net, "port_net"),
            (cancel, "cancellation"),
        ):
            gate(f"{key}_{tick}", abs(value - float(metrics[index][key])) / scale, 1e-12)
    gate("all_trace_updates", trace_error, 1e-12)
    gate("all_intrinsic_updates", step_error, 1e-12)
    gate("all_damping", loss_error / scale, 1e-12)
    initial = (
        0.0
        if start == 0
        else float(rows(Path(m["checkpoint"]).parent / "metrics.csv")[start]["fluid"])
    )  # replaced below with exact full checkpoint energy.
    if start:
        pre = io.snapshot(m["checkpoint"])
        initial = energy(pre["fields"], 24 / pre["n"]) + math.fsum(
            node_energy(x, scalar) for x in pre["nodes"]
        )
        initial_accounts = pre["accounts"]
        offset = (
            initial
            - float(metrics[0]["force_work"])
            - float(metrics[0]["switch_work"])
            + float(metrics[0]["loss"])
        )
        # Initial histories retain prior work/loss: original total balance has zero baseline.
        initial = 0.0
        require(
            (folder / "branch-before.q12").read_bytes() == Path(m["checkpoint"]).read_bytes(),
            "QR12 exact branch ancestry",
        )
        del initial_accounts, offset
    residual = (
        max(
            abs(
                float(r["fluid"])
                + float(r["neural"])
                + float(r["loss"])
                - float(r["force_work"])
                - float(r["switch_work"])
                - initial
            )
            for r in metrics
        )
        / scale
    )
    gate("total_energy_balance", residual, 0.01)
    for path in sorted(folder.glob("*.q12")):
        state = io.snapshot(path)
        tick = state["tick"]
        h = 24 / state["n"]
        e = energy(state["fields"], h)
        if path.name.startswith("pre-") or path.name == "branch-before.q12":
            continue
        index = tick - start
        gate("fluid_energy_" + path.stem, abs(e - float(metrics[index]["fluid"])) / scale, 1e-12)
        require(
            np.array_equal(state["nodes"], a[index]["nodes"]),
            "QR12 checkpoint complete owned-state identity",
        )
        for i, pos in enumerate(state["positions"]):
            if m["policy"] != "SENSOR_OFF":
                require(
                    np.allclose(
                        io11.local(state["fields"], pos),
                        a[index]["nodes"][i]["packet"][:5],
                        rtol=1e-12,
                        atol=1e-14,
                    ),
                    "QR12 actual local packet reconstruction",
                )
        for axis in range(3):
            sl = [slice(None)] * 3
            sl[2 - axis] = -1
            require(
                np.count_nonzero(state["fields"][axis + 1][tuple(sl)]) == 0, "QR12 rigid wall slots"
            )
    if s["oracle"]:
        for p in folder.glob("*.q11"):
            f = io11.fluid(p)
            index = f["tick"]
            gate(
                "oracle_fluid_energy",
                abs(energy(f["fields"], 24 / f["n"]) - float(metrics[index]["fluid"])) / scale,
                1e-12,
            )
    result = dict(
        case=folder.name,
        raw=raw,
        sources=sources,
        valid=all(g["verdict"] == "PASS" for g in gates),
        gates=gates,
        trace_error=trace_error,
        step_error=step_error,
        energy_residual=residual,
    )
    cache.write_text(json.dumps(result, indent=2) + "\n")
    csv_write(folder / "audit-gates.csv", gates)
    return result


def audit_case(folder, fresh=False):
    import fcntl

    folder = Path(folder)
    with (folder.parent / ".audit.lock").open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        return _audit_case(folder, fresh)


def stage(root, fresh=False):
    root = Path(root)
    results = []
    for row in rows(root / "ledger.csv"):
        print("audit QR12", root.name, row["case"], flush=True)
        results.append(audit_case(root / row["case"], fresh))
    result = dict(
        stage=root.name,
        executions=len(results),
        valid=all(r["valid"] for r in results),
        failures=[r["case"] for r in results if not r["valid"]],
    )
    (root / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--fresh", action="store_true")
    a = p.parse_args()
    print(json.dumps(stage(a.root, a.fresh), indent=2))


if __name__ == "__main__":
    main()
