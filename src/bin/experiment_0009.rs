//! Registered QR9 standalone acoustic prerequisite runner.
use qr_neural_memory_system::acoustic_0009::{Fixture, Fluid, number, reference};
use std::{
    fs,
    io::{self, BufWriter, Write},
    path::Path,
    time::Instant,
};

fn case(root: &Path, fixture: Fixture, n: usize, dt: f64, suffix: &str) -> io::Result<()> {
    let label = format!("{}_n{n}_dt{dt}{suffix}", fixture.name());
    let dir = root.join(&label);
    fs::create_dir(&dir)?;
    let start = Instant::now();
    let mut fluid = Fluid::new(n, dt)?;
    fluid.initialize(fixture);
    let mut events = fs::OpenOptions::new()
        .append(true)
        .open(root.join("events.csv"))?;
    writeln!(events, "{label},STARTED")?;
    let basis = if let Fixture::Mode(mode) = fixture {
        Some(
            (0..fluid.q.len())
                .map(|i| fluid.mode(mode, i))
                .collect::<Vec<_>>(),
        )
    } else {
        None
    };
    let basis_norm = basis
        .as_ref()
        .map_or(1., |b| b.iter().map(|x| x.0 * x.0).sum::<f64>());
    let mut metrics = BufWriter::new(fs::File::create(dir.join("metrics.csv"))?);
    writeln!(
        metrics,
        "tick,time,energy,max_pressure,max_velocity,pressure_projection,velocity_projection"
    )?;
    let mut probes = BufWriter::new(fs::File::create(dir.join("probes.csv"))?);
    writeln!(probes, "tick,axis,offset,q,wx,wy,wz,energy_density")?;
    let ticks = if dt.to_bits() == 0.05_f64.to_bits() {
        480
    } else {
        960
    };
    for tick in 0..=ticks {
        if tick > 0 {
            fluid.advance()?;
        }
        let time = number(tick) * dt;
        let pressure_peak = fluid.q.iter().map(|x| x.abs()).fold(0_f64, f64::max);
        let velocity_peak = fluid
            .w
            .iter()
            .flatten()
            .map(|x| x.abs())
            .fold(0_f64, f64::max);
        let (projection_p, projection_w) = basis.as_ref().map_or((0., 0.), |b| {
            let p = b
                .iter()
                .enumerate()
                .map(|(i, x)| fluid.q[i] * x.0)
                .sum::<f64>()
                / basis_norm;
            let w = b
                .iter()
                .enumerate()
                .map(|(i, x)| (0..3).map(|a| fluid.w[a][i] * x.1[a]).sum::<f64>())
                .sum::<f64>()
                / basis_norm;
            (p, w)
        });
        writeln!(
            metrics,
            "{tick},{time:.17e},{:.17e},{pressure_peak:.17e},{velocity_peak:.17e},{projection_p:.17e},{projection_w:.17e}",
            fluid.energy()
        )?;
        for axis in 0..3 {
            for offset in [-6., -4., -2., 0., 2., 4., 6.] {
                let mut point = [12.; 3];
                point[axis] += offset;
                let x = fluid.sample(point);
                writeln!(
                    probes,
                    "{tick},{axis},{offset},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
                    x[0], x[1], x[2], x[3], x[4]
                )?;
            }
        }
        if [0., 6., 12., 24.].contains(&time) {
            fs::write(dir.join(format!("{tick:06}.q9a")), fluid.encode(fixture)?)?;
        }
    }
    metrics.flush()?;
    probes.flush()?;
    fs::write(
        dir.join("COMPLETE"),
        b"Recorded full registered horizon; not a scientific verdict.\n",
    )?;
    let mut ledger = fs::OpenOptions::new()
        .append(true)
        .open(root.join("ledger.csv"))?;
    writeln!(
        ledger,
        "{label},{n},{dt},{},{:.6},COMPLETE",
        ticks + 1,
        start.elapsed().as_secs_f64()
    )?;
    writeln!(events, "{label},COMPLETE")?;
    println!("{label} complete {:.3}s", start.elapsed().as_secs_f64());
    Ok(())
}
fn main() -> io::Result<()> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 3 || args[1] != "standalone" {
        return Err(io::Error::other(
            "usage: experiment_0009 standalone NEW_ROOT",
        ));
    }
    let root = Path::new(&args[2]);
    fs::create_dir(root)?;
    fs::write(
        root.join("ledger.csv"),
        "case,n,dt,tick_rows,elapsed_seconds,status\n",
    )?;
    fs::write(root.join("events.csv"), "case,status\n")?;
    let mut plan = String::from("case,n,dt,initial_status\n");
    for f in [
        Fixture::Mode([4, 0, 0]),
        Fixture::Mode([6, 0, 0]),
        Fixture::Mode([8, 0, 0]),
        Fixture::Mode([4, 4, 4]),
        Fixture::Gaussian,
    ] {
        for (n, dt) in [(48, 0.05), (48, 0.025), (96, 0.025)] {
            use std::fmt::Write as _;
            writeln!(plan, "{}_n{n}_dt{dt},{n},{dt},NOT_RUN", f.name()).expect("string write");
        }
    }
    plan.push_str("zero_n48_dt0.05,48,0.05,NOT_RUN\nmode8-0-0_n48_dt0.05_repeat,48,0.05,NOT_RUN\n");
    fs::write(root.join("plan.csv"), plan)?;
    let p = reference();
    fs::write(
        root.join("reference.csv"),
        format!(
            "density,sound_speed,bulk_modulus,dynamic_viscosity\n{:.17e},{:.17e},{:.17e},{:.17e}\n",
            p[0], p[1], p[2], p[3]
        ),
    )?;
    for f in [
        Fixture::Mode([4, 0, 0]),
        Fixture::Mode([6, 0, 0]),
        Fixture::Mode([8, 0, 0]),
        Fixture::Mode([4, 4, 4]),
        Fixture::Gaussian,
    ] {
        for (n, dt) in [(48, 0.05), (48, 0.025), (96, 0.025)] {
            if let Err(e) = case(root, f, n, dt, "") {
                fs::write(root.join("FAILED"), format!("{f:?}: {e}"))?;
                return Err(e);
            }
        }
    }
    case(root, Fixture::Zero, 48, 0.05, "")?;
    case(root, Fixture::Mode([8, 0, 0]), 48, 0.05, "_repeat")?;
    fs::write(
        root.join("COMPLETE"),
        b"17 raw executions; independent validation pending.\n",
    )
}
