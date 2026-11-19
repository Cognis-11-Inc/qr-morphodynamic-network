"""Frozen QR12 collective observables, fixed controls and numerical comparisons."""

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from analysis import io_0012 as io
from analysis.causal_0012 import relative_delta
from analysis.experiment_0009 import csv_write, relative, rows
from analysis.gates_0012 import compare


def features(folder):
    s = io.stream(folder)
    stride = round(0.05 / s["dt"])
    nodes = s["frames"][::stride]["nodes"]
    time = np.arange(len(nodes)) * 0.05
    window = (time >= 16) & (time <= 40)
    metrics = rows(Path(folder) / "metrics.csv")[::stride]
    e = np.array([[float(r["e" + str(i)]) for i in range(s["count"])] for r in metrics])
    states = np.stack((nodes["u"], nodes["v"]), axis=-1)
    result = measure(states[window], e[window], nodes["v"][window, :, 9])
    final = metrics[-1]
    result.update(
        force_work=float(final["force_work"]),
        switch_work=float(final["switch_work"]),
        positive_work=float(final["positive"]),
        negative_work=float(final["negative"]),
        peak_node_energy=e.max(axis=0).tolist(),
        decay_ratio=float(e[-1].sum() / max(e[round(12 / 0.05)].sum(), 1e-30)),
        n=s["n"],
        dt=s["dt"],
    )
    arrival = []
    for i in range(s["count"]):
        a = np.flatnonzero(e[:, i] >= 1e-10 * max(float(final["positive"]), 1e-30))
        arrival.append(float(time[a[0]]) if len(a) else None)
    result["arrival"] = arrival
    return result, states, e, nodes["v"][:, :, 9]


def measure(states, energies, velocity):
    total = energies.sum(axis=1)
    participation = np.divide(
        total**2,
        (energies**2).sum(axis=1),
        out=np.zeros_like(total),
        where=(energies**2).sum(axis=1) > 0,
    )
    vectors = states.transpose(1, 0, 2, 3).reshape(states.shape[1], -1)
    norms = np.linalg.norm(vectors, axis=1)
    cos = []
    locks = []
    count = len(velocity)
    fft = np.fft.fft(velocity, axis=0)
    h = np.zeros(count)
    h[0] = 1
    if count % 2 == 0:
        h[count // 2] = 1
        h[1 : count // 2] = 2
    else:
        h[1 : (count + 1) // 2] = 2
    phase = np.angle(np.fft.ifft(fft * h[:, None], axis=0))
    rms = np.sqrt(np.mean(velocity**2, axis=0))
    freq = np.fft.rfftfreq(count, 0.05)
    power = abs(np.fft.rfft(velocity, axis=0)) ** 2
    dominant = freq[np.argmax(power, axis=0)]
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            if min(norms[i], norms[j]) >= 1e-8:
                cos.append(abs(float(np.dot(vectors[i], vectors[j]) / (norms[i] * norms[j]))))
            if min(rms[i], rms[j]) >= 1e-8:
                locks.append(float(abs(np.mean(np.exp(1j * (phase[:, i] - phase[:, j]))))))
    carrier = np.exp(-2j * np.pi * np.arange(count) * 0.05 / 8) @ velocity / count
    return dict(
        participation=float(participation.mean()),
        diversity=1 - float(np.mean(cos)) if cos else None,
        diversity_pairs=len(cos),
        PLV=float(np.mean(locks)) if locks else None,
        phase_pairs=len(locks),
        dominant_frequency=dominant.tolist(),
        carrier_real=carrier.real.tolist(),
        carrier_imag=carrier.imag.tolist(),
    )


def comparison(pair):
    primary, fine = pair
    values = compare(primary, fine)

    def pattern(folder, dt):
        return [
            (round(int(e["tick"]) * dt / 0.05), e["neuron"], e["a"], e["b"])
            for e in rows(folder / "events.csv")
            if e["accepted"] == "1"
        ]

    values["event_pattern_disagree"] = int(pattern(primary, 0.05) != pattern(fine, 0.025))
    return dict(case=primary.name, **values)


def review(root):
    root = Path(root)
    d = root / "d"
    allrows = {}
    values = {}
    numerical = []
    for r in rows(d / "ledger.csv"):
        x, states, e, velocity = features(d / r["case"])
        allrows[r["case"]] = x
        values[r["case"]] = (states, e, velocity)
    pairs = [(d / name, d / (name[:-1] + "F")) for name in sorted(allrows) if name.endswith("_P")]
    # Independent saved-case analysis only, never parallel physical updates.
    with ProcessPoolExecutor(max_workers=4) as pool:
        numerical = list(pool.map(comparison, pairs))
    csv_write(root / "collective-numerical.csv", numerical)
    pair_valid = {
        row["case"][:-2]: all(
            v <= 0.1
            for k, v in row.items()
            if k not in ("case", "palette_positions_disagree", "event_pattern_disagree")
        )
        and row["palette_positions_disagree"] == 0
        and row["event_pattern_disagree"] == 0
        for row in numerical
    }
    valid = all(pair_valid.values())
    summaries = []
    for seed in (409, 419):
        standard_valid = pair_valid[f"s{seed}_FIXED"] and pair_valid[f"s{seed}_ADAPTIVE"]
        changes = []
        for grid in "PF":
            a = allrows[f"s{seed}_ADAPTIVE_{grid}"]
            b = allrows[f"s{seed}_FIXED_{grid}"]
            delta = {
                k: (a[k] - b[k]) if a[k] is not None and b[k] is not None else None
                for k in ("participation", "diversity", "PLV", "decay_ratio")
            }
            delta["dose_relative_difference"] = abs(a["positive_work"] - b["positive_work"]) / max(
                b["positive_work"], 1e-30
            )
            changes.append(delta)
        resolved = {
            k: changes[0][k] is not None
            and changes[1][k] is not None
            and min(abs(changes[0][k]), abs(changes[1][k])) > 0.05
            and min(abs(changes[0][k]), abs(changes[1][k]))
            >= 5 * abs(changes[0][k] - changes[1][k])
            for k in ("participation", "diversity", "PLV", "decay_ratio")
        }
        diversity = (
            "INDETERMINATE"
            if not standard_valid or max(c["dose_relative_difference"] for c in changes) > 0.01
            else "PASS"
            if resolved["diversity"] and min(c["diversity"] for c in changes) >= 0.05
            else "FAIL"
        )
        summaries.append(
            dict(
                seed=seed,
                morphological_modulation="PASS"
                if standard_valid and any(resolved.values())
                else "INDETERMINATE"
                if not standard_valid
                else "FAIL",
                increased_diversity=diversity,
                changes=changes,
                resolved_observables=resolved,
            )
        )
    controls = []
    for grid in "PF":
        shared = values[f"s409_FIXED_{grid}"][0]
        solo = values[f"s409_SOLO0_{grid}"][0]
        independent = np.zeros_like(shared)
        independent[:, 0] = solo[:, 0]
        common = values[f"s409_COMMON_{grid}"][0]
        private = np.concatenate([values[f"s409_IND{i}_{grid}"][0] for i in range(4)], axis=1)
        time = np.arange(len(common)) * 0.05
        late = time >= 16
        energies = np.concatenate([values[f"s409_IND{i}_{grid}"][1] for i in range(4)], axis=1)
        vel = np.concatenate([values[f"s409_IND{i}_{grid}"][2] for i in range(4)], axis=1)
        private_features = measure(private[late], energies[late], vel[late])
        controls.append(
            dict(
                grid=grid,
                shared_vs_independent_single_relative=relative(shared, independent),
                shared_remote_norm=float(np.linalg.norm(shared[:, 1:])),
                common_vs_independent_common_relative=relative(common, private),
                private_common_observables=private_features,
                shared_common_observables=allrows[f"s409_COMMON_{grid}"],
            )
        )
    fixedP = values["s409_FIXED_P"][0][:, 1:]
    fixedF = values["s409_FIXED_F"][0][:, 1:]
    unc = float(np.linalg.norm(fixedP - fixedF))
    norm = float(np.linalg.norm(fixedF))
    detected = min(
        sum(
            x > 1e-10 * allrows[f"s409_FIXED_{g}"]["positive_work"]
            for x in allrows[f"s409_FIXED_{g}"]["peak_node_energy"][1:]
        )
        for g in "PF"
    )
    coupling_valid = all(pair_valid["s409_" + label] for label in ("FIXED", "SOLO0", "OFF"))
    reciprocal = (
        coupling_valid
        and detected >= 2
        and norm > 1e-8
        and norm >= 5 * unc
        and all(c["shared_vs_independent_single_relative"] > 0.001 for c in controls)
    )
    regimes = []
    for kind, left, right in (
        ("sustained", "SUSTAINED_FIXED", "FIXED"),
        ("geometry", "ALT_FIXED", "FIXED"),
        ("perturb_fixed", "PERTURB_FIXED", "FIXED"),
        ("perturb_adaptive", "PERTURB_ADAPTIVE", "ADAPTIVE"),
    ):
        p = values[f"s409_{left}_P"][0] - values[f"s409_{right}_P"][0]
        f = values[f"s409_{left}_F"][0] - values[f"s409_{right}_F"][0]
        dn = float(np.linalg.norm(f))
        err = float(np.linalg.norm(p - f))
        rel = relative_delta(f, values[f"s409_{right}_F"][0])
        regime_valid = pair_valid[f"s409_{left}"] and pair_valid[f"s409_{right}"]
        regimes.append(
            dict(
                comparison=kind,
                norm=dn,
                grid_error=err,
                relative_effect=rel,
                verdict="PASS"
                if regime_valid
                and dn > 1e-8
                and dn >= 5 * err
                and (rel > 0.1 or kind.startswith("perturb"))
                else "INDETERMINATE"
                if not regime_valid or dn < 5 * err
                else "FAIL",
            )
        )
    r = dict(
        M3_reciprocal_collective="PASS"
        if reciprocal
        else "INDETERMINATE"
        if not coupling_valid
        else "FAIL",
        M3_morphological_modulation="PASS"
        if all(s["morphological_modulation"] == "PASS" for s in summaries)
        else "INDETERMINATE"
        if any(s["morphological_modulation"] == "INDETERMINATE" for s in summaries)
        else "FAIL",
        M3_increased_diversity="PASS"
        if all(s["increased_diversity"] == "PASS" for s in summaries)
        else "INDETERMINATE"
        if any(s["increased_diversity"] == "INDETERMINATE" for s in summaries)
        else "FAIL",
        numerically_valid=valid,
        standard_seeds=summaries,
        controls=controls,
        regimes=regimes,
        observables=allrows,
        scope=(
            "Finite driven four-neuron cases; activity/diversity/coordination "
            "are not intelligence or an automatic improvement."
        ),
    )
    (root / "collective-verification.json").write_text(json.dumps(r, indent=2) + "\n")
    csv_write(root / "regime-comparisons.csv", regimes)
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    a = p.parse_args()
    print(json.dumps(review(a.root), indent=2))


if __name__ == "__main__":
    main()
