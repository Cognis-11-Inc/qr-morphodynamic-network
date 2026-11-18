"""Versioned QR11 fields, owned states and every-tick observation streams."""

import math
import struct
from pathlib import Path

import numpy as np

from analysis.experiment_0005 import fnv, require

NODE = np.dtype(
    [
        ("palette", "u1", (64,)),
        ("u", "<f8", (64,)),
        ("v", "<f8", (64,)),
        ("packet", "<f8", (7,)),
        ("previous", "<f8"),
        ("age", "<u8"),
        ("z", "<f8", (405,)),
        ("loss", "<f8"),
        ("committed", "<u8"),
    ]
)
assert NODE.itemsize == 4416


def fluid(path):
    data = Path(path).read_bytes()
    require(len(data) >= 80 and data[:8] == b"QR11AC01", "QR11 fluid magic")
    version, n, tick, dt, kind, *m = struct.unpack_from("<3Qd4Q", data, 8)
    require(
        version == 1 and n in (48, 96) and dt in (0.05, 0.025) and kind == 2 and m == [0, 0, 0],
        "QR11 fluid metadata",
    )
    require(tick <= 1920 and len(data) == 80 + 32 * n**3, "QR11 full-field length/clock")
    require(
        fnv(data[:-8]) == struct.unpack_from("<Q", data, len(data) - 8)[0], "QR11 fluid checksum"
    )
    a = np.frombuffer(data, dtype="<f8", offset=72, count=4 * n**3).reshape(4, n, n, n)
    require(np.isfinite(a).all(), "QR11 finite full fields")
    return dict(n=n, tick=tick, dt=dt, fields=a)


def neurons(path):
    data = Path(path).read_bytes()
    require(len(data) >= 48 and data[:8] == b"QR11NEU1", "QR11 owned-state magic")
    version, count, tick, dt = struct.unpack_from("<3Qd", data, 8)
    require(version == 1 and count in (2, 3) and dt in (0.05, 0.025), "QR11 owned-state metadata")
    require(len(data) == 48 + count * 4416, "QR11 owned-state length")
    require(
        fnv(data[:-8]) == struct.unpack_from("<Q", data, len(data) - 8)[0],
        "QR11 owned-state checksum",
    )
    a = np.frombuffer(data, dtype=NODE, offset=40, count=count).copy()
    valid_nodes(a)
    return dict(tick=tick, dt=dt, nodes=a)


def valid_nodes(a):
    require((a["palette"] <= 4).all() and (a["committed"] <= 1).all(), "QR11 legal node values")
    require(
        all(np.isfinite(a[k]).all() for k in ("u", "v", "packet", "previous", "z", "loss")),
        "QR11 finite owned state",
    )
    require((np.abs(a["z"]) <= 1 + 1e-14).all(), "QR11 bounded trace")


def stream(path):
    with Path(path).open("rb") as f:
        header = f.read(48)
    require(len(header) == 48 and header[:8] == b"QR11OBS1", "QR11 observation magic")
    version, count, n, dt, ticks = struct.unpack_from("<3QdQ", header, 8)
    require(
        version == 1
        and count in (2, 3)
        and n in (48, 96)
        and dt in (0.05, 0.025)
        and ticks <= 1920,
        "QR11 observation metadata",
    )
    dtype = np.dtype([("tick", "<u8"), ("nodes", NODE, (count,)), ("checksum", "<u8")])
    require(
        Path(path).stat().st_size == 48 + (ticks + 1) * dtype.itemsize,
        "QR11 observation exact coverage",
    )
    frames = np.memmap(path, dtype=dtype, mode="r", offset=48, shape=(ticks + 1,))
    return dict(count=count, n=n, dt=dt, ticks=ticks, frames=frames)


def kernel(n, position):
    coords = (np.arange(n) + 0.5) * (24 / n)
    axes = []
    for x in position:
        w = np.maximum(0, 1 - abs(coords - x) / 1.5)
        ids = np.flatnonzero(w > 0)
        axes.append((ids, w[ids]))
    z, y, x = np.meshgrid(axes[2][0], axes[1][0], axes[0][0], indexing="ij")
    wz, wy, wx = np.meshgrid(axes[2][1], axes[1][1], axes[0][1], indexing="ij")
    ids = ((z * n + y) * n + x).ravel()
    weights = (wz * wy * wx).ravel()
    weights = weights / math.fsum(float(x) for x in weights)
    return ids, weights


def local(fields, position):
    n = fields.shape[1]
    ids, weights = kernel(n, position)
    a = fields.reshape(4, -1)
    sample = np.zeros(5)
    sample[0] = np.dot(weights, a[0, ids])
    density = 0.5 * a[0, ids] ** 2
    for axis in range(3):
        stride = n**axis
        valid = (ids // stride) % n > 0
        left = np.zeros(len(ids))
        left[valid] = a[axis + 1, ids[valid] - stride]
        right = a[axis + 1, ids]
        sample[axis + 1] = np.dot(weights, 0.5 * (left + right))
        density += 0.25 * right**2 + 0.25 * left**2
    sample[4] = np.dot(weights, density)
    return sample


def restrict(fields):
    n = fields.shape[1] // 2
    out = np.empty((4, n, n, n))
    out[0] = fields[0].reshape(n, 2, n, 2, n, 2).mean(axis=(1, 3, 5))
    for axis in range(3):
        normal = 2 - axis
        selected = np.take(fields[axis + 1], np.arange(1, 2 * n, 2), axis=normal)
        shape = []
        for a in range(3):
            shape.extend((n,) if a == normal else (n, 2))
        reshaped = selected.reshape(shape)
        means = []
        index = 0
        for a in range(3):
            if a != normal:
                means.append(index + 1)
                index += 2
            else:
                index += 1
        out[axis + 1] = reshaped.mean(axis=tuple(means))
    return out
