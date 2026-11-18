"""Independent QR10 numerical rehabilitation: full fields, fsum and separated errors."""

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np

from analysis import experiment_0009 as old
from analysis.experiment_0005 import fnv, require

GRIDS = ((24, 0.0125), (48, 0.05), (48, 0.025), (48, 0.0125), (96, 0.0125))


def decode(path):
    data = path.read_bytes()
    require(len(data) >= 80 and data[:8] == b"QR10AC01", "QR10 magic")
    version, n, tick, dt, kind, *mode = struct.unpack_from("<3Qd4Q", data, 8)
    require(version == 1 and n in (24, 48, 96), "QR10 grid/version")
    require(dt in (0.05, 0.025, 0.0125) and tick <= 19200, "QR10 clock")
    require(kind in (0, 1, 2) and all(x < n for x in mode), "QR10 fixture")
    require(kind != 0 or any(mode), "nonzero mode")
    require(len(data) == 80 + 32 * n**3, "QR10 length")
    require(fnv(data[:-8]) == struct.unpack_from("<Q", data, len(data) - 8)[0], "QR10 checksum")
    fields = np.frombuffer(data, dtype="<f8", offset=72).copy()[:-1].reshape(4, n, n, n)
    require(np.isfinite(fields).all(), "finite fields")
    return dict(n=n, dt=dt, tick=tick, kind=kind, mode=mode, fields=fields)


def energy(fields, h):
    return 0.5 * h**3 * math.fsum(float(x) * float(x) for x in fields.ravel())


def split_exact(n, mode, time, dt):
    basis, k = old.shapes(n, mode)
    h = 24 / n
    kh = 2 / h * (9 / 8 * np.sin(k * h / 2) - np.sin(3 * k * h / 2) / 24)
    omega = float(np.linalg.norm(kh))
    numerical = 2 * math.asin(dt * omega / 2) / dt
    result = basis.copy()
    result[0] *= math.cos(numerical * time)
    result[1:] *= math.sin(numerical * time) / math.sqrt(1 - (dt * omega / 2) ** 2)
    return result


def layout():
    for mode in old.MODES:
        for n, dt in GRIDS:
            yield f"{old.fixture_name(mode)}_n{n}_dt{dt}", n, dt, mode, 24
    for n, dt in ((48, 0.05), (48, 0.025), (96, 0.0125)):
        yield f"gaussian_n{n}_dt{dt}", n, dt, None, 24
    yield "zero_n48_dt0.05", 48, 0.05, None, 24
    yield "mode8-0-0_n48_dt0.05_repeat", 48, 0.05, (8, 0, 0), 24
    yield "mode8-0-0_n48_dt0.05_long", 48, 0.05, (8, 0, 0), 240


def audit(root):
    gates, observations, summaries, rates = [], [], [], []

    def gate(category, case, name, value, limit, lower=0):
        gates.append(
            dict(
                category=category,
                case=case,
                gate=name,
                value=float(value),
                lower=lower,
                limit=limit,
                verdict="PASS" if lower <= value <= limit else "FAIL",
            )
        )

    ledger = old.rows(root / "ledger.csv")
    require(
        len(ledger) == 26 and {r["case"] for r in ledger} == {x[0] for x in layout()},
        "exact matrix",
    )
    require(all(r["status"] == "COMPLETE" for r in ledger), "complete execution")
    for name, n, dt, mode, horizon in layout():
        print("audit", name, flush=True)
        folder = root / name
        metrics = old.rows(folder / "metrics.csv")
        ticks = round(horizon / dt)
        require(len(metrics) == ticks + 1, "every tick")
        for i, row in enumerate(metrics):
            require(int(row["tick"]) == i and float(row["time"]) == i * dt, "clock")
            require(all(math.isfinite(float(x)) for x in row.values()), "finite diagnostics")
        probes = old.rows(folder / "probes.csv")
        require(len(probes) == (ticks + 1) * 21, "probe coverage")
        initial = float(metrics[0]["energy"])
        drift = max(abs(float(r["energy"]) - initial) for r in metrics) / max(initial, 1e-30)
        gate("D", name, "actual_energy_drift", drift, 0.001 if n == 96 else 0.003)
        temporal, spatial, continuum = [], [], []
        for time in (0, horizon / 4, horizon / 2, horizon):
            tick = round(time / dt)
            f = decode(folder / f"{tick:06}.q10")
            require((f["n"], f["dt"], f["tick"]) == (n, dt, tick), "checkpoint identity")
            require(f["kind"] == (0 if mode else 2 if name.startswith("zero") else 1), "fixture")
            require(not mode or f["mode"] == list(mode), "mode")
            field = f["fields"]
            actual = energy(field, 24 / n)
            reported = float(metrics[tick]["energy"])
            scale = max(actual, 1e-30)
            gate("D", name, f"accounting_t{time}", abs(actual - reported) / scale, 1e-12)
            naive = 0.0
            for x in field.ravel():
                naive += float(x) * float(x)
            naive *= 0.5 * (24 / n) ** 3
            partition = math.fsum(float(x) for x in old.density(field).ravel()) * (24 / n) ** 3
            gate("D", name, f"partition_t{time}", abs(partition - actual) / scale, 1e-12)
            for axis in range(3):
                wall = [slice(None)] * 3
                wall[2 - axis] = -1
                gate(
                    "E",
                    name,
                    f"wall{axis}_t{time}",
                    float(np.max(abs(field[axis + 1][tuple(wall)]))),
                    0,
                )
            cell_density = old.density(field)
            for probe in probes[tick * 21 : (tick + 1) * 21]:
                require(int(probe["tick"]) == tick, "probe clock")
                point = [12.0] * 3
                point[int(probe["axis"])] += float(probe["offset"])
                measured = np.array(
                    [float(probe[k]) for k in ("q", "wx", "wy", "wz", "energy_density")]
                )
                require(
                    np.allclose(
                        measured,
                        old.probe_sample(field, point, cell_density),
                        rtol=1e-12,
                        atol=1e-14,
                    ),
                    "probe reconstruction",
                )
            if name.startswith("gaussian") and time == 0:
                gate("D", name, "initial_unit_energy", abs(actual - 1), 1e-12)
            obs = dict(
                case=name,
                time=time,
                energy_fsum=actual,
                energy_reported=reported,
                accounting_absolute=abs(actual - reported),
                naive_relative=abs(naive - actual) / scale,
            )
            if mode:
                truth = old.exact(n, mode, time)
                semi = old.exact(n, mode, time, True)
                split = split_exact(n, mode, time, dt)
                residual = old.relative(field, split)
                gate("E", name, f"split_reference_t{time}", residual, 1e-10)
                ce, te = old.relative(field, truth), old.relative(field, semi)
                corrected = field - (split - semi)
                se = old.relative(corrected, truth)
                norm = float(np.linalg.norm(truth.ravel()))
                basis, k = old.shapes(n, mode)
                normp = float(np.sum(basis[0] ** 2))
                p = float(np.sum(field[0] * basis[0]) / normp)
                v = float(np.sum(field[1:] * basis[1:]) / normp)
                angle = float(np.linalg.norm(k)) * time
                phase = float(np.angle(complex(p, v) * np.exp(-1j * angle)))
                amp = abs(math.hypot(p, v) - 1)
                speed = abs(phase / angle) if time else 0
                obs.update(
                    continuum_error=ce,
                    temporal_error=te,
                    corrected_spatial_error=se,
                    analytical_spatial_error=old.relative(semi, truth),
                    split_residual=residual,
                    absolute_rms=float(np.sqrt(np.mean((field - truth) ** 2))),
                    pressure_error=float(np.linalg.norm((field[0] - truth[0]).ravel()) / norm),
                    velocity_error=float(np.linalg.norm((field[1:] - truth[1:]).ravel()) / norm),
                    phase=phase,
                    amplitude=amp,
                    speed_error=speed,
                )
                if time and horizon == 24:
                    temporal.append(te)
                    spatial.append(se)
                    continuum.append(ce)
                    if n >= 48:
                        for key, value, limit in (
                            ("field", ce, 0.0015 if n == 96 else 0.01),
                            ("phase", abs(phase), 0.015),
                            ("amplitude", amp, 0.003),
                            ("speed", speed, 0.003),
                        ):
                            gate("A", name, f"{key}_t{time}", value, limit)
            elif name.startswith("gaussian"):
                density = old.density(field)
                for axis in range(3):
                    gate(
                        "E",
                        name,
                        f"reflection{axis}_t{time}",
                        old.relative(density, np.flip(density, axis)),
                        1e-10,
                    )
                gate(
                    "E",
                    name,
                    f"permutation_t{time}",
                    old.relative(density, density.transpose(2, 0, 1)),
                    1e-10,
                )
            else:
                gate("E", name, f"zero_t{time}", float(np.max(abs(field))), 0)
            observations.append(obs)
        if name.startswith("zero"):
            gate(
                "E",
                name,
                "zero_every_tick",
                max(
                    abs(float(r[k]))
                    for r in metrics
                    for k in ("energy", "max_pressure", "max_velocity")
                ),
                0,
            )
        summaries.append(
            dict(
                case=name,
                drift=drift,
                temporal_max=max(temporal, default=0),
                spatial_max=max(spatial, default=0),
                continuum_max=max(continuum, default=0),
            )
        )
    lookup = {r["case"]: r for r in summaries}
    for mode in old.MODES:
        prefix = old.fixture_name(mode)
        for category, grids, key, limits in (
            ("B", ((48, 0.05), (48, 0.025), (48, 0.0125)), "temporal_max", (0.2, 0.3)),
            ("C", ((24, 0.0125), (48, 0.0125), (96, 0.0125)), "spatial_max", (0.04, 0.09)),
        ):
            values = [lookup[f"{prefix}_n{n}_dt{dt}"][key] for n, dt in grids]
            for i in range(2):
                if values[i] < 1e-10:
                    rates.append(
                        dict(
                            mode=prefix,
                            category=category,
                            pair=i,
                            ratio=None,
                            order=None,
                            verdict="INDETERMINATE",
                        )
                    )
                else:
                    ratio = values[i + 1] / values[i]
                    gate(category, prefix, f"ratio{i}", ratio, limits[1], limits[0])
                    rates.append(
                        dict(
                            mode=prefix,
                            category=category,
                            pair=i,
                            ratio=ratio,
                            order=-math.log2(ratio),
                            verdict=gates[-1]["verdict"],
                        )
                    )
    original = root / "mode8-0-0_n48_dt0.05"
    repeat = root / "mode8-0-0_n48_dt0.05_repeat"
    require(
        sorted(p.name for p in original.iterdir()) == sorted(p.name for p in repeat.iterdir()),
        "repeat files",
    )
    gate(
        "E",
        "repeat",
        "bytes",
        sum(p.read_bytes() != (repeat / p.name).read_bytes() for p in original.iterdir()),
        0,
    )
    categories = {
        c: "FAIL"
        if any(g["verdict"] == "FAIL" for g in gates if g["category"] == c)
        else "INDETERMINATE"
        if any(r["verdict"] == "INDETERMINATE" for r in rates if r["category"] == c)
        else "PASS"
        for c in "ABCDE"
    }
    result = dict(
        schema=1,
        executions=26,
        checkpoints=len(observations),
        categories=categories,
        level_A="PASS" if all(categories[c] == "PASS" for c in "ADE") else "FAIL",
        level_B="PASS" if all(v == "PASS" for v in categories.values()) else "INDETERMINATE",
        failures=[g for g in gates if g["verdict"] == "FAIL"],
        verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    for filename, records in (
        ("gates.csv", gates),
        ("observations.csv", observations),
        ("summary.csv", summaries),
        ("rates.csv", rates),
    ):
        # Heterogeneous mode/zero observations retain explicit empty columns.
        import csv

        keys = list(dict.fromkeys(k for r in records for k in r))
        with (root / filename).open("w") as stream:
            writer = csv.DictWriter(stream, fieldnames=keys)
            writer.writeheader()
            writer.writerows(records)
    (root / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    audit(parser.parse_args().root)


if __name__ == "__main__":
    main()
