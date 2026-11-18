"""Preregistered QR11 stage dependencies and component-specific scientific decisions."""

import argparse
import json
from pathlib import Path

import numpy as np

from analysis import experiment_0009 as old
from analysis import experiment_0010 as qr10
from analysis import io_0011 as io
from analysis.audit_0011 import audit_stage, signature
from analysis.experiment_0005 import require


def compare(folder_a, folder_b):
    a = io.stream(Path(folder_a) / "observations.q11o")
    b = io.stream(Path(folder_b) / "observations.q11o")
    stride = round(a["dt"] / b["dt"])
    require(stride >= 1, "QR11 comparison time direction")
    av, bv = a["frames"]["nodes"], b["frames"][::stride]["nodes"]
    require(len(av) == len(bv), "QR11 aligned physical samples")
    values = {}
    for id in range(a["count"]):
        for key in ("packet", "z"):
            values[f"node{id}_{key}"] = old.relative(av[:, id][key], bv[:, id][key])
        values[f"node{id}_uv"] = old.relative(
            np.stack((av[:, id]["u"], av[:, id]["v"])), np.stack((bv[:, id]["u"], bv[:, id]["v"]))
        )
    for path in sorted(Path(folder_a).glob("*.q11")):
        f = io.fluid(path)
        target = Path(folder_b) / f"{round(f['tick'] * f['dt'] / b['dt']):06}.q11"
        g = io.fluid(target)
        truth = io.restrict(g["fields"]) if g["n"] == 2 * f["n"] else g["fields"]
        values[f"fluid_t{f['tick'] * f['dt']}"] = old.relative(f["fields"], truth)
    return values


def l1(root):
    root = Path(root)
    stage = root / "l1"
    receipt = audit_stage(stage)
    gates = []

    def gate(category, name, value, limit=0):
        gates.append(
            dict(
                category=category,
                gate=name,
                value=float(value),
                limit=limit,
                verdict="PASS" if value <= limit else "FAIL",
            )
        )

    gate("reliability", "independent_all_cases", int(not receipt["valid"]))
    for name in ("REF_P", "REF_T", "REF_F", "ABPLUS_P", "ABMINUS_P"):
        folder = stage / name
        reference = root / "references" / name
        s = io.stream(folder / "observations.q11o")
        responses = []
        for id in range(s["count"]):
            response = float(np.linalg.norm(s["frames"]["nodes"][:, id]["packet"]))
            responses.append(dict(case=name, neuron=id, packet_norm=response))
            gate("causality", f"{name}_node{id}", 0 if response > 1e-8 else 1)
        for path in folder.glob("*.q11"):
            f = io.fluid(path)
            g = qr10.decode(reference / (path.stem + ".q10"))
            gate(
                "reference",
                str(path.relative_to(stage)),
                old.relative(f["fields"], g["fields"]),
                1e-12,
            )
            node = s["frames"][f["tick"]]["nodes"]
            rows = old.rows(reference / (path.stem + ".neuron.csv"))
            for id in range(s["count"]):
                original = rows[id * 64 : (id + 1) * 64]
                for field in ("u", "v"):
                    gate(
                        "reference",
                        f"{name}_{path.stem}_{id}_{field}",
                        old.relative(
                            node[id][field], np.array([float(r[field]) for r in original])
                        ),
                        1e-12,
                    )
    for name in ("QUIET_P", "QUIET_F", "OFF_P", "OFF_F"):
        a = io.stream(stage / name / "observations.q11o")["frames"]["nodes"]
        gate("silence", name, float(np.max(abs(a["packet"]))))
    original = stage / "REF_P"
    repeat = stage / "REPEAT_P"

    def raw(folder):
        return {
            p.name: p.read_bytes()
            for p in folder.iterdir()
            if p.is_file() and p.name not in ("audit.json", "audit-gates.csv")
        }

    gate("determinism", "same_case_raw_bytes", int(raw(original) != raw(repeat)))
    for path in original.glob("*.q11"):
        gate(
            "reference",
            "passive_sensor_" + path.stem,
            int(path.read_bytes() != (stage / "SENSOR_OFF_P" / path.name).read_bytes()),
        )
    for grid in ("T", "F"):
        for name, value in compare(stage / "REF_P", stage / ("REF_" + grid)).items():
            gate("refinement", grid + "_" + name, value, 0.1)
    for grid in ("P", "F"):
        pos = io.stream(stage / ("REF_" + grid) / "observations.q11o")["frames"]["nodes"]
        neg = io.stream(stage / ("NEG_" + grid) / "observations.q11o")["frames"]["nodes"]
        odd = [0, 1, 2, 3, 6]
        even = [4, 5]
        gate(
            "polarity",
            grid + "_signed_packets",
            float(np.max(abs(pos["packet"][:, :, odd] + neg["packet"][:, :, odd]))),
            1e-12,
        )
        gate(
            "polarity",
            grid + "_even_packets",
            float(np.max(abs(pos["packet"][:, :, even] - neg["packet"][:, :, even]))),
            1e-12,
        )
        a, b = pos["z"].reshape(len(pos), 2, 3, 135), neg["z"].reshape(len(neg), 2, 3, 135)
        gate(
            "polarity",
            grid + "_signed_traces",
            float(np.max(abs(a[:, :, :, odd] + b[:, :, :, odd]))),
            1e-12,
        )
        gate(
            "polarity",
            grid + "_energy_traces",
            float(np.max(abs(a[:, :, :, 4] - b[:, :, :, 4]))),
            1e-12,
        )
        gate(
            "polarity",
            grid + "_resolved_signed_signal",
            0 if np.linalg.norm(a[:, :, :, odd]) > 1e-8 else 1,
        )
    verdicts = {
        c: "PASS" if all(g["verdict"] == "PASS" for g in gates if g["category"] == c) else "FAIL"
        for c in (
            "causality",
            "silence",
            "determinism",
            "refinement",
            "polarity",
            "reference",
            "reliability",
        )
    }
    result = dict(
        schema=1,
        L1=verdicts,
        prerequisite_pass=all(v == "PASS" for v in verdicts.values()),
        failures=[g for g in gates if g["verdict"] == "FAIL"],
    )
    old.csv_write(stage / "scientific-gates.csv", gates)
    (stage / "gates.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


def pilot(root):
    root = Path(root)
    stage = root / "pilot"
    receipt = audit_stage(stage)
    gates = []
    for signal in ("S9", "S27", "ORDER"):
        for grid in ("T", "F"):
            for name, value in compare(
                stage / (signal + "_P"), stage / (signal + "_" + grid)
            ).items():
                gates.append(
                    dict(
                        question="validity",
                        case=signal,
                        gate=grid + "_" + name,
                        value=value,
                        limit=0.1,
                        verdict="PASS" if value <= 0.1 else "FAIL",
                    )
                )
    a, b = signature(stage / "S9_P", "SIGNED"), signature(stage / "ORDER_P", "SIGNED")
    af, bf = signature(stage / "S9_F", "SIGNED"), signature(stage / "ORDER_F", "SIGNED")
    separation = float(np.linalg.norm(af - bf))
    uncertainty = max(float(np.linalg.norm(a - af)), float(np.linalg.norm(b - bf)))
    structure = separation > 1e-8 and separation >= 5 * uncertainty
    gate = dict(
        question="structure",
        case="S9_ORDER",
        gate="equal_work_temporal_signature",
        value=separation,
        uncertainty=uncertainty,
        limit=5 * uncertainty,
        verdict="PASS" if structure else "INDETERMINATE",
    )
    gates.append(gate)
    validity = receipt["valid"] and all(
        g["verdict"] == "PASS" for g in gates if g["question"] == "validity"
    )
    # Repeat reuses only an amplitude, never a physical trajectory.
    original = stage / "S9_P"
    repeat = stage / "REPEAT_P"
    for suffix in ("observations.q11o", "metrics.csv", "kicks.csv", "exchange.csv"):
        require(
            (original / suffix).read_bytes() == (repeat / suffix).read_bytes(),
            "QR11 pilot actual repeat " + suffix,
        )
    result = dict(
        schema=1,
        L2_mechanistic="PASS" if validity else "FAIL",
        L2_structure="PASS" if structure else "INDETERMINATE",
        L3_equal_work="PASS" if receipt["valid"] else "FAIL",
        prerequisite_pass=bool(validity and structure),
        gates=gates,
    )
    old.csv_write(
        stage / "scientific-gates.csv",
        [
            {
                k: r.get(k, "")
                for k in ("question", "case", "gate", "value", "uncertainty", "limit", "verdict")
            }
            for r in gates
        ],
    )
    (stage / "gates.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=("l1", "pilot"))
    p.add_argument("root", type=Path)
    a = p.parse_args()
    {"l1": l1, "pilot": pilot}[a.stage](a.root)


if __name__ == "__main__":
    main()
