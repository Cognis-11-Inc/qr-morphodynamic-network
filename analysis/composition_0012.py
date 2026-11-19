"""Independent open-operator composition; predictions never consume direct outcomes."""

# Long literal proof/scope text is retained as complete sentences.
# ruff: noqa: E501

import argparse
import json
import time
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from analysis import io_0011 as io11
from analysis import io_0012 as io
from analysis.audit_0011 import neural_free, phi
from analysis.audit_0012 import sha, source
from analysis.audit_coupling_0010 import seeded_palette
from analysis.experiment_0005 import require
from analysis.experiment_0009 import csv_write, relative
from analysis.plan_0012 import plan


@dataclass(frozen=True)
class Interface:
    n: int = 48
    dt: float = 0.05
    units: str = "normalized"
    orientation: str = "positive-face-x-fast"
    fluid_owner: int = 1
    nodes: tuple = (0, 1)


def compile_modules(modules, n=48, dt=0.05, count=4):
    reference = Interface(n=n, dt=dt)
    seen = []
    for module in modules:
        require(
            (module.n, module.dt, module.units, module.orientation, module.fluid_owner)
            == (
                reference.n,
                reference.dt,
                reference.units,
                reference.orientation,
                reference.fluid_owner,
            ),
            "QR12 incompatible open interface",
        )
        seen.extend(module.nodes)
    require(sorted(seen) == list(range(count)), "QR12 node ownership/ports")
    return tuple(("PORT", i, m) for i in seen for m in (9, 27))


def ordinary_validator(modules, n=48, dt=0.05, count=4):
    # Ordinary physical validation uses the SAME constraints, without categorical terminology.
    if any(
        m.n != n
        or m.dt != dt
        or m.units != "normalized"
        or m.orientation != "positive-face-x-fast"
        or m.fluid_owner != 1
        for m in modules
    ):
        return False
    return sorted(i for m in modules for i in m.nodes) == list(range(count))


def mathematical_tests(root):
    root = Path(root)
    root.mkdir(exist_ok=True, parents=True)
    a = ("kick0", "forward_ports")
    b = ("fluid", "intrinsic")
    c = ("reverse_ports", "kick1", "sense", "event")
    require(
        (a + b) + c == a + (b + c) and () + a == a and a + () == a, "QR12 exact word category laws"
    )
    valid = (Interface(), Interface(nodes=(2, 3)))
    faults = [
        replace(valid[1], n=96),
        replace(valid[1], dt=0.025),
        replace(valid[1], units="untyped"),
        replace(valid[1], orientation="negative-face"),
        replace(valid[1], fluid_owner=2),
        replace(valid[1], nodes=(2,)),
    ]
    records = []
    for name, fault in zip(
        ("grid", "dt", "units", "orientation", "owner", "missing-node"), faults, strict=True
    ):
        rejected = False
        try:
            compile_modules((valid[0], fault))
        except ValueError:
            rejected = True
        records.append(
            dict(
                fault=name,
                categorical_rejected=rejected,
                ordinary_rejected=not ordinary_validator((valid[0], fault)),
            )
        )
    require(all(r["categorical_rejected"] for r in records), "QR12 invalid compositions rejected")
    compile_modules(valid)
    compile_modules((Interface(nodes=(0, 2)), Interface(nodes=(1, 3))))
    timings = {}
    for name, fun in (
        ("typed_compile", compile_modules),
        ("ordinary_validate", ordinary_validator),
    ):
        start = time.perf_counter()
        for _ in range(10000):
            fun(valid)
        timings[name + "_10000_seconds"] = time.perf_counter() - start
    r = dict(
        MATHEMATICAL_VALIDITY="PASS",
        ENGINEERING_UTILITY="PASS"
        if any(r["categorical_rejected"] and not r["ordinary_rejected"] for r in records)
        else "FAIL",
        exact_word_identity=True,
        exact_word_associativity=True,
        proof="Partial-function composition: domain={x in dom(f):f(x) in dom(g)}. Both associations are defined exactly when x,f(x),g(f(x)) are defined; values agree by the same ordered evaluation. Identity is total identity on each typed valid-state set. Illegal machine results are undefined; no reassociation of floating arithmetic.",
        interface_tests=records,
        timings=timings,
        limitation="Typed open-system engineering is valid, but a conventional physical validator checks the same constraints; no unique categorical advantage is inferred.",
    )
    (root / "formal-verification.json").write_text(json.dumps(r, indent=2) + "\n")
    csv_write(root / "interface-tests.csv", records)
    return r


def fluid_step(fields, dt):
    n = fields.shape[1]
    a = dt / (24 / n)

    def pressure(factor):
        q = fields[0]
        for j in range(3):
            axis = 2 - j
            z = np.moveaxis(q, axis, -1)
            v = np.moveaxis(fields[j + 1], axis, -1)[..., :-1] * a * factor
            z[..., :-1] -= (9 / 8) * v
            z[..., 1:] += (9 / 8) * v
            z[..., 2:] -= v[..., :-1] / 24
            z[..., -1] -= v[..., -1] / 24
            z[..., :-2] += v[..., 1:] / 24
            z[..., 0] += v[..., 0] / 24

    pressure(0.5)
    for j in range(3):
        axis = 2 - j
        q = np.moveaxis(fields[0], axis, -1)
        w = np.moveaxis(fields[j + 1], axis, -1)
        back = np.concatenate((q[..., :1], q[..., :-2]), axis=-1)
        ahead = np.concatenate((q[..., 2:], q[..., -1:]), axis=-1)
        w[..., :-1] -= a * ((9 / 8) * (q[..., 1:] - q[..., :-1]) - (ahead - back) / 24)
    pressure(0.5)


def predict_case(config, dest):
    n, dt, geometry = config["n"], config["dt"], config["geometry"]
    positions = io.positions(geometry)
    count = len(positions)
    ids = [2182, 2186, 2184, 2188]
    selected = [2, 3] if geometry == 21 else list(range(count))
    nodes = np.zeros(count, dtype=io.NODE)
    for i, index in enumerate(selected):
        nodes["palette"][i] = seeded_palette(427, ids[index])
    modules = (
        (Interface(n, dt, nodes=tuple(range(min(2, count)))),)
        if count == 2
        else (Interface(n, dt, nodes=(0, 1)), Interface(n, dt, nodes=(2, 3)))
    )
    schedule = compile_modules(modules, n, dt, count)
    fields = np.zeros((4, n, n, n))
    h = 24 / n
    scale = h**1.5
    kernels = [io11.kernel(n, p) for p in positions]
    norms = [float(np.linalg.norm(w)) for _, w in kernels]
    losses = np.zeros(count)
    force_work = 0.0
    saved = []
    start = time.perf_counter()
    for tick in range(round(8 / dt) + 1):
        if tick:
            f = source("PULSE", (tick - 0.5) * dt)
            impulse = 0.5 * dt * f
            transferred = np.zeros(count)
            old = nodes["v"][0, 9]
            nodes["v"][0, 9] += impulse
            force_work += 0.5 * (nodes["v"][0, 9] ** 2 - old**2)
            for half in (0, 1):
                if half == 1:
                    fluid_step(fields, dt)
                    u, v, loss = neural_free(nodes["palette"], nodes["u"], nodes["v"], dt)
                    nodes["u"] = u
                    nodes["v"] = v
                    losses += loss
                for _, i, m in schedule if half == 0 else reversed(schedule):
                    ids, w = kernels[i]
                    q = fields[0].ravel()
                    norm = norms[i]
                    x = scale / norm * np.dot(w, q[ids])
                    v = nodes["v"][i, m]
                    angle = 0.1 * norm / scale * dt * 0.5
                    c, s = np.cos(angle), np.sin(angle)
                    nx = c * x + s * v
                    nv = c * v - s * x
                    e0 = 0.5 * h**3 * np.sum(q[ids] ** 2)
                    q[ids] += w / norm / scale * (nx - x)
                    transferred[i] += 0.5 * h**3 * np.sum(q[ids] ** 2) - e0
                    nodes["v"][i, m] = nv
                if half == 1:
                    old = nodes["v"][0, 9]
                    nodes["v"][0, 9] += impulse
                    force_work += 0.5 * (nodes["v"][0, 9] ** 2 - old**2)
            for i, p in enumerate(positions):
                values = io11.local(fields, p)
                previous = nodes["previous"][i]
                nodes["packet"][i] = np.r_[
                    values, -transferred[i] / dt, (values[0] - previous) / dt
                ]
                nodes["previous"][i] = values[0]
            decay = np.exp(-dt / np.array((0.5, 2, 8)))[None, :, None]
            nodes["z"] = (
                decay * nodes["z"].reshape(count, 3, 135) + (1 - decay) * phi(nodes)[:, None, :]
            ).reshape(count, 405)
            nodes["age"] = tick
            nodes["loss"] = losses
            maximum = nodes["z"][:, 277:341].max(axis=1)
            nodes["latch"] = np.where(
                maximum >= 0.02, 1, np.where(maximum < 0.005, 0, nodes["latch"])
            )
        if tick in (0, round(4 / dt), round(8 / dt)):
            path = dest / (config["case"] + f"-{tick:06}.npz")
            np.savez(path, fields=fields, nodes=nodes, force_work=force_work)
            saved.append(path)
    return dict(
        case=config["case"],
        seconds=time.perf_counter() - start,
        files={p.name: sha(p) for p in saved},
        inputs=config,
    )


def freeze_predictions(root):
    root = Path(root)
    require(not (root / "e").exists(), "QR12 independent prediction before direct E outcomes")
    dest = root / "predictions"
    dest.mkdir()
    results = [predict_case(c, dest) for c in plan(root, "e")]
    r = dict(
        frozen=True,
        source_sha256=sha(Path(__file__)),
        predictions=results,
        scope="No direct trajectory files read; seed427, fixed registered interfaces/input and independent equations only.",
    )
    (dest / "freeze.json").write_text(json.dumps(r, indent=2) + "\n")
    (root / "PREDICTIONS_SHA256.txt").write_text(
        sha(dest / "freeze.json") + "  predictions/freeze.json\n"
    )
    return r


def review(root):
    root = Path(root)
    dest = root / "predictions"
    frozen = json.loads((dest / "freeze.json").read_text())
    require(
        sha(dest / "freeze.json") == (root / "PREDICTIONS_SHA256.txt").read_text().split()[0],
        "QR12 frozen predictions unchanged",
    )
    results = []
    for record in frozen["predictions"]:
        actual = checkpoints = root / "e" / record["case"]
        for name, digest in record["files"].items():
            p = dest / name
            require(sha(p) == digest, "QR12 predicted bytes unchanged")
            pred = np.load(p)
            tick = int(p.stem.split("-")[-1])
            direct = io.snapshot(actual / f"{tick:06}.q12")
            if tick == 0:
                continue
            e = relative(pred["fields"], direct["fields"])
            ne = relative(
                np.stack((pred["nodes"]["u"], pred["nodes"]["v"])),
                np.stack((direct["nodes"]["u"], direct["nodes"]["v"])),
            )
            remote = direct["nodes"][1:]
            remote_norm = float(np.linalg.norm(np.stack((remote["u"], remote["v"]))))
            prediction_remote = float(
                np.linalg.norm(
                    np.stack(
                        (pred["nodes"]["u"][1:] - remote["u"], pred["nodes"]["v"][1:] - remote["v"])
                    )
                )
            )
            results.append(
                dict(
                    case=record["case"],
                    tick=tick,
                    field_error=e,
                    neural_error=ne,
                    trace_error=relative(pred["nodes"]["z"], direct["nodes"]["z"]),
                    remote_norm=remote_norm,
                    prediction_remote_error=prediction_remote,
                    closed_product_remote_error=remote_norm,
                )
            )
    from analysis.gates_0012 import compare

    refinement = [compare(root / "e/DIRECT4_P", root / "e" / ("DIRECT4_" + g)) for g in "TF"]
    valid = all(
        max(r[k] for k in ("field_error", "neural_error", "trace_error")) <= 1e-10 for r in results
    ) and all(max(v.values()) <= 0.1 for v in refinement)
    informative = [
        r for r in results if r["case"].startswith("DIRECT4") and r["remote_norm"] > 1e-10
    ]
    predictive = (
        valid
        and bool(informative)
        and all(
            r["prediction_remote_error"] <= 0.1 * r["closed_product_remote_error"]
            for r in informative
        )
    )
    r = dict(
        PHYSICAL_AGREEMENT="PASS" if valid else "INDETERMINATE",
        PREDICTIVE_UTILITY="PASS" if predictive else "FAIL" if valid else "INDETERMINATE",
        comparisons=results,
        refinement=refinement,
        scope="Independent open-operator numerical prediction; no claim of categorical superiority over ordinary modular coupled simulation.",
    )
    csv_write(root / "composition-errors.csv", results)
    (root / "composition-verification.json").write_text(json.dumps(r, indent=2) + "\n")
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=["formal", "predict", "review"])
    p.add_argument("root", type=Path)
    a = p.parse_args()
    print(
        json.dumps(
            {"formal": mathematical_tests, "predict": freeze_predictions, "review": review}[
                a.stage
            ](a.root),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
