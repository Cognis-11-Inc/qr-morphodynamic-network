"""QR11 bounded-state commitment, reset/probe plans and independent causal audits."""

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

from analysis import experiment_0009 as old
from analysis import io_0011 as io
from analysis.audit_0011 import audit_stage
from analysis.audit_coupling_0010 import neuron_energy
from analysis.experiment_0005 import require
from analysis.gates_0011 import compare
from analysis.plan_0011 import HELD, TRAIN, condition, write


def end_state(folder):
    return sorted(Path(folder).glob("*.n11"))[-1]


def operation(root, folder, name, source, enabled=True):
    source = Path(source)
    state = end_state(source)
    fluid = state.with_suffix(".q11")
    out = Path(folder) / name
    subprocess.run(
        [
            str(Path(root) / "registered-runner"),
            "commit",
            str(state),
            str(out),
            "1" if enabled else "0",
            str(fluid),
        ],
        check=True,
    )
    return dict(case=name, source=str(source), enabled=enabled, kind="COMMIT_OPERATION")


def verify_operation(folder, enabled):
    folder = Path(folder)
    a = io.neurons(folder / "before.n11")
    b = io.neurons(folder / "after.n11")
    require(a["tick"] == b["tick"] and a["dt"] == b["dt"], "QR11 commit clock")
    receipts = old.rows(folder / "commit.csv")
    chosen = old.rows(folder / "swaps.csv")
    gates = []
    edges = []
    for id, (before, after) in enumerate(zip(a["nodes"], b["nodes"], strict=True)):
        for key in ("u", "v", "packet", "previous", "age", "z", "loss"):
            require(np.array_equal(before[key], after[key]), "QR11 commit only morphology and flag")
        require(
            int(before["committed"]) == 0 and int(after["committed"]) == 1,
            "QR11 one commitment flag",
        )
        z = before["z"].reshape(3, 135)
        scores = z[2, 7:71] + 0.5 * abs(z[2, 71:135] - z[0, 71:135])
        maximum = float(scores.max())
        palette = before["palette"]
        candidate = []
        for m in range(64):
            for n in range(m + 1, 64):
                if abs(m // 8 - n // 8) + abs(m % 8 - n % 8) != 1:
                    continue
                eligible = bool(
                    palette[m] != palette[n]
                    and z[2, 7 + m] >= 0.01
                    and z[2, 7 + n] >= 0.01
                    and scores[m] >= 0.01
                    and scores[n] >= 0.01
                    and (scores[m] >= 0.05 * maximum or scores[n] >= 0.05 * maximum)
                )
                edges.append(
                    dict(
                        neuron=id,
                        a=m,
                        b=n,
                        eligible=eligible,
                        score_sum=float(scores[m] + scores[n]),
                    )
                )
                if eligible:
                    candidate.append((m, n))
        candidate.sort(key=lambda pair: (-float(scores[pair[0]] + scores[pair[1]]), *pair))
        used = set()
        accepted = []
        p = palette.copy()
        for m, n in candidate:
            if enabled and len(accepted) < 4 and m not in used and n not in used:
                accepted.append((m, n))
                used.update((m, n))
                p[m], p[n] = palette[n], palette[m]
        for edge in edges:
            if edge["neuron"] == id:
                pair = (edge["a"], edge["b"])
                edge["rank"] = candidate.index(pair) + 1 if pair in candidate else ""
                edge["accepted"] = pair in accepted
        actual = [(int(r["a"]), int(r["b"])) for r in chosen if int(r["neuron"]) == id]
        require(
            actual == accepted and np.array_equal(p, after["palette"]),
            "QR11 independently reconstructed exact swaps",
        )
        require(
            np.array_equal(np.bincount(p, minlength=5), np.bincount(palette, minlength=5))
            and np.count_nonzero(p != palette) <= 8,
            "QR11 structural constraints",
        )
        e0 = neuron_energy(palette, before["u"], before["v"])
        e1 = neuron_energy(p, after["u"], after["v"])
        work = float(receipts[id]["switch_work"])
        require(abs((e1 - e0) - work) <= 1e-12 * max(e0, e1, 1e-30), "QR11 actual switching work")
        gates.append(
            dict(
                neuron=id,
                edits=int(np.count_nonzero(p != palette)),
                switch_work=work,
                energy_before=e0,
                energy_after=e1,
            )
        )
    old.csv_write(folder / "eligibility-ledger.csv", edges)
    result = dict(valid=True, nodes=gates)
    (folder / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def pilot(root):
    root = Path(root)
    require(
        json.loads((root / "pilot/gates.json").read_text())["prerequisite_pass"],
        "QR11 lawful sensory/trace prerequisite",
    )
    dest = root / "morph_pilot"
    dest.mkdir()
    plan = []
    labels = ("S9", "S27", "ORDER", "NEG", "SINGLE", "QUIET", "OFF", "TRACE_OFF", "SCRAMBLED")
    for grid in ("P", "F"):
        for label in labels:
            plan.append(
                operation(root, dest, label + "_" + grid, root / "pilot" / (label + "_" + grid))
            )
        plan.append(operation(root, dest, "FROZEN_" + grid, root / "pilot" / ("S9_" + grid), False))
    plan.append(operation(root, dest, "REPEAT_P", root / "pilot/REPEAT_P"))
    old.csv_write(dest / "plan.csv", plan)
    results = {r["case"]: verify_operation(dest / r["case"], r["enabled"]) for r in plan}
    gate = []

    def g(name, value, limit=0):
        gate.append(
            dict(
                gate=name,
                value=float(value),
                limit=limit,
                verdict="PASS" if value <= limit else "FAIL",
            )
        )

    anyedit = any(
        results[label + "_P"]["nodes"][1]["edits"] > 0 for label in ("S9", "S27", "ORDER")
    )
    g("exposure_edits_exist", 0 if anyedit else 1)
    for label in ("QUIET", "OFF", "TRACE_OFF", "FROZEN"):
        for grid in ("P", "F"):
            g(label + "_receiver_edits_" + grid, results[label + "_" + grid]["nodes"][1]["edits"])
    numerical_morphology = []
    for label in ("S9", "S27", "ORDER"):
        a = io.neurons(dest / (label + "_P") / "after.n11")["nodes"]
        b = io.neurons(dest / (label + "_F") / "after.n11")["nodes"]
        av = io.neurons(dest / (label + "_P") / "before.n11")["nodes"]
        bv = io.neurons(dest / (label + "_F") / "before.n11")["nodes"]
        for id in (0, 1):
            ea = set(np.flatnonzero(a[id]["palette"] != av[id]["palette"]))
            eb = set(np.flatnonzero(b[id]["palette"] != bv[id]["palette"]))
            jaccard = len(ea & eb) / len(ea | eb) if ea | eb else 1.0
            numerical_morphology.append(
                dict(
                    condition=label,
                    neuron=id,
                    jaccard=jaccard,
                    palette_equal=bool(np.array_equal(a[id]["palette"], b[id]["palette"])),
                    primary_positions=sorted(int(x) for x in ea),
                    fine_positions=sorted(int(x) for x in eb),
                )
            )
            if id == 1:
                g(label + "_receiver_edit_disagreement", 1 - jaccard, 0.1)
    for file in ("after.n11", "scores.csv", "swaps.csv", "commit.csv"):
        require(
            (dest / "S9_P" / file).read_bytes() == (dest / "REPEAT_P" / file).read_bytes(),
            "QR11 actual commit repeat",
        )
    passed = all(r["verdict"] == "PASS" for r in gate)
    status = "PASS" if passed else "FAIL" if not anyedit else "INDETERMINATE"
    result = dict(
        schema=1,
        L4=status,
        prerequisite_pass=passed,
        operations=len(plan),
        gates=gate,
        all_nodes=results,
        numerical_morphology=numerical_morphology,
    )
    old.csv_write(dest / "gates.csv", gate)
    (dest / "gates.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


def probe_plan(root):
    root = Path(root)
    require(
        json.loads((root / "morph_pilot/gates.json").read_text())["prerequisite_pass"],
        "QR11 L4 prerequisite",
    )
    dest = root / "retention_pilot"
    plan = []
    labels = (
        "S9",
        "S27",
        "ORDER",
        "NEG",
        "SINGLE",
        "QUIET",
        "OFF",
        "TRACE_OFF",
        "SCRAMBLED",
        "FROZEN",
        "RESTORED_S9",
        "VIRGIN",
    )
    for grid in ("P", "F"):
        cal = "cal_" + grid
        plan.append(condition(cal, grid, seed=301, signal="PROBE", horizon=16, mode="SENSOR_OFF"))
        for label in labels:
            if label == "VIRGIN":
                state = virgin = ""
            else:
                origin = "S9" if label == "RESTORED_S9" else label
                state = str(root / "morph_pilot" / (origin + "_" + grid) / "after.n11")
                virgin = str(root / "pilot" / ("S9_" + grid) / "000000.n11")
                if label == "RESTORED_S9":
                    virgin = "restore:" + virgin
            plan.append(
                condition(
                    label + "_" + grid,
                    grid,
                    seed=301,
                    signal="PROBE",
                    horizon=16,
                    policy="same:" + str(dest / cal),
                    state=state,
                    virgin=virgin,
                )
            )
    assert len(plan) == 26
    return write(root, "retention_pilot", plan, root / "morph_pilot/gates.json")


def probe_vector(folder):
    s = io.stream(Path(folder) / "observations.q11o")
    a = s["frames"]["nodes"][:, 1]
    return np.stack((a["u"], a["v"]), axis=-1).ravel().copy()


def retention_pilot(root):
    root = Path(root)
    stage = root / "retention_pilot"
    receipt = audit_stage(stage)
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

    g("physical_validity", int(not receipt["valid"]))
    for label in ("S9", "S27"):
        for name, value in compare(stage / (label + "_P"), stage / (label + "_F")).items():
            g(label + "_" + name, value, 0.1)
        # P/F every-tick vectors need matched physical clocks, not flattened slicing.
        p = io.stream(stage / (label + "_P") / "observations.q11o")
        f = io.stream(stage / (label + "_F") / "observations.q11o")
        fp = f["frames"][::2]["nodes"][:, 1]
        vp = io.stream(stage / "VIRGIN_P/observations.q11o")["frames"]["nodes"][:, 1]
        vf = io.stream(stage / "VIRGIN_F/observations.q11o")["frames"][::2]["nodes"][:, 1]
        pa = p["frames"]["nodes"][:, 1]
        deltaP = np.stack((pa["u"] - vp["u"], pa["v"] - vp["v"]), axis=-1).ravel()
        deltaF = np.stack((fp["u"] - vf["u"], fp["v"] - vf["v"]), axis=-1).ravel()
        norm = float(np.linalg.norm(deltaF))
        error = float(np.linalg.norm(deltaP - deltaF))
        g(label + "_resolved_delta", 0 if norm > 1e-8 and norm >= 5 * error else 1)
        for grid in ("P", "F"):
            virgin = probe_vector(stage / ("VIRGIN_" + grid))
            adapted = probe_vector(stage / (label + "_" + grid))
            effect = old.relative(adapted, virgin)
            g(label + "_effect_" + grid, 0 if effect >= 0.01 else 1)
    for grid in ("P", "F"):
        virgin = probe_vector(stage / ("VIRGIN_" + grid))
        w0 = float(old.rows(stage / ("VIRGIN_" + grid) / "metrics.csv")[-1]["work"])
        for label in (
            "S9",
            "S27",
            "ORDER",
            "NEG",
            "SINGLE",
            "QUIET",
            "OFF",
            "TRACE_OFF",
            "SCRAMBLED",
            "FROZEN",
            "RESTORED_S9",
        ):
            w = float(old.rows(stage / (label + "_" + grid) / "metrics.csv")[-1]["work"])
            g(label + "_same_source_work_" + grid, abs(w - w0) / abs(w0), 0.01)
        for label in ("QUIET", "OFF", "TRACE_OFF", "FROZEN", "RESTORED_S9"):
            g(
                label + "_virgin_match_" + grid,
                old.relative(probe_vector(stage / (label + "_" + grid)), virgin),
                1e-12,
            )
    passed = all(r["verdict"] == "PASS" for r in gates)
    result = dict(
        schema=1,
        L5_causal="PASS" if passed else "INDETERMINATE",
        prerequisite_pass=passed,
        gates=gates,
    )
    old.csv_write(stage / "gates.csv", gates)
    (stage / "gates.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


def main_operations(root):
    root = Path(root)
    require(
        json.loads((root / "retention_pilot/gates.json").read_text())["prerequisite_pass"],
        "QR11 causal retention pilot prerequisite",
    )
    dest = root / "morph_main"
    dest.mkdir()
    plan = []
    for stage in ("train", "held", "controls"):
        for row in old.rows(root / stage / "plan.csv"):
            if row["case"].startswith("cal_"):
                continue
            name = (stage + "_" + row["case"]) if stage == "controls" else row["case"]
            plan.append(operation(root, dest, name, root / stage / row["case"]))
    require(len(plan) == 52, "QR11 all preregistered actual endpoints")
    old.csv_write(dest / "plan.csv", plan)
    values = {r["case"]: verify_operation(dest / r["case"], True) for r in plan}
    (dest / "verification.json").write_text(
        json.dumps(dict(valid=True, operations=52, results=values), indent=2) + "\n"
    )


def retention_plan(root, stage):
    root = Path(root)
    dest = root / stage
    plan = []
    require(
        (root / "morph_main/verification.json").exists(),
        "QR11 verified retained physical configurations",
    )
    if stage == "retention_train":
        seeds, grids = TRAIN, ("P",)
    else:
        require(
            (root / "retention_templates.json").exists(),
            "QR11 fixed retention templates before held probes",
        )
        seeds, grids = HELD, ("P", "F")
    for seed in seeds:
        for distance in (4, 6):
            for grid in grids:
                cal = f"cal_s{seed}_d{distance}_{grid}"
                plan.append(
                    condition(
                        cal,
                        grid,
                        seed=seed,
                        distance=distance,
                        signal="PROBE",
                        horizon=16,
                        mode="SENSOR_OFF",
                    )
                )
                for history_module in (9, 27):
                    for variant in ("ADAPTED", "VIRGIN"):
                        if variant == "ADAPTED":
                            name = f"s{seed}_d{distance}_m{history_module}_{grid}"
                            state = str(root / "morph_main" / name / "after.n11")
                            origin = "train" if stage == "retention_train" else "held"
                            virgin = str(root / origin / name / "000000.n11")
                        else:
                            state = virgin = ""
                        plan.append(
                            condition(
                                f"s{seed}_d{distance}_h{history_module}_{variant}_{grid}",
                                grid,
                                seed=seed,
                                distance=distance,
                                signal="PROBE",
                                horizon=16,
                                policy="same:" + str(dest / cal),
                                state=state,
                                virgin=virgin,
                            )
                        )
    require(
        len(plan) == (40 if stage == "retention_train" else 80), "QR11 complete retention matrix"
    )
    return write(root, stage, plan, root / "retention_pilot/gates.json")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "stage",
        choices=(
            "pilot",
            "probe-plan",
            "retention-pilot",
            "main",
            "retention-train",
            "retention-held",
        ),
    )
    p.add_argument("root", type=Path)
    a = p.parse_args()
    if a.stage in ("retention-train", "retention-held"):
        retention_plan(a.root, a.stage.replace("-", "_"))
    else:
        {
            "pilot": pilot,
            "probe-plan": probe_plan,
            "retention-pilot": retention_pilot,
            "main": main_operations,
        }[a.stage](a.root)


if __name__ == "__main__":
    main()
