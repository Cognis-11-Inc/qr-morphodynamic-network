//! Serial Experiment 0007 execution, with a frozen training/evaluation boundary.
use qr_neural_memory_system::{
    observation::checksum,
    operational_0007::{DIM, Decoder, OUTPUTS, Operator, Outcome, TIMES},
};
use std::{
    env,
    fs::{self, File},
    io::{self, BufWriter, Write},
    path::Path,
    time::Instant,
};
const TRAIN: [u64; 4] = [7, 19, 31, 43];
const HELD: [u64; 4] = [59, 71, 83, 97];
const CONTROLS: [&str; 8] = [
    "VIRGIN",
    "ALL",
    "WRITE_PORT_ONLY",
    "READ_PORT_ONLY",
    "REMOTE_ONLY",
    "SHUFFLED",
    "FROZEN",
    "NO_WRITE",
];
const PROBES: [usize; 6] = [0, 2182, 2183, 2184, 2186, 2191];
fn floats(path: &Path, x: &[f64]) -> io::Result<()> {
    let mut w = BufWriter::new(File::create(path)?);
    for v in x {
        w.write_all(&v.to_le_bytes())?;
    }
    w.flush()
}
fn load(path: &Path) -> io::Result<Vec<f64>> {
    let b = fs::read(path)?;
    if b.len() % 8 != 0 {
        return Err(io::Error::other("numeric file length"));
    }
    Ok(b.as_chunks::<8>()
        .0
        .iter()
        .map(|x| f64::from_le_bytes(*x))
        .collect())
}
fn vector(path: &Path) -> io::Result<[f64; DIM]> {
    load(path)?
        .try_into()
        .map_err(|_| io::Error::other("feature length"))
}
fn ident(seed: u64, rule: u8, symbol: usize, kind: &str) -> String {
    format!("s{seed}_r{rule}_w{symbol}_{kind}")
}
fn sample(op: &Operator) -> Vec<f64> {
    let b = op.body();
    OUTPUTS
        .iter()
        .flat_map(|&id| {
            [9, 27]
                .into_iter()
                .flat_map(move |m| [b.state.u[id * 64 + m], b.state.v[id * 64 + m]])
        })
        .collect()
}
fn reset_receipt(op: &mut Operator, path: &Path) -> io::Result<()> {
    let p = op.body().state.palette.concat();
    op.reset()?;
    if p != op.body().state.palette.concat() || !op.zero() {
        return Err(io::Error::other("reset failed"));
    }
    fs::write(
        path,
        format!(
            "zero=true\npalette_retained=true\npalette_fnv={}\n",
            checksum(&p)
        ),
    )
}
fn initial_fingerprint(op: &Operator) -> u64 {
    let b = op.body();
    let mut bytes = b.state.palette.concat();
    for x in b
        .state
        .u
        .iter()
        .chain(&b.state.v)
        .chain(b.history())
        .chain(b.shape_history())
    {
        bytes.extend_from_slice(&x.to_le_bytes());
    }
    for x in [b.state.dt, b.loss, b.boundary_loss, b.work, b.switch_work] {
        bytes.extend_from_slice(&x.to_le_bytes());
    }
    bytes.extend_from_slice(&b.state.tick.to_le_bytes());
    checksum(&bytes)
}
// Fixed operation recorder; all tick measurements precede advancement.
#[allow(clippy::too_many_lines)]
fn record(op: &mut Operator, folder: &Path, write: bool, amplitude: f64) -> io::Result<Vec<f64>> {
    fs::create_dir(folder)?;
    let b = op.body();
    let e0 = b.energy().total();
    let dt = b.state.dt;
    let cp = op.checkpoint()?;
    fs::write(
        folder.join("parameters.csv"),
        format!(
            "seed,rule,operation,port,module,dt,amplitude,initial_energy,initial_fingerprint\n{},{},{:?},{},{},{dt:.17e},{amplitude:.17e},{e0:.17e},{}\n",
            b.state.seed,
            cp.rule,
            cp.operation,
            cp.port,
            b.state.module,
            initial_fingerprint(op)
        ),
    )?;
    let mut global = BufWriter::new(File::create(folder.join("metrics.csv"))?);
    writeln!(
        global,
        "tick,time,kinetic,onsite,coupling,loss,boundary_loss,switch_work,drift,peak,velocity_peak"
    )?;
    let mut trace = BufWriter::new(File::create(folder.join("outputs.f64"))?);
    let mut probes = if write {
        let mut f = BufWriter::new(File::create(folder.join("early.q7p"))?);
        f.write_all(b"QR7PRB01")?;
        Some(f)
    } else {
        None
    };
    let end = if write { 8. } else { 32. };
    let mut features = Vec::new();
    loop {
        let b = op.body();
        let tick = b.state.tick;
        let t = f64::from(u32::try_from(tick).map_err(io::Error::other)?) * dt;
        let e = b.energy();
        let drift =
            (e.total() - e0 + b.loss + b.boundary_loss - b.switch_work).abs() / e0.max(1e-12);
        let peak = b.state.u.iter().fold(0_f64, |a, x| a.max(x.abs()));
        let vmax = b.state.v.iter().fold(0_f64, |a, x| a.max(x.abs()));
        writeln!(
            global,
            "{tick},{t:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{drift:.17e},{peak:.17e},{vmax:.17e}",
            e.kinetic, e.onsite, e.coupling, b.loss, b.boundary_loss, b.switch_work
        )?;
        let samples = sample(op);
        for v in &samples {
            trace.write_all(&v.to_le_bytes())?;
        }
        if let Some(p) = &mut probes {
            p.write_all(&tick.to_le_bytes())?;
            for id in PROBES {
                for m in 0..64 {
                    p.write_all(&b.state.u[id * 64 + m].to_le_bytes())?;
                    p.write_all(&b.state.v[id * 64 + m].to_le_bytes())?;
                }
            }
        }
        let checkpoint = if write {
            tick == 0 || (t - 8.).abs() < 1e-9
        } else {
            tick == 0 || TIMES.iter().any(|x| (t - x).abs() < 1e-9)
        };
        if checkpoint {
            fs::write(
                folder.join(format!("{tick:06}.q7f")),
                op.checkpoint()?.encode()?,
            )?;
        }
        if !write && TIMES.iter().any(|x| (t - x).abs() < 1e-9) {
            features.extend(samples);
        }
        if !drift.is_finite() || drift > 0.01 || peak > 100. || vmax > 100. {
            return Err(io::Error::other("QR7 numerical drift/field gate"));
        }
        if t >= end - 1e-9 {
            break;
        }
        op.advance()?;
    }
    global.flush()?;
    trace.flush()?;
    if let Some(mut p) = probes {
        p.flush()?;
    }
    if !write {
        floats(&folder.join("features.f64"), &features)?;
        fs::write(folder.join("COMPLETE"), b"frozen READ\n")?;
    }
    Ok(features)
}
fn exposure(
    root: &Path,
    op: &mut Operator,
    id: &str,
    symbol: usize,
    quiet: bool,
    frozen: bool,
) -> io::Result<Outcome> {
    op.restore()?;
    let amplitude = op.write(symbol, quiet)?;
    let folder = root.join(id);
    record(op, &folder, true, amplitude)?;
    let b = op.body();
    floats(&folder.join("velocity-history.f64"), b.history())?;
    floats(&folder.join("shape-history.f64"), b.shape_history())?;
    floats(&folder.join("scores.f64"), &b.scores())?;
    let pre = b.energy();
    let before = b.state.palette.clone();
    let outcome = op.commit(frozen)?;
    let b = op.body();
    let post = b.energy();
    fs::write(folder.join("post.q7f"), op.checkpoint()?.encode()?)?;
    let mut edits = BufWriter::new(File::create(folder.join("edits.csv"))?);
    writeln!(edits, "id,module,before,after")?;
    for (id, (a, p)) in before.iter().zip(&b.state.palette).enumerate() {
        for m in 0..64 {
            if a[m] != p[m] {
                writeln!(edits, "{id},{m},{},{}", a[m], p[m])?;
            }
        }
    }
    edits.flush()?;
    let mut work = BufWriter::new(File::create(folder.join("switch.csv"))?);
    writeln!(work, "id,pre,post,work")?;
    for id in 0..4096 {
        writeln!(
            work,
            "{id},{:.17e},{:.17e},{:.17e}",
            pre.local[id],
            post.local[id],
            post.local[id] - pre.local[id]
        )?;
    }
    work.flush()?;
    fs::write(
        folder.join("commit.csv"),
        format!(
            "frozen,quiet,pre,post,switch_work\n{frozen},{quiet},{:.17e},{:.17e},{:.17e}\n",
            pre.total(),
            post.total(),
            b.switch_work
        ),
    )?;
    reset_receipt(op, &folder.join("RESET"))?;
    fs::write(folder.join("COMPLETE"), b"WRITE committed/reset\n")?;
    Ok(outcome)
}
fn read_pair(root: &Path, op: &mut Operator, id: &str, calibrate: bool) -> io::Result<[f64; DIM]> {
    let mut features = Vec::new();
    for module in [9, 27] {
        op.reset()?;
        let amplitude = op.read(module, calibrate)?;
        let folder = root.join(format!("{id}_p{module}"));
        features.extend(record(op, &folder, false, amplitude)?);
        reset_receipt(op, &folder.join("RESET"))?;
    }
    let x: [f64; DIM] = features
        .try_into()
        .map_err(|_| io::Error::other("read feature count"))?;
    floats(&root.join(format!("{id}.f64")), &x)?;
    Ok(x)
}
fn reuse(root: &Path, op: &mut Operator, id: &str, cal: &str) -> io::Result<()> {
    for module in [9, 27] {
        op.reset()?;
        op.read(module, false)?;
        let fingerprint = initial_fingerprint(op);
        let source = format!("{cal}_p{module}");
        let parameters = fs::read_to_string(root.join(&source).join("parameters.csv"))?;
        let original = parameters
            .lines()
            .nth(1)
            .and_then(|s| s.split(',').next_back())
            .ok_or_else(|| io::Error::other("calibration fingerprint missing"))?
            .parse::<u64>()
            .map_err(io::Error::other)?;
        if fingerprint != original {
            return Err(io::Error::other("calibration reuse initial state differs"));
        }
        let folder = root.join(format!("{id}_p{module}"));
        fs::create_dir(&folder)?;
        fs::write(folder.join("REUSED"), source)?;
        fs::write(
            folder.join("EQUIVALENT"),
            format!("initial_fingerprint={fingerprint}\nfull_reset=true\n"),
        )?;
        op.reset()?;
    }
    fs::copy(
        root.join(format!("{cal}.f64")),
        root.join(format!("{id}.f64")),
    )?;
    Ok(())
}
fn collect(root: &Path, seeds: &[u64], fine: bool) -> io::Result<()> {
    let dt = if fine { 0.0125 } else { 0.025 };
    let mut ledger = BufWriter::new(File::create(root.join("ledger.csv"))?);
    writeln!(ledger, "id,seed,rule,symbol,kind,actual,source")?;
    for &seed in seeds {
        let cal = format!("s{seed}_CALIBRATE");
        let mut op = Operator::new(seed, dt, 2)?;
        read_pair(root, &mut op, &cal, true)?;
        writeln!(ledger, "{cal},{seed},0,-1,CALIBRATE,2,{cal}")?;
        ledger.flush()?;
        for rule in [2, 3] {
            let mut op = Operator::new(seed, dt, rule)?;
            let quiet = ident(seed, rule, 0, "ZERO_EXPOSURE");
            exposure(root, &mut op, &quiet, 0, true, false)?;
            writeln!(ledger, "{quiet},{seed},{rule},-1,ZERO_EXPOSURE,1,{quiet}")?;
            for symbol in 0..2 {
                let frozen = ident(seed, rule, symbol, "FROZEN_EXPOSURE");
                exposure(root, &mut op, &frozen, symbol, false, true)?;
                writeln!(
                    ledger,
                    "{frozen},{seed},{rule},{symbol},FROZEN_EXPOSURE,1,{frozen}"
                )?;
                let write = ident(seed, rule, symbol, "WRITE");
                let outcome = exposure(root, &mut op, &write, symbol, false, false)?;
                writeln!(ledger, "{write},{seed},{rule},{symbol},WRITE,1,{write}")?;
                for kind in CONTROLS {
                    if fine && kind != "REMOTE_ONLY" {
                        continue;
                    }
                    let id = ident(seed, rule, symbol, kind);
                    op.reset()?;
                    op.control(&outcome, kind)?;
                    let shared = ["VIRGIN", "FROZEN", "NO_WRITE"].contains(&kind);
                    if shared {
                        reuse(root, &mut op, &id, &cal)?;
                    } else {
                        read_pair(root, &mut op, &id, false)?;
                    }
                    writeln!(
                        ledger,
                        "{id},{seed},{rule},{symbol},{kind},{},{}",
                        if shared { 0 } else { 2 },
                        if shared { &cal } else { &id }
                    )?;
                    ledger.flush()?;
                }
                println!("seed={seed} rule={rule} symbol={symbol} dt={dt} complete");
            }
        }
    }
    ledger.flush()?;
    fs::write(root.join("COMPLETE"), b"registered collection complete\n")
}
fn model_path(root: &Path, rule: u8, calibrated: bool) -> std::path::PathBuf {
    root.join(format!(
        "template_r{rule}_{}.f64",
        if calibrated { "calibrated" } else { "raw" }
    ))
}
fn fit(root: &Path) -> io::Result<()> {
    for rule in [2, 3] {
        for calibrated in [true, false] {
            let mut means = [[0.; DIM]; 2];
            for seed in TRAIN {
                let baseline = vector(&root.join(format!("s{seed}_CALIBRATE.f64")))?;
                for (symbol, mean) in means.iter_mut().enumerate() {
                    let x = vector(
                        &root.join(format!("{}.f64", ident(seed, rule, symbol, "REMOTE_ONLY"))),
                    )?;
                    for j in 0..DIM {
                        mean[j] += x[j] - if calibrated { baseline[j] } else { 0. };
                    }
                }
            }
            for value in means.iter_mut().flatten() {
                *value /= 4.;
            }
            floats(&model_path(root, rule, calibrated), &means.concat())?;
        }
    }
    let mut receipt = vec![String::from(
        "QR7 templates: means of REMOTE_ONLY seeds 7,19,31,43; no evaluation data\n",
    )];
    for rule in [2, 3] {
        for calibrated in [true, false] {
            let p = model_path(root, rule, calibrated);
            receipt.push(format!(
                "{} {}\n",
                p.file_name().unwrap_or_default().to_string_lossy(),
                checksum(&fs::read(&p)?)
            ));
        }
    }
    fs::write(root.join("TRAINING_FROZEN"), receipt.concat())
}
fn predict(training: &Path, root: &Path, seeds: &[u64], fine: bool) -> io::Result<()> {
    let frozen = fs::read_to_string(training.join("TRAINING_FROZEN"))?;
    let mut out = BufWriter::new(File::create(root.join("predictions.csv"))?);
    writeln!(out, "id,rule,calibrated,expected,prediction,d0,d1")?;
    for rule in [2, 3] {
        for calibrated in [true, false] {
            let p = model_path(training, rule, calibrated);
            let values = load(&p)?;
            if !frozen.contains(&format!(
                "{} {}\n",
                p.file_name().unwrap_or_default().to_string_lossy(),
                checksum(&fs::read(&p)?)
            )) {
                return Err(io::Error::other("training template changed"));
            }
            if values.len() != 2 * DIM {
                return Err(io::Error::other("template length"));
            }
            let model = Decoder {
                means: [
                    values[..DIM]
                        .try_into()
                        .map_err(|_| io::Error::other("template"))?,
                    values[DIM..]
                        .try_into()
                        .map_err(|_| io::Error::other("template"))?,
                ],
            };
            for &seed in seeds {
                let baseline = vector(&root.join(format!("s{seed}_CALIBRATE.f64")))?;
                for symbol in 0..2 {
                    for kind in CONTROLS {
                        if fine && kind != "REMOTE_ONLY" {
                            continue;
                        }
                        let id = ident(seed, rule, symbol, kind);
                        let raw = vector(&root.join(format!("{id}.f64")))?;
                        let x = std::array::from_fn(|j| {
                            raw[j] - if calibrated { baseline[j] } else { 0. }
                        });
                        // Expected class is accessed only after pure numeric prediction.
                        let (prediction, d) = model.predict(&x)?;
                        writeln!(
                            out,
                            "{id},{rule},{calibrated},{symbol},{},{:.17e},{:.17e}",
                            prediction.map_or_else(|| "AMBIGUOUS".into(), |n| n.to_string()),
                            d[0],
                            d[1]
                        )?;
                    }
                }
            }
        }
    }
    out.flush()
}
fn main() -> io::Result<()> {
    let args: Vec<_> = env::args().collect();
    if args.len() != 3 {
        return Err(io::Error::other(
            "usage: experiment_0007 train|evaluate|refine|repeat ROOT",
        ));
    }
    let start = Instant::now();
    let root = Path::new(&args[2]);
    fs::create_dir_all(root)?;
    let stage = &args[1];
    let folder = root.join(stage);
    fs::create_dir(&folder)?;
    match stage.as_str() {
        "train" => {
            collect(&folder, &TRAIN, false)?;
            fit(&folder)?;
            predict(&folder, &folder, &TRAIN, false)?;
        }
        "evaluate" => {
            if !root.join("train/TRAINING_FROZEN").exists() {
                return Err(io::Error::other("freeze training before evaluation"));
            }
            collect(&folder, &HELD, false)?;
            predict(&root.join("train"), &folder, &HELD, false)?;
        }
        "refine" => {
            if !root.join("train/TRAINING_FROZEN").exists() {
                return Err(io::Error::other("freeze training before refinement"));
            }
            collect(&folder, &HELD, true)?;
            predict(&root.join("train"), &folder, &HELD, true)?;
        }
        "repeat" => {
            let mut op = Operator::new(31, 0.025, 2)?;
            let id = ident(31, 2, 0, "WRITE");
            let outcome = exposure(&folder, &mut op, &id, 0, false, false)?;
            op.control(&outcome, "REMOTE_ONLY")?;
            read_pair(&folder, &mut op, &ident(31, 2, 0, "REMOTE_ONLY"), false)?;
            fs::write(folder.join("COMPLETE"), b"repeat complete\n")?;
        }
        _ => return Err(io::Error::other("unknown QR7 stage")),
    }
    fs::write(
        folder.join("wall_seconds.txt"),
        format!("{:.3}\n", start.elapsed().as_secs_f64()),
    )?;
    Ok(())
}
