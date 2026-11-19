//! QR12 deterministic serial experiment plans, complete forks and raw observation.
use crate::{
    acoustic_0010::number,
    listening_0011::{Mode, World as Original},
    morphodynamic_0012::{Event, World},
};
use std::{
    f64::consts::PI,
    fs,
    io::{self, BufWriter, Write},
    path::Path,
    time::Instant,
};
fn parse<T: std::str::FromStr>(s: &str) -> io::Result<T> {
    s.parse().map_err(|_| io::Error::other("QR12 typed plan"))
}
fn force(kind: &str, time: f64) -> f64 {
    if kind == "QUIET" {
        0.
    } else if kind.starts_with("SUSTAINED") {
        (2. * PI * time / 8.).sin()
            * if time < 4. {
                (PI * time / 8.).sin().powi(2)
            } else {
                1.
            }
    } else if time <= 12. {
        (2. * PI * time / 8.).sin() * (PI * time / 12.).sin().powi(2)
    } else {
        0.
    }
}
fn file(dir: &Path, name: &str, header: &str) -> io::Result<BufWriter<fs::File>> {
    let mut f = BufWriter::new(fs::File::create(dir.join(name))?);
    writeln!(f, "{header}")?;
    Ok(f)
}
fn header(w: &World, start: usize, end: usize) -> Vec<u8> {
    let mut b = b"QR12OBS1".to_vec();
    for x in [
        1,
        w.neurons.len() as u64,
        w.fluid.n as u64,
        w.fluid.dt.to_bits(),
        start as u64,
        end as u64,
        w.seed,
        w.geometry as u64,
        u64::from(w.scalar),
    ] {
        b.extend(x.to_le_bytes());
    }
    b
}
fn event_log(
    dir: &Path,
    tick: usize,
    events: &[Event],
    out: &mut impl Write,
    scores: &mut impl Write,
) -> io::Result<()> {
    for e in events {
        let (a, b) = e.pair.map_or((-1_i32, -1_i32), |(a, b)| {
            (i32::try_from(a).unwrap(), i32::try_from(b).unwrap())
        });
        writeln!(
            out,
            "{tick},{},{a},{b},{},{},{},{:.17e},{}",
            e.id,
            u8::from(e.latch),
            u8::from(e.accepted),
            e.cause,
            e.work,
            e.before
                .iter()
                .zip(e.after)
                .filter(|(a, b)| **a != *b)
                .count()
        )?;
        for m in 0..64 {
            writeln!(
                scores,
                "{tick},{},{m},{},{},{:.17e},{:.17e}",
                e.id, e.before[m], e.after[m], e.h[m], e.score[m]
            )?;
        }
    }
    let _ = dir;
    Ok(())
}
#[allow(
    clippy::too_many_lines,
    clippy::float_cmp,
    clippy::many_single_char_names
)] // One append-only physical execution boundary.
fn run(root: &Path, row: &[&str]) -> io::Result<()> {
    if row.len() != 11 {
        return Err(io::Error::other("QR12 plan schema"));
    }
    let [
        name,
        seed,
        n,
        dt,
        geometry,
        policy,
        forcing,
        horizon,
        mask,
        scalar,
        checkpoint,
    ] = <&[&str; 11]>::try_from(row).unwrap();
    let dir = root.join(name);
    fs::create_dir(&dir)?;
    let wall = Instant::now();
    let seed = parse(seed)?;
    let n = parse(n)?;
    let dt = parse(dt)?;
    let geometry = parse(geometry)?;
    let scalar = *scalar == "1";
    let mask = parse(mask)?;
    let horizon: usize = parse(horizon)?;
    let mut w = if checkpoint.is_empty() {
        World::new(seed, n, dt, geometry, scalar, mask)?
    } else {
        World::load(Path::new(checkpoint))?
    };
    if w.fluid.n != n || w.fluid.dt != dt || w.seed != seed {
        return Err(io::Error::other("QR12 continuation configuration"));
    }
    let start = w.fluid.tick;
    let end = (0..=4000)
        .find(|&i| number(i) * dt == number(horizon))
        .ok_or_else(|| io::Error::other("QR12 clock"))?;
    fs::write(
        dir.join("metadata.csv"),
        format!(
            "case,seed,n,dt,geometry,policy,forcing,horizon,mask,scalar,checkpoint,start_tick\n{name},{seed},{n},{dt},{geometry},{policy},{forcing},{horizon},{mask},{},{checkpoint},{start}\n",
            u8::from(scalar)
        ),
    )?;
    let mut obs = BufWriter::new(fs::File::create(dir.join("observations.q12o"))?);
    obs.write_all(&header(&w, start, end))?;
    let mut metrics = file(
        &dir,
        "metrics.csv",
        "tick,time,fluid,neural,loss,force_work,switch_work,positive,negative,port_net,cancellation,e0,e1,e2,e3",
    )?;
    let mut kicks = file(
        &dir,
        "kicks.csv",
        "tick,half,neuron,module,before,after,impulse",
    )?;
    let mut ports = file(
        &dir,
        "exchange.csv",
        "tick,half,neuron,module,x_before,x_after,v_before,v_after,fluid_delta,neural_delta",
    )?;
    let mut events = file(
        &dir,
        "events.csv",
        "tick,neuron,a,b,latch,accepted,cause,work,positions",
    )?;
    let mut scores = file(
        &dir,
        "scores.csv",
        "tick,neuron,module,before,after,H8,score",
    )?;
    let initial = w.totals();
    let initial_energy = initial[0] + initial[1];
    if start > 0 {
        fs::copy(checkpoint, dir.join("branch-before.q12"))?;
        if policy.starts_with("ISOLATED") {
            w.mask = 1;
        }
        let intervention = match *policy {
            "PERMIT" | "ISOLATED_PERMIT" => "PERMIT",
            "EXTERNAL" => "EXTERNAL_TARGET",
            _ => "FIXED",
        };
        if *policy == "SHAM" {
            let mut permitted = w.clone();
            let e = permitted.events("PERMIT")?;
            let dw = e[0].work;
            let veto = w.events("FIXED")?;
            event_log(&dir, start, &veto, &mut events, &mut scores)?;
            w.sham(dw)?;
            fs::write(dir.join("sham.csv"), format!("target_work\n{dw:.17e}\n"))?;
        } else {
            let e = w.events(intervention)?;
            event_log(&dir, start, &e, &mut events, &mut scores)?;
        }
        fs::write(dir.join("branch-after.q12"), w.snapshot())?;
    }
    let mut oracle = if *policy == "ORACLE" {
        Some(Original::new(seed, n, dt, 4, false, true)?)
    } else {
        None
    };
    if let Some(o) = &oracle {
        obs = BufWriter::new(fs::File::create(dir.join("observations.q11o"))?);
        obs.write_all(&o.stream_header(end))?;
        fs::remove_file(dir.join("observations.q12o"))?;
    }
    for tick in start..=end {
        if tick > start {
            let time = (number(tick) - 0.5) * dt;
            let value = force(forcing, time);
            let mut applied = Vec::new();
            if *forcing == "COMMON" {
                for id in 0..w.neurons.len() {
                    applied.push((id, 9, 0.5 * value));
                }
            } else {
                applied.push((
                    0,
                    9,
                    if forcing.starts_with("IND") {
                        0.5 * value
                    } else {
                        value
                    },
                ));
            }
            let mode = if *policy == "SENSOR_OFF" {
                Mode::SensorOff
            } else if *policy == "TRACE_OFF" {
                Mode::Off
            } else {
                Mode::On
            };
            if let Some(o) = &mut oracle {
                o.advance(&applied, mode)?;
            } else {
                w.advance(&applied, mode)?;
            }
            if oracle.is_none() {
                let t = number(tick) * dt;
                if start == 0 && [16., 24., 32.].contains(&t) {
                    fs::write(dir.join(format!("pre-{tick:06}.q12")), w.snapshot())?;
                }
                {
                    let p = if start == 0
                        && (*policy == "ADAPTIVE"
                            || *policy == "NONADAPTIVE"
                            || *policy == "TRACE_OFF")
                    {
                        if *policy == "TRACE_OFF" {
                            "ADAPTIVE"
                        } else {
                            *policy
                        }
                    } else {
                        "FIXED"
                    };
                    let e = w.events(p)?;
                    event_log(&dir, tick, &e, &mut events, &mut scores)?;
                }
                if forcing.starts_with("PERTURB") && t == 24. {
                    w.kick(2, 1, 9, 0.01);
                }
                for &(half, id, m, b, a, i) in &w.kicks {
                    writeln!(kicks, "{tick},{half},{id},{m},{b:.17e},{a:.17e},{i:.17e}")?;
                }
                for &(half, id, m, r) in &w.exchanges {
                    writeln!(
                        ports,
                        "{tick},{half},{id},{m},{}",
                        r.map(|x| format!("{x:.17e}")).join(",")
                    )?;
                }
            } else if let Some(o) = &oracle {
                for &(half, id, b, a, i) in &o.kicks {
                    writeln!(kicks, "{tick},{half},{id},9,{b:.17e},{a:.17e},{i:.17e}")?;
                }
                for &(half, id, m, r) in &o.exchanges {
                    writeln!(
                        ports,
                        "{tick},{half},{id},{m},{}",
                        r.map(|x| format!("{x:.17e}")).join(",")
                    )?;
                }
            }
        }
        if let Some(o) = &oracle {
            obs.write_all(&o.frame())?;
            let a = o.totals();
            let e = [a[0], a[1], a[3], a[4], 0., a[5], a[6], a[7], a[10]];
            let energies = [o.neurons[0].energy(), o.neurons[1].energy(), 0., 0.];
            writeln!(
                metrics,
                "{tick},{:.17e},{},{}",
                number(tick) * dt,
                e.map(|x| format!("{x:.17e}")).join(","),
                energies.map(|x| format!("{x:.17e}")).join(",")
            )?;
            if tick == 0 || tick == end / 2 || tick == end {
                fs::write(dir.join(format!("{tick:06}.q11")), o.fluid_bytes()?)?;
                fs::write(dir.join(format!("{tick:06}.n11")), o.snapshot())?;
            }
        } else {
            obs.write_all(&w.frame())?;
            let e = w.totals();
            let energies = std::array::from_fn::<_, 4, _>(|i| {
                if i < w.neurons.len() {
                    w.node_energy(i)
                } else {
                    0.
                }
            });
            writeln!(
                metrics,
                "{tick},{:.17e},{},{}",
                number(tick) * dt,
                e.map(|x| format!("{x:.17e}")).join(","),
                energies.map(|x| format!("{x:.17e}")).join(",")
            )?;
            if tick == start
                || tick == end
                || number(tick) * dt == (number(start) + number(end)) * dt / 2.
                || [16., 24., 32.].contains(&(number(tick) * dt))
            {
                fs::write(dir.join(format!("{tick:06}.q12")), w.snapshot())?;
            }
            if e[0] + e[1] > 100. * (initial_energy + e[5]).max(1e-20) {
                return Err(io::Error::other("QR12 energy ceiling"));
            }
        }
        if wall.elapsed().as_secs_f64() > 300. {
            return Err(io::Error::other("QR12 case runtime ceiling"));
        }
    }
    obs.flush()?;
    metrics.flush()?;
    kicks.flush()?;
    ports.flush()?;
    events.flush()?;
    scores.flush()?;
    fs::write(
        dir.join("COMPLETE"),
        b"Actual trajectory complete; independent audit pending.\n",
    )?;
    let mut ledger = fs::OpenOptions::new()
        .append(true)
        .open(root.join("ledger.csv"))?;
    writeln!(
        ledger,
        "{name},{:.6},COMPLETE",
        wall.elapsed().as_secs_f64()
    )?;
    println!("{name} {:.3}s", wall.elapsed().as_secs_f64());
    Ok(())
}
/// Execute one previously frozen stage serially, preserving failed/partial cases.
/// # Errors
/// Rejects invalid prerequisites, existing outputs and malformed physical states.
pub fn matrix(root: &Path) -> io::Result<()> {
    let gate = fs::read_to_string(root.join("PREREQUISITE"))?;
    if gate.trim() != "A"
        && !fs::read_to_string(gate.trim())?.contains("\"prerequisite_pass\": true")
    {
        return Err(io::Error::other("QR12 independent prerequisite"));
    }
    let rows = fs::read_to_string(root.join("plan.csv"))?;
    fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(root.join("ledger.csv"))?
        .write_all(b"case,elapsed_seconds,status\n")?;
    let mut log = file(root, "execution-events.csv", "case,status")?;
    for row in rows.lines().skip(1) {
        let fields = row.split(',').collect::<Vec<_>>();
        writeln!(log, "{},STARTED", fields[0])?;
        log.flush()?;
        if let Err(e) = run(root, &fields) {
            writeln!(log, "{},FAILED", fields[0])?;
            log.flush()?;
            fs::write(root.join("FAILED"), e.to_string())?;
            return Err(e);
        }
        writeln!(log, "{},COMPLETE", fields[0])?;
        log.flush()?;
    }
    fs::write(
        root.join("COMPLETE"),
        b"Stage physical trajectories complete.\n",
    )
}
