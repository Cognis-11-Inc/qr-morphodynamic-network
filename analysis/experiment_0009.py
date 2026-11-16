"""Independent QR9 standalone energy, analytic-field and refinement audit.

No Rust PASS fields are consumed. Full-field analytic comparisons reconstruct
continuum and semidiscrete solutions independently with NumPy tensor operations.
"""

import argparse
import csv
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np

from analysis.experiment_0005 import fnv, require

GRIDS = ((48, 0.05), (48, 0.025), (96, 0.025))
MODES = ((4, 0, 0), (6, 0, 0), (8, 0, 0), (4, 4, 4))
TIMES = (0, 6, 12, 24)


def reference():
    """Recompute referenced atmospheric coefficients without engine constants."""
    t, s = 20.0, 0.035
    rho = (
        999.92293295
        + 0.020341179217 * t
        - 0.0061624591598 * t**2
        + 0.000022614664708 * t**3
        - 0.000000046570659168 * t**4
        + s * (802.00240891 - 2.0005183488 * t + 0.016771024982 * t**2 - 0.000030600536746 * t**3)
        - 0.000016132224742 * s**2 * t**2
    )
    c = 1448.96 + 4.591 * t - 0.05304 * t**2 + 0.0002374 * t**3
    mu = (0.000042844324477 + 1 / (0.15700386464 * (t + 64.992620050) ** 2 - 91.296496657)) * (
        1
        + (1.540913604 + 0.019981117208 * t - 0.000095203865864 * t**2) * s
        + (7.9739318223 - 0.075614568881 * t + 0.00047237011074 * t**2) * s**2
    )
    return np.array((rho, c, rho * c**2, mu))


def decode(path):
    data = path.read_bytes()
    require(len(data) >= 80 and data[:8] == b"QR9AC001", "QR9 magic/length")
    version, n, tick, dt, kind, *mode = struct.unpack_from("<3Qd4Q", data, 8)
    require(version == 1 and 4 <= n <= 128 and dt in (0.05, 0.025), "QR9 metadata")
    require(kind <= 2 and tick <= 960 and all(x < n for x in mode), "QR9 fixture/clock")
    require(kind != 0 or any(mode), "QR9 nonzero mode")
    require(len(data) == 80 + 32 * n**3, "QR9 exact length")
    require(fnv(data[:-8]) == struct.unpack_from("<Q", data, len(data) - 8)[0], "QR9 checksum")
    fields = np.frombuffer(data, dtype="<f8", offset=72, count=4 * n**3).reshape(4, n, n, n)
    require(np.isfinite(fields).all(), "QR9 finite state")
    return dict(n=n, dt=dt, tick=tick, kind=kind, mode=mode, fields=fields)


def shapes(n, mode):
    """Continuum Neumann basis evaluated at actual cell/face coordinates."""
    h = 24 / n
    k = np.array(mode, dtype=float) * np.pi / 24
    norm = np.linalg.norm(k)
    coords = (np.arange(n) + 0.5) * h
    pressure = np.ones((n, n, n))
    cosine = []
    for axis in range(3):
        shape = [1] * 3
        shape[2 - axis] = n
        cosine.append(np.cos(k[axis] * coords).reshape(shape))
        pressure *= cosine[-1]
    velocity = np.zeros((3, n, n, n))
    for axis in range(3):
        shape = [1] * 3
        shape[2 - axis] = n
        wave = np.sin(k[axis] * (np.arange(n) + 1) * h)
        wave[-1] = 0
        velocity[axis] = k[axis] / norm * wave.reshape(shape)
        for other in range(3):
            if other != axis:
                velocity[axis] *= cosine[other]
    return np.concatenate((pressure[None], velocity)), k


def exact(n, mode, time, semidiscrete=False):
    basis, k = shapes(n, mode)
    h = 24 / n
    if semidiscrete:
        kh = 2 / h * (9 / 8 * np.sin(k * h / 2) - np.sin(3 * k * h / 2) / 24)
        # The registered modes have either one or three equal nonzero axes.
        require(
            np.allclose(kh / max(np.linalg.norm(kh), 1e-30), k / np.linalg.norm(k)),
            "mode direction",
        )
        frequency = np.linalg.norm(kh)
    else:
        frequency = np.linalg.norm(k)
    out = basis.copy()
    out[0] *= np.cos(frequency * time)
    out[1:] *= np.sin(frequency * time)
    return out


def relative(a, b):
    return float(np.linalg.norm((a - b).ravel()) / max(np.linalg.norm(b.ravel()), 1e-30))


def energy(fields, h):
    return float(0.5 * h**3 * np.sum(fields**2))


def density(fields):
    """Cell density with each internal face kinetic term split half to each cell."""
    result = 0.5 * fields[0] ** 2
    for axis in range(3):
        w = fields[axis + 1]
        result += 0.25 * w**2
        shifted = np.roll(w, 1, axis=2 - axis)
        lower = [slice(None)] * 3
        lower[2 - axis] = 0
        shifted[tuple(lower)] = 0
        result += 0.25 * shifted**2
    return result


def probe_sample(fields, point, cell_density=None):
    n = fields.shape[1]
    coords = (np.arange(n) + 0.5) * (24 / n)
    xyz = [int(np.argmin(abs(coords - x))) for x in point]
    zyx = tuple(reversed(xyz))
    values = [fields[0][zyx]]
    for axis in range(3):
        lower = list(zyx)
        lower[2 - axis] -= 1
        before = 0 if xyz[axis] == 0 else fields[axis + 1][tuple(lower)]
        values.append(0.5 * (fields[axis + 1][zyx] + before))
    values.append((density(fields) if cell_density is None else cell_density)[zyx])
    return np.array(values)


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def fixture_name(mode):
    return "mode" + "-".join(map(str, mode))


def layout():
    for mode in MODES:
        for n, dt in GRIDS:
            yield f"{fixture_name(mode)}_n{n}_dt{dt}", n, dt, mode
    for n, dt in GRIDS:
        yield f"gaussian_n{n}_dt{dt}", n, dt, None
    yield "zero_n48_dt0.05", 48, 0.05, None
    yield "mode8-0-0_n48_dt0.05_repeat", 48, 0.05, (8, 0, 0)


def csv_write(path, records):
    if records:
        with path.open("w") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)


def audit(root):
    """Reconstruct all prerequisite decisions, retaining every failed gate."""
    gates, checkpoints, summaries = [], [], []

    def gate(case, name, value, limit, passed=None):
        result = bool(value <= limit if passed is None else passed)
        gates.append(
            dict(case=case, gate=name, value=float(value), limit=float(limit), passed=result)
        )

    physical = np.array([float(x) for x in rows(root / "reference.csv")[0].values()])
    gate("reference", "properties_reconstruction", relative(physical, reference()), 1e-12)
    ledger = rows(root / "ledger.csv")
    require(
        {x[0] for x in layout()} == {x["case"] for x in ledger}, "complete exact 17-case matrix"
    )
    require(len(ledger) == 17 and all(x["status"] == "COMPLETE" for x in ledger), "ledger complete")
    for name, n, dt, mode in layout():
        folder = root / name
        require((folder / "COMPLETE").exists(), name + " incomplete")
        print("auditing", name, flush=True)
        metrics = rows(folder / "metrics.csv")
        expected = round(24 / dt) + 1
        require(len(metrics) == expected, name + " tick coverage")
        for tick, row in enumerate(metrics):
            require(
                int(row["tick"]) == tick and float(row["time"]) == tick * dt,
                "contiguous physical clock",
            )
            require(all(math.isfinite(float(v)) for v in row.values()), "finite metrics")
        initial = float(metrics[0]["energy"])
        drift = max(abs(float(x["energy"]) - initial) for x in metrics) / max(initial, 1e-30)
        gate(name, "actual_energy_drift", drift, 0.0025 if n == 96 else 0.01)
        probes = rows(folder / "probes.csv")
        require(len(probes) == expected * 21, "probe tick coverage")
        maximum_error = maximum_time_error = 0.0
        for time in TIMES:
            tick = round(time / dt)
            f = decode(folder / f"{tick:06}.q9a")
            require((f["n"], f["dt"], f["tick"]) == (n, dt, tick), "checkpoint identity")
            require(
                f["kind"] == (0 if mode else 2 if name.startswith("zero") else 1),
                "fixture identity",
            )
            if mode:
                require(f["mode"] == list(mode), "mode identity")
            fields = f["fields"]
            cell_density = density(fields)
            actual = energy(fields, 24 / n)
            reported = float(metrics[tick]["energy"])
            gate(
                name,
                f"energy_reconstruction_t{time}",
                abs(actual - reported) / max(actual, 1e-30),
                1e-12,
            )
            gate(
                name,
                f"partition_sum_t{time}",
                abs(float(density(fields).sum()) * (24 / n) ** 3 - actual) / max(actual, 1e-30),
                1e-12,
            )
            for axis in range(3):
                wall = [slice(None)] * 3
                wall[2 - axis] = -1
                gate(
                    name,
                    f"rigid_wall_axis{axis}_t{time}",
                    float(np.max(abs(fields[axis + 1][tuple(wall)]))),
                    0,
                )
            for probe in probes[tick * 21 : (tick + 1) * 21]:
                point = [12.0] * 3
                point[int(probe["axis"])] += float(probe["offset"])
                measured = np.array(
                    [float(probe[k]) for k in ("q", "wx", "wy", "wz", "energy_density")]
                )
                require(
                    np.allclose(
                        measured, probe_sample(fields, point, cell_density), rtol=1e-12, atol=1e-14
                    ),
                    "raw probe reconstruction",
                )
            if mode:
                truth = exact(n, mode, time)
                error = relative(fields, truth)
                terr = relative(fields, exact(n, mode, time, True))
                basis, k = shapes(n, mode)
                norm = float(np.sum(basis[0] ** 2))
                projection = (
                    np.array([np.sum(fields[0] * basis[0]), np.sum(fields[1:] * basis[1:])]) / norm
                )
                require(
                    np.allclose(
                        projection,
                        [
                            float(metrics[tick][key])
                            for key in ("pressure_projection", "velocity_projection")
                        ],
                        rtol=1e-10,
                        atol=1e-12,
                    ),
                    "modal projection reconstruction",
                )
                angle = np.linalg.norm(k) * time
                phase = float(np.angle(complex(*projection) * np.exp(-1j * angle)))
                amplitude = float(abs(np.linalg.norm(projection) - 1))
                speed_error = abs(phase / angle) if time else 0
                record = dict(
                    case=name,
                    n=n,
                    dt=dt,
                    time=time,
                    continuum_error=error,
                    semidiscrete_time_error=terr,
                    phase_error=phase,
                    amplitude_error=amplitude,
                    speed_error=speed_error,
                )
                checkpoints.append(record)
                if time:
                    maximum_error = max(maximum_error, error)
                    maximum_time_error = max(maximum_time_error, terr)
                    gate(name, f"continuum_field_t{time}", error, 0.015 if n == 96 else 0.05)
                    gate(name, f"modal_phase_t{time}", abs(phase), 0.01 if n == 96 else 0.03)
                    gate(name, f"modal_amplitude_t{time}", amplitude, 0.01)
                    gate(name, f"effective_speed_t{time}", speed_error, 0.0025 if n == 96 else 0.01)
            elif name.startswith("gaussian"):
                e = density(fields)
                for axis in range(3):
                    gate(
                        name,
                        f"reflection_symmetry{axis}_t{time}",
                        relative(e, np.flip(e, axis=axis)),
                        1e-10,
                    )
                gate(
                    name, f"permutation_symmetry_t{time}", relative(e, e.transpose(2, 0, 1)), 1e-10
                )
                if time == 0:
                    gate(name, "initial_energy_matching", abs(actual - 1), 1e-12)
            else:
                gate(name, f"zero_fields_t{time}", float(np.max(abs(fields))), 0)
        if name.startswith("zero"):
            gate(
                name,
                "zero_every_tick_metrics",
                max(
                    abs(float(x[k]))
                    for x in metrics
                    for k in ("energy", "max_pressure", "max_velocity")
                ),
                0,
            )
            gate(
                name,
                "zero_every_tick_probes",
                max(
                    abs(float(x[k]))
                    for x in probes
                    for k in ("q", "wx", "wy", "wz", "energy_density")
                ),
                0,
            )
        summaries.append(
            dict(case=name, drift=drift, continuum_max=maximum_error, time_max=maximum_time_error)
        )
    for mode in MODES:
        prefix = fixture_name(mode)
        selected = [
            next(s for s in summaries if s["case"] == f"{prefix}_n{n}_dt{dt}") for n, dt in GRIDS
        ]
        if selected[0]["time_max"] > 1e-8:
            gate(
                prefix,
                "temporal_error_reduction",
                selected[1]["time_max"] / selected[0]["time_max"],
                0.35,
            )
        if selected[0]["continuum_max"] > 1e-6:
            gate(
                prefix,
                "spatial_error_reduction",
                selected[2]["continuum_max"] / selected[0]["continuum_max"],
                0.35,
            )
    original = root / "mode8-0-0_n48_dt0.05"
    repeat = root / "mode8-0-0_n48_dt0.05_repeat"
    names = sorted(p.name for p in original.iterdir())
    require(names == sorted(p.name for p in repeat.iterdir()), "repeat coverage")
    gate(
        "repeat",
        "all_raw_bytes",
        sum((original / p).read_bytes() != (repeat / p).read_bytes() for p in names),
        0,
    )
    failed = [g for g in gates if not g["passed"]]
    result = dict(
        schema=1,
        executions=17,
        checkpoints=68,
        gates=len(gates),
        failures=failed,
        S1="FAIL" if failed else "PASS",
        downstream_authorized=not failed,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    csv_write(root / "gates.csv", gates)
    csv_write(root / "modal_errors.csv", checkpoints)
    csv_write(root / "case_summary.csv", summaries)
    (root / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    audit(args.root)


if __name__ == "__main__":
    main()
