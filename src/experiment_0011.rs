//! QR11 serial physical-case execution and bounded morphology operations.
use crate::{
    acoustic_0010::{Fluid, number},
    listening_0011::{Mode, World, load_neurons, write_nodes},
    observation::checksum,
};
use std::{
    f64::consts::PI,
    fs,
    io::{self, BufWriter, Write},
    path::Path,
    time::Instant,
};
fn parse<T: std::str::FromStr>(s: &str) -> io::Result<T> {
    s.parse()
        .map_err(|_| io::Error::other("QR11 typed plan field"))
}
fn csv(path: &Path) -> io::Result<Vec<Vec<String>>> {
    Ok(fs::read_to_string(path)?
        .lines()
        .skip(1)
        .filter(|s| !s.is_empty())
        .map(|s| s.split(',').map(str::to_owned).collect())
        .collect())
}
fn last_work(path: &Path) -> io::Result<f64> {
    let rows = csv(&path.join("metrics.csv"))?;
    parse(
        &rows
            .last()
            .ok_or_else(|| io::Error::other("empty calibration"))?[6],
    )
}
fn amplitude(policy: &str) -> io::Result<f64> {
    if let Some(value) = policy.strip_prefix("fixed:") {
        return parse(value);
    }
    let path = policy
        .strip_prefix("work1:")
        .or_else(|| policy.strip_prefix("same:"))
        .ok_or_else(|| io::Error::other("QR11 amplitude policy"))?;
    let work = last_work(Path::new(path))?;
    if !work.is_finite() || work <= 0. {
        return Err(io::Error::other("QR11 calibration net work"));
    }
    Ok(work.sqrt().recip())
}
fn force(signal: &str, time: f64) -> f64 {
    if signal == "ZERO" {
        return 0.;
    }
    if signal == "REF" || signal == "REFNEG" || signal == "AB+" || signal == "AB-" {
        return if time <= 12. {
            (2. * PI / 12. * time).sin()
                * (PI * time / 12.).sin().powi(2)
                * if signal == "REFNEG" { -1. } else { 1. }
        } else {
            0.
        };
    }
    if signal == "PROBE" {
        return if time <= 8. {
            (2. * PI / 8. * time).sin() * (PI * time / 8.).sin().powi(2)
        } else {
            0.
        };
    }
    let signs = match signal {
        "STD" => [1., 1., -1.],
        "ORDER" => [-1., 1., 1.],
        "NEG" => [-1., -1., 1.],
        "SINGLE" => [0., 0., -1.],
        _ => [0.; 3],
    };
    for (k, start) in [0., 16., 32.].into_iter().enumerate() {
        let t = time - start;
        if (0. ..=12.).contains(&t) {
            return signs[k] * (2. * PI / 8. * t).sin() * (PI * t / 12.).sin().powi(2);
        }
    }
    0.
}
fn load_fluid(path: &Path) -> io::Result<Fluid> {
    let b = fs::read(path)?;
    if b.len() < 80
        || &b[..8] != b"QR11AC01"
        || checksum(&b[..b.len() - 8]) != u64::from_le_bytes(b[b.len() - 8..].try_into().unwrap())
    {
        return Err(io::Error::other("QR11 fluid checkpoint"));
    }
    let word = |offset| u64::from_le_bytes(b[offset..offset + 8].try_into().unwrap());
    let n = usize::try_from(word(16)).map_err(io::Error::other)?;
    if b.len() != 80 + 32 * n.pow(3) {
        return Err(io::Error::other("QR11 fluid length"));
    }
    let mut f = Fluid::new(n, f64::from_bits(word(32)))?;
    f.tick = usize::try_from(word(24)).map_err(io::Error::other)?;
    for (i, x) in f.q.iter_mut().chain(f.w.iter_mut().flatten()).enumerate() {
        *x = f64::from_bits(word(72 + 8 * i));
    }
    Ok(f)
}
#[allow(clippy::too_many_lines)] // Append-only complete physical execution and observer records.
fn case(root: &Path, row: &[String]) -> io::Result<()> {
    if row.len() != 14 {
        return Err(io::Error::other("QR11 plan schema"));
    }
    let [
        name,
        seed,
        n,
        dt,
        distance,
        module,
        signal,
        horizon,
        policy,
        mode,
        three,
        coupled,
        state,
        virgin,
    ] = <&[String; 14]>::try_from(row).unwrap();
    let dir = root.join(name);
    fs::create_dir(&dir)?;
    let start = Instant::now();
    let mut events = fs::OpenOptions::new()
        .append(true)
        .open(root.join("events.csv"))?;
    writeln!(events, "{name},STARTED")?;
    let n: usize = parse(n)?;
    let dt: f64 = parse(dt)?;
    let horizon: usize = parse(horizon)?;
    let seed: u64 = parse(seed)?;
    let distance: usize = parse(distance)?;
    let module: usize = parse(module)?;
    let mode = Mode::parse(mode)?;
    let amplitude = amplitude(policy)?;
    let mut world = World::new(seed, n, dt, distance, three == "1", coupled == "1")?;
    if !state.is_empty() {
        let (tick, old_dt, nodes) = load_neurons(Path::new(state))?;
        if old_dt.to_bits() != dt.to_bits() {
            return Err(io::Error::other("QR11 state grid mismatch"));
        }
        world.neurons = nodes;
        let fluid_path = Path::new(state)
            .parent()
            .unwrap()
            .join("fluid_reference.txt");
        world.fluid = load_fluid(Path::new(fs::read_to_string(fluid_path)?.trim()))?;
        if world.fluid.tick != tick {
            return Err(io::Error::other("QR11 continuation clock"));
        }
        let removed = world.reset()?;
        let (_, _, original) =
            load_neurons(Path::new(virgin.strip_prefix("restore:").unwrap_or(virgin)))?;
        world.neurons[0].install(original[0].palette)?;
        if virgin.starts_with("restore:") {
            world.neurons[1].install(original[1].palette)?;
        }
        fs::write(
            dir.join("reset.csv"),
            format!("removed_energy,source_restore_work\n{removed:.17e},0\n"),
        )?;
    }
    fs::write(
        dir.join("metadata.csv"),
        format!(
            "schema,seed,n,dt,distance,module,signal,horizon,amplitude,mode,three,coupled,state_ref,virgin_ref,amplitude_policy\n1,{seed},{n},{dt},{distance},{module},{signal},{horizon},{amplitude:.17e},{mode:?},{three},{coupled},{state},{virgin},{policy}\n"
        ),
    )?;
    let ticks = (0..=4000)
        .find(|&i| (number(i) * dt).to_bits() == number(horizon).to_bits())
        .ok_or_else(|| io::Error::other("QR11 clock"))?;
    let mut obs = BufWriter::new(fs::File::create(dir.join("observations.q11o"))?);
    obs.write_all(&world.stream_header(ticks))?;
    let mut metrics = BufWriter::new(fs::File::create(dir.join("metrics.csv"))?);
    writeln!(
        metrics,
        "tick,time,fluid_energy,neural_energy,receiver_energy,loss,work,positive_work,negative_work,source_net,source_positive,source_backflow,exchange_cancellation"
    )?;
    let mut kicks = BufWriter::new(fs::File::create(dir.join("kicks.csv"))?);
    writeln!(kicks, "tick,half,neuron,module,before,after,impulse")?;
    let mut exchanges = BufWriter::new(fs::File::create(dir.join("exchange.csv"))?);
    writeln!(
        exchanges,
        "tick,half,neuron,module,x_before,x_after,v_before,v_after,fluid_delta,neural_delta"
    )?;
    let cal = mode == Mode::SensorOff
        && policy == "fixed:1"
        && signal != "REF"
        && signal != "AB+"
        && signal != "AB-";
    for tick in 0..=ticks {
        if tick > 0 {
            let value = amplitude * force(signal, (number(tick) - 0.5) * dt);
            let mut forces = vec![(0, module, value)];
            if three == "1" {
                forces.push((2, module, if signal == "AB-" { -value } else { value }));
            }
            world.advance(&forces, mode)?;
            for &(half, id, before, after, impulse) in &world.kicks {
                writeln!(
                    kicks,
                    "{tick},{half},{id},{module},{before:.17e},{after:.17e},{impulse:.17e}"
                )?;
            }
            for &(half, id, m, r) in &world.exchanges {
                writeln!(
                    exchanges,
                    "{tick},{half},{id},{m},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
                    r[0], r[1], r[2], r[3], r[4], r[5]
                )?;
            }
        }
        obs.write_all(&world.frame())?;
        let e = world.totals();
        writeln!(
            metrics,
            "{tick},{:.17e},{}",
            number(tick) * dt,
            e.map(|x| format!("{x:.17e}")).join(",")
        )?;
        let checkpoints = if horizon == 48 {
            vec![0, ticks / 3, 2 * ticks / 3, ticks]
        } else {
            vec![0, ticks / 2, ticks]
        };
        if checkpoints.contains(&tick) && (!cal || tick == 0 || tick == ticks) {
            fs::write(dir.join(format!("{tick:06}.q11")), world.fluid_bytes()?)?;
            fs::write(dir.join(format!("{tick:06}.n11")), world.snapshot())?;
        }
    }
    obs.flush()?;
    metrics.flush()?;
    kicks.flush()?;
    exchanges.flush()?;
    fs::write(
        dir.join("COMPLETE"),
        b"Physical trajectory complete; independent scientific audit pending.\n",
    )?;
    let mut ledger = fs::OpenOptions::new()
        .append(true)
        .open(root.join("ledger.csv"))?;
    writeln!(
        ledger,
        "{name},{:.6},COMPLETE",
        start.elapsed().as_secs_f64()
    )?;
    writeln!(events, "{name},COMPLETE")?;
    println!("{name} {:.3}s", start.elapsed().as_secs_f64());
    Ok(())
}
/// Run every frozen planned physical case serially, refusing existing case folders.
/// # Errors
/// Rejects invalid prerequisites, plans, existing outputs or failed physical execution.
pub fn matrix(root: &Path) -> io::Result<()> {
    let prerequisite = fs::read_to_string(root.join("PREREQUISITE"))?;
    if prerequisite.trim() != "L1"
        && !fs::read_to_string(prerequisite.trim())?.contains("\"prerequisite_pass\": true")
    {
        return Err(io::Error::other("QR11 independent prerequisite gate"));
    }
    let plan = csv(&root.join("plan.csv"))?;
    fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(root.join("ledger.csv"))?
        .write_all(b"case,elapsed_seconds,status\n")?;
    fs::write(root.join("events.csv"), "case,status\n")?;
    for row in plan {
        if let Err(error) = case(root, &row) {
            let mut f = fs::OpenOptions::new()
                .append(true)
                .open(root.join("events.csv"))?;
            writeln!(f, "{},FAILED", row[0])?;
            fs::write(root.join("FAILED"), error.to_string())?;
            return Err(error);
        }
    }
    fs::write(
        root.join("COMPLETE"),
        b"All planned trajectories complete, independent gates pending.\n",
    )
}
/// Apply one owned-state morphology operation; no new PDE trajectory is implied.
/// # Errors
/// Rejects malformed input, illegal commit state, existing outputs or IO errors.
pub fn commit(input: &Path, output: &Path, enabled: bool, fluid_ref: &Path) -> io::Result<()> {
    fs::create_dir(output)?;
    let (tick, dt, mut nodes) = load_neurons(input)?;
    fs::copy(input, output.join("before.n11"))?;
    let mut receipts = BufWriter::new(fs::File::create(output.join("commit.csv"))?);
    writeln!(
        receipts,
        "neuron,before_energy,after_energy,switch_work,positions"
    )?;
    let mut scores = BufWriter::new(fs::File::create(output.join("scores.csv"))?);
    writeln!(scores, "neuron,module,before,after,H8,C8,Cfast,score")?;
    let mut edges = BufWriter::new(fs::File::create(output.join("swaps.csv"))?);
    writeln!(edges, "neuron,a,b")?;
    for (id, node) in nodes.iter_mut().enumerate() {
        let before = node.energy();
        let old = node.palette;
        let s = node.scores();
        let (work, swaps) = node.commit(enabled, dt)?;
        writeln!(
            receipts,
            "{id},{before:.17e},{:.17e},{work:.17e},{}",
            node.energy(),
            2 * swaps.len()
        )?;
        for (m, score) in s.iter().enumerate() {
            writeln!(
                scores,
                "{id},{m},{},{},{:.17e},{:.17e},{:.17e},{score:.17e}",
                old[m],
                node.palette[m],
                node.memory.z[270 + 7 + m],
                node.memory.z[270 + 71 + m],
                node.memory.z[71 + m]
            )?;
        }
        for (a, b) in swaps {
            writeln!(edges, "{id},{a},{b}")?;
        }
    }
    scores.flush()?;
    edges.flush()?;
    receipts.flush()?;
    write_nodes(&output.join("after.n11"), tick, dt, &nodes)?;
    fs::write(
        output.join("fluid_reference.txt"),
        format!("{}\n", fluid_ref.display()),
    )?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn physical_calibration_reads_source_work_not_receiver_or_loss() {
        let folder = std::env::temp_dir().join(format!("qr11-cal-{}", std::process::id()));
        fs::create_dir(&folder).unwrap();
        fs::write(
            folder.join("metrics.csv"),
            "tick,time,fluid_energy,neural_energy,receiver_energy,loss,work\n0,0,1,2,3,0.25,4\n",
        )
        .unwrap();
        assert_eq!(last_work(&folder).unwrap(), 4.);
        assert_eq!(
            amplitude(&format!("work1:{}", folder.display())).unwrap(),
            0.5
        );
        fs::remove_dir_all(folder).unwrap();
    }
}
