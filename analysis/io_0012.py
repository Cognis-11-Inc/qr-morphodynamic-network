"""QR12 complete shared-fluid checkpoints and every-tick owned-node observations."""

import struct
from pathlib import Path

import numpy as np

from analysis import io_0011 as old
from analysis.experiment_0005 import fnv, require

NODE = np.dtype(
    old.NODE.descr
    + [
        (k, "<f8" if k in ("event_work_sum", "event_work_correction") else "<u8")
        for k in (
            "latch",
            "last",
            "events",
            "attempts",
            "event_work_sum",
            "event_work_correction",
            "budget",
            "vetoes",
        )
    ]
)
assert NODE.itemsize == 4480


def snapshot(path):
    b = Path(path).read_bytes()
    require(len(b) >= 152 and b[:8] == b"QR12FUL1", "QR12 complete checkpoint magic")
    require(fnv(b[:-8]) == struct.unpack_from("<Q", b, len(b) - 8)[0], "QR12 complete checksum")
    version, n, tick, dt, seed, count, geometry, scalar, mask = struct.unpack_from("<3Qd5Q", b, 8)
    require(
        version == 1 and 4 <= n <= 128 and count in (1, 2, 4) and dt in (0.05, 0.025),
        "QR12 state dimensions",
    )
    require(len(b) == 152 + 4600 * count + 32 * n**3, "QR12 exact complete length")
    pos = np.frombuffer(b, dtype="<f8", offset=80, count=3 * count).reshape(count, 3)
    off = 80 + 24 * count
    fields = np.frombuffer(b, dtype="<f8", offset=off, count=4 * n**3).reshape(4, n, n, n)
    off += 32 * n**3
    nodes = np.frombuffer(b, dtype=NODE, offset=off, count=count)
    off += 4480 * count
    accounts = np.frombuffer(b, dtype="<f8", offset=off, count=8)
    ports = np.frombuffer(b, dtype="<f8", offset=off + 64, count=12 * count).reshape(count, 2, 6)
    require(
        np.isfinite(fields).all() and np.isfinite(accounts).all() and np.isfinite(ports).all(),
        "QR12 finite complete physical state",
    )
    valid(nodes)
    require(
        (nodes["age"] == tick).all()
        and (nodes["events"] <= 3).all()
        and np.array_equal(nodes["events"], nodes["budget"]),
        "QR12 clock and local event budget",
    )
    return dict(
        n=n,
        tick=tick,
        dt=dt,
        seed=seed,
        count=count,
        geometry=geometry,
        scalar=scalar,
        mask=mask,
        positions=pos,
        fields=fields,
        nodes=nodes,
        accounts=accounts,
        ports=ports,
    )


def valid(nodes):
    old.valid_nodes(nodes)
    require(
        (nodes["latch"] <= 1).all()
        and np.isfinite(nodes["event_work_sum"]).all()
        and np.isfinite(nodes["event_work_correction"]).all(),
        "QR12 controller validity",
    )


def stream(folder):
    folder = Path(folder)
    if (folder / "observations.q11o").exists():
        s = old.stream(folder / "observations.q11o")
        return dict(**s, start=0, end=s["ticks"], oracle=True)
    p = folder / "observations.q12o"
    with p.open("rb") as f:
        b = f.read(80)
    require(b[:8] == b"QR12OBS1", "QR12 stream magic")
    version, count, n, dt, start, end, seed, geometry, scalar = struct.unpack_from("<3Qd5Q", b, 8)
    require(version == 1 and count in (1, 2, 4) and start <= end <= 2000, "QR12 stream dimensions")
    dtype = np.dtype([("tick", "<u8"), ("nodes", NODE, (count,)), ("checksum", "<u8")])
    require(
        p.stat().st_size == 80 + (end - start + 1) * dtype.itemsize, "QR12 stream exact coverage"
    )
    a = np.memmap(p, dtype=dtype, mode="r", offset=80, shape=(end - start + 1,))
    return dict(
        n=n,
        dt=dt,
        count=count,
        start=start,
        end=end,
        ticks=end - start,
        frames=a,
        seed=seed,
        geometry=geometry,
        scalar=scalar,
        oracle=False,
    )


def positions(geometry):
    a = np.array(((10.0, 10.0, 12.0), (14.0, 10.0, 12.0), (10.0, 14.0, 12.0), (14.0, 14.0, 12.0)))
    if geometry == 1:
        return np.array(
            ((9.0, 9.0, 12.0), (15.0, 9.0, 12.0), (9.0, 15.0, 12.0), (15.0, 15.0, 12.0))
        )
    if geometry == 2:
        return np.array(((10.5, 12.5, 12.5), (14.5, 12.5, 12.5)))
    if 10 <= geometry <= 13:
        return a[[geometry - 10]]
    if geometry in (20, 21):
        return a[[0, 1] if geometry == 20 else [2, 3]]
    return a
