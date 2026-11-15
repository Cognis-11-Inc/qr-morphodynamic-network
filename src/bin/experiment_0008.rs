//! Registered serial QR8 physics and measured-output recorder.
use qr_neural_memory_system::communication_0008::{
    DISTANCES, Frozen, MODULES, REGION_VALUES, Signal, TIMES, probes, regions,
};
use std::{
    env,
    fs::{self, File},
    io::{self, BufWriter, Write},
    path::Path,
    time::Instant,
};
const TRAIN: [u64; 4] = [101, 103, 107, 109];
const HELD: [u64; 4] = [127, 131, 137, 139];
fn number(n: u64) -> io::Result<f64> {
    Ok(f64::from(u32::try_from(n).map_err(io::Error::other)?))
}
fn values(w: &mut BufWriter<File>, xs: &[f64]) -> io::Result<()> {
    for x in xs {
        w.write_all(&x.to_le_bytes())?;
    }
    Ok(())
}
#[allow(clippy::too_many_lines)] // Explicit physical observation order is kept in one loop.
fn run(root: &Path, seed: u64, dt: f64, signal: Signal) -> io::Result<()> {
    let id = format!("s{seed}_{}", signal.name());
    let folder = root.join(&id);
    fs::create_dir(&folder)?;
    let mut body = Frozen::new(seed, dt, signal)?;
    let initial = body.observer().total();
    let before = body.body().state.palette.clone();
    let amp = body.amplitudes();
    fs::write(
        folder.join("parameters.csv"),
        format!(
            "id,seed,dt,signal,module,port_a,port_b,amplitude_a,amplitude_b,unit_energy,initial_energy\n{id},{seed},{dt:.17e},{},{},2182,2186,{:.17e},{:.17e},{:.17e},{initial:.17e}\n",
            signal.name(),
            signal.module(),
            amp[0],
            amp[1],
            body.unit_energy()
        ),
    )?;
    let regions = regions();
    let probes = probes(&regions);
    let mut global = BufWriter::new(File::create(folder.join("metrics.csv"))?);
    writeln!(
        global,
        "tick,time,kinetic,onsite,coupling,loss,boundary_loss,forcing_work,switch_work,drift,peak,velocity_peak,participation,active_receivers,other_energy,other_motion,cross_energy,cross_motion"
    )?;
    let mut shell = BufWriter::new(File::create(folder.join("regions.q8r"))?);
    shell.write_all(b"QR8REG01")?;
    for n in [1, 10, REGION_VALUES as u64] {
        shell.write_all(&n.to_le_bytes())?;
    }
    let mut stream = BufWriter::new(File::create(folder.join("probes.q8p"))?);
    stream.write_all(b"QR8PRB01")?;
    for n in [1, probes.len() as u64, MODULES.len() as u64] {
        stream.write_all(&n.to_le_bytes())?;
    }
    for &id in &probes {
        stream.write_all(&(id as u64).to_le_bytes())?;
    }
    for m in MODULES {
        stream.write_all(&(m as u64).to_le_bytes())?;
    }
    loop {
        let medium = body.body();
        let observer = body.observer();
        let tick = medium.state.tick;
        let time = number(tick)? * dt;
        let loss = medium.loss + medium.boundary_loss;
        let drift = (observer.total() - initial + loss).abs() / initial.max(1e-12);
        let g = observer.global();
        let c = observer.components;
        writeln!(
            global,
            "{tick},{time:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{drift:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
            c[0],
            c[1],
            c[2],
            medium.loss,
            medium.boundary_loss,
            medium.work,
            medium.switch_work,
            observer.peaks[0],
            observer.peaks[1],
            g[0],
            g[1],
            g[2],
            g[3],
            g[4],
            g[5]
        )?;
        shell.write_all(&tick.to_le_bytes())?;
        for r in &regions {
            values(&mut shell, &observer.region(r))?;
        }
        stream.write_all(&tick.to_le_bytes())?;
        for &id in &probes {
            values(
                &mut stream,
                &[observer.neuron[id], observer.neuron_motion[id]],
            )?;
            for m in MODULES {
                values(
                    &mut stream,
                    &[medium.state.u[id * 64 + m], medium.state.v[id * 64 + m]],
                )?;
            }
        }
        if tick == 0 || TIMES.iter().any(|t| (time - t).abs() < 1e-9) {
            if medium.state.palette != before {
                return Err(io::Error::other("QR8 frozen palette changed"));
            }
            let reference = medium.energy();
            if (reference.total() - observer.total()).abs() > 1e-12
                || reference
                    .local
                    .iter()
                    .zip(&observer.neuron)
                    .any(|(a, b)| (a - b).abs() > 1e-12)
            {
                return Err(io::Error::other("QR8 passive partition mismatch"));
            }
            fs::write(
                folder.join(format!("{tick:06}.q8f")),
                body.record().encode()?,
            )?;
        }
        if !drift.is_finite()
            || drift > 0.01
            || observer.peaks.iter().any(|p| !p.is_finite() || *p > 100.)
            || medium.work != 0.
            || medium.switch_work != 0.
        {
            return Err(io::Error::other("QR8 numerical/drive gate"));
        }
        if signal == Signal::Zero
            && (observer.total() != 0. || observer.peaks.iter().any(|x| *x != 0.))
        {
            return Err(io::Error::other("QR8 exact zero gate"));
        }
        if time >= 32. - 1e-9 {
            break;
        }
        body.advance()?;
    }
    if body
        .body()
        .history()
        .iter()
        .chain(body.body().shape_history())
        .any(|x| *x != 0.)
    {
        return Err(io::Error::other("QR8 unexpected history"));
    }
    global.flush()?;
    shell.flush()?;
    stream.flush()?;
    fs::write(
        folder.join("COMPLETE"),
        b"frozen physics and observation complete\n",
    )?;
    println!("COMPLETE {id} dt={dt}");
    Ok(())
}
fn ledger(path: &Path, rows: &[(String, &str, String)]) -> io::Result<()> {
    let mut s = vec![String::from("id,status,reason\n")];
    for (id, status, reason) in rows {
        s.push(format!("{id},{status},{reason}\n"));
    }
    fs::write(path, s.concat())
}
fn main() -> io::Result<()> {
    let args: Vec<_> = env::args().collect();
    if args.len() != 3 {
        return Err(io::Error::other(
            "usage: experiment_0008 train|evaluate|refine|repeat ROOT",
        ));
    }
    let root = Path::new(&args[2]);
    fs::create_dir_all(root)?;
    let stage = &args[1];
    if !["train", "evaluate", "refine", "repeat"].contains(&stage.as_str()) {
        return Err(io::Error::other("unknown QR8 stage"));
    }
    if ["evaluate", "refine"].contains(&stage.as_str())
        && !fs::read_to_string(root.join("train/TRAINING_FROZEN"))?
            .starts_with("QR8_TRAINING_FROZEN_SCHEMA1\n")
    {
        return Err(io::Error::other(
            "freeze references before held-out execution",
        ));
    }
    let definitions = include_str!("../../docs/EXPERIMENT_0008_REGIONS.json");
    let region_file = root.join("regions.json");
    if region_file.exists() {
        if fs::read_to_string(&region_file)? != definitions {
            return Err(io::Error::other("QR8 region registration differs"));
        }
    } else {
        fs::write(region_file, definitions)?;
    }
    let folder = root.join(stage);
    fs::create_dir(&folder)?;
    let start = Instant::now();
    let seeds = if stage == "train" {
        &TRAIN[..]
    } else if stage == "repeat" {
        &[107][..]
    } else {
        &HELD[..]
    };
    let signals = if stage == "repeat" {
        &[Signal::ABm][..]
    } else {
        &Signal::ALL[..]
    };
    let dt = if stage == "refine" { 0.0125 } else { 0.025 };
    let mut rows: Vec<_> = seeds
        .iter()
        .flat_map(|&seed| {
            signals.iter().map(move |signal| {
                (
                    format!("s{seed}_{}", signal.name()),
                    "NOT_RUN",
                    String::from("awaiting serial execution"),
                )
            })
        })
        .collect();
    ledger(&folder.join("ledger.csv"), &rows)?;
    for (index, (&seed, &signal)) in seeds
        .iter()
        .flat_map(|seed| signals.iter().map(move |signal| (seed, signal)))
        .enumerate()
    {
        if let Err(error) = run(&folder, seed, dt, signal) {
            let message = error.to_string().replace([',', '\n'], " ");
            rows[index].1 = "FAILED";
            rows[index].2.clone_from(&message);
            let case = folder.join(&rows[index].0);
            if case.is_dir() {
                fs::write(case.join("FAILED"), message)?;
            }
            ledger(&folder.join("ledger.csv"), &rows)?;
            return Err(error);
        }
        rows[index].1 = "COMPLETE";
        rows[index].2 = String::from("actual trajectory no reuse");
        ledger(&folder.join("ledger.csv"), &rows)?;
    }
    fs::write(
        folder.join("wall_seconds.txt"),
        format!("{:.3}\n", start.elapsed().as_secs_f64()),
    )?;
    fs::write(
        folder.join("COMPLETE"),
        format!("{} trajectories; distances {:?}\n", rows.len(), DISTANCES),
    )
}
