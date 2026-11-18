//! Stationary actual 64-module QR-neuron adapter with reciprocal fluid transducers.
use crate::{
    acoustic_0010::{Fixture, Fluid, accurate_sum, number},
    lattice::{Case, Configuration, Drive, Lattice},
};
use std::{
    f64::consts::PI,
    fs,
    io::{self, BufWriter, Write},
    path::Path,
    time::Instant,
};

#[derive(Clone)]
struct Neuron {
    palette: [u8; 64],
    u: [f64; 64],
    v: [f64; 64],
    omega: [f64; 64],
    gamma: [f64; 64],
    edges: Vec<(usize, usize, f64)>,
    loss: f64,
}
fn links(m: usize) -> Vec<usize> {
    (0..64)
        .filter(|&j| (m / 8).abs_diff(j / 8) + (m % 8).abs_diff(j % 8) == 1)
        .collect()
}
impl Neuron {
    fn new(palette: [u8; 64]) -> Self {
        let omega = std::array::from_fn(|m| {
            let occupied = links(m).iter().filter(|&&j| palette[j] != 0).count();
            (0.8 + 0.08 * f64::from(palette[m])
                + 0.04 * number(occupied)
                + if palette[m] == 1 { 0.12 } else { 0. })
            .powi(2)
        });
        let gamma = std::array::from_fn(|m| {
            0.08 + 0.01 * number(links(m).iter().filter(|&&j| palette[j] == 0).count())
                + if palette[m] == 1 { 0. } else { 0.02 }
        });
        let g = palette.map(|p| match p {
            0 => 0.5,
            1 => 1.,
            _ => 0.75,
        });
        let mut edges = Vec::new();
        for m in 0..64 {
            for j in links(m) {
                if m < j {
                    edges.push((m, j, 0.15 * g[m] * g[j]));
                }
            }
        }
        Self {
            palette,
            u: [0.; 64],
            v: [0.; 64],
            omega,
            gamma,
            edges,
            loss: 0.,
        }
    }
    fn acceleration(&self) -> [f64; 64] {
        let mut a = std::array::from_fn(|i| -self.omega[i] * self.u[i]);
        for &(i, j, k) in &self.edges {
            let f = k * (self.u[j] - self.u[i]);
            a[i] += f;
            a[j] -= f;
        }
        a
    }
    fn damp(&mut self, dt: f64) {
        for i in 0..64 {
            let before = self.v[i];
            self.v[i] *= (-self.gamma[i] * dt * 0.5).exp();
            self.loss += 0.5 * (before * before - self.v[i] * self.v[i]);
        }
    }
    fn step(&mut self, dt: f64) {
        self.damp(dt);
        let a = self.acceleration();
        for (v, f) in self.v.iter_mut().zip(a) {
            *v += 0.5 * dt * f;
        }
        for (u, v) in self.u.iter_mut().zip(self.v) {
            *u += dt * v;
        }
        let a = self.acceleration();
        for (v, f) in self.v.iter_mut().zip(a) {
            *v += 0.5 * dt * f;
        }
        self.damp(dt);
    }
    fn energy(&self) -> f64 {
        accurate_sum(
            (0..64).map(|i| {
                f64::midpoint(self.v[i] * self.v[i], self.omega[i] * self.u[i] * self.u[i])
            }),
        ) + accurate_sum(
            self.edges
                .iter()
                .map(|&(i, j, k)| 0.5 * k * (self.u[i] - self.u[j]).powi(2)),
        )
    }
    fn kick(&mut self, module: usize, impulse: f64) -> f64 {
        let old = self.v[module];
        self.v[module] += impulse;
        0.5 * (self.v[module] * self.v[module] - old * old)
    }
}
struct Port {
    neuron: usize,
    module: usize,
    weights: Vec<(usize, f64)>,
    norm: f64,
    net: f64,
    positive: f64,
    negative: f64,
    neural: f64,
    cancellation: f64,
}
impl Port {
    fn new(fluid: &Fluid, neuron: usize, module: usize, position: [f64; 3]) -> Self {
        let mut weights = Vec::new();
        for i in 0..fluid.q.len() {
            let x = fluid.position(i);
            let w = (0..3)
                .map(|a| (1. - (x[a] - position[a]).abs() / 1.5).max(0.))
                .product::<f64>();
            if w > 0. {
                weights.push((i, w));
            }
        }
        let sum = accurate_sum(weights.iter().map(|x| x.1));
        for x in &mut weights {
            x.1 /= sum;
        }
        let norm = accurate_sum(weights.iter().map(|x| x.1 * x.1)).sqrt();
        Self {
            neuron,
            module,
            weights,
            norm,
            net: 0.,
            positive: 0.,
            negative: 0.,
            neural: 0.,
            cancellation: 0.,
        }
    }
    fn rotate(&mut self, fluid: &mut Fluid, neurons: &mut [Neuron], dt: f64) -> [f64; 6] {
        let volume = fluid.h.powi(3);
        let scale = volume.sqrt();
        let x = scale / self.norm * accurate_sum(self.weights.iter().map(|&(i, w)| w * fluid.q[i]));
        let v = neurons[self.neuron].v[self.module];
        let angle = 0.1 * self.norm / scale * dt;
        let (c, s) = (angle.cos(), angle.sin());
        let next_x = c * x + s * v;
        let next_v = c * v - s * x;
        let before = accurate_sum(
            self.weights
                .iter()
                .map(|&(i, _)| 0.5 * volume * fluid.q[i] * fluid.q[i]),
        );
        for &(i, w) in &self.weights {
            fluid.q[i] += w / self.norm / scale * (next_x - x);
        }
        let after = accurate_sum(
            self.weights
                .iter()
                .map(|&(i, _)| 0.5 * volume * fluid.q[i] * fluid.q[i]),
        );
        neurons[self.neuron].v[self.module] = next_v;
        let df = after - before;
        let dn = 0.5 * (next_v * next_v - v * v);
        self.net += df;
        self.positive += df.max(0.);
        self.negative += (-df).max(0.);
        self.neural += dn;
        self.cancellation += (df + dn).abs();
        [x, next_x, v, next_v, df, dn]
    }
}
#[derive(Clone)]
struct Condition {
    seed: u64,
    module: usize,
    band: usize,
    distance: usize,
    n: usize,
    dt: f64,
    control: String,
}
impl Condition {
    fn label(&self) -> String {
        format!(
            "s{}_m{}_b{}_d{}_n{}_dt{}_{}",
            self.seed, self.module, self.band, self.distance, self.n, self.dt, self.control
        )
    }
}
fn direct_energy(neurons: &[Neuron]) -> f64 {
    accurate_sum((0..64).map(|m| 0.5 * (0.4 / 6.) * (neurons[0].u[m] - neurons[1].u[m]).powi(2)))
}
fn direct_kick(neurons: &mut [Neuron], dt: f64) {
    for m in 0..64 {
        let f = (0.4 / 6.) * (neurons[1].u[m] - neurons[0].u[m]);
        neurons[0].v[m] += dt * f;
        neurons[1].v[m] -= dt * f;
    }
}
fn neural_dump(dir: &Path, tick: usize, neurons: &[Neuron]) -> io::Result<()> {
    let mut out = BufWriter::new(fs::File::create(dir.join(format!("{tick:06}.neuron.csv")))?);
    writeln!(out, "neuron,module,palette,u,v")?;
    for (id, neuron) in neurons.iter().enumerate() {
        for m in 0..64 {
            writeln!(
                out,
                "{id},{m},{},{:.17e},{:.17e}",
                neuron.palette[m], neuron.u[m], neuron.v[m]
            )?;
        }
    }
    out.flush()
}
#[allow(clippy::too_many_lines)] // Contiguous deterministic recording and integration.
fn case(root: &Path, c: &Condition) -> io::Result<()> {
    let start = Instant::now();
    let label = c.label();
    let dir = root.join(&label);
    fs::create_dir(&dir)?;
    let mut events = fs::OpenOptions::new()
        .append(true)
        .open(root.join("events.csv"))?;
    writeln!(events, "{label},STARTED")?;
    let lattice = Lattice::new(Case {
        seed: c.seed,
        configuration: Configuration::Heterogeneous,
        drive: Drive::Zero,
        ..Case::default()
    })?
    .observe();
    let mut neurons = vec![
        Neuron::new(lattice.neurons[2182].palette),
        Neuron::new(lattice.neurons[2186].palette),
    ];
    let mut fluid = Fluid::new(c.n, c.dt)?;
    let positions = [[10.5, 12.5, 12.5], [10.5 + number(c.distance), 12.5, 12.5]];
    let mut ports = Vec::new();
    if !["OFF", "DIRECT", "FROZEN", "ZERO"].contains(&c.control.as_str()) {
        for (id, position) in positions.into_iter().enumerate() {
            if (id == 0 && c.control == "RECEIVER_ONLY") || (id == 1 && c.control == "SOURCE_ONLY")
            {
                continue;
            }
            for module in [9, 27] {
                ports.push(Port::new(&fluid, id, module, position));
            }
        }
    }
    let metadata = format!(
        "schema,seed,module,band,distance,n,dt,control,source_x,source_y,source_z,receiver_x,receiver_y,receiver_z\n1,{},{},{},{},{},{},{},10.5,12.5,12.5,{},12.5,12.5\n",
        c.seed,
        c.module,
        c.band,
        c.distance,
        c.n,
        c.dt,
        if c.control == "REPEAT" {
            "FLUID"
        } else {
            &c.control
        },
        10.5 + number(c.distance)
    );
    fs::write(dir.join("metadata.csv"), metadata)?;
    let mut metrics = BufWriter::new(fs::File::create(dir.join("metrics.csv"))?);
    writeln!(
        metrics,
        "tick,time,fluid_energy,source_energy,receiver_energy,loss,work,positive_work,direct_energy,exchange_cancellation,source_net,source_positive,source_backflow,receiver_net,receiver_positive,receiver_backflow"
    )?;
    let mut kicks = BufWriter::new(fs::File::create(dir.join("kicks.csv"))?);
    writeln!(kicks, "tick,half,before,after,impulse")?;
    let mut exchanges = BufWriter::new(fs::File::create(dir.join("exchange.csv"))?);
    writeln!(
        exchanges,
        "tick,half,neuron,module,x_before,x_after,v_before,v_after,fluid_delta,neural_delta"
    )?;
    let mut history = BufWriter::new(fs::File::create(dir.join("history.csv"))?);
    writeln!(history, "tick,module,u,v")?;
    let mut probes = BufWriter::new(fs::File::create(dir.join("probes.csv"))?);
    writeln!(probes, "tick,q,wx,wy,wz,density")?;
    let (mut work, mut positive_work) = (0., 0.);
    let ticks = if c.dt.to_bits() == 0.05_f64.to_bits() {
        480
    } else {
        960
    };
    let stride = if ticks == 480 { 2 } else { 4 };
    for tick in 0..=ticks {
        if tick > 0 {
            let time = (number(tick) - 0.5) * c.dt;
            let force = if time <= 12. && !["ZERO", "FROZEN"].contains(&c.control.as_str()) {
                (2. * PI / [12., 8., 6.][c.band] * time).sin() * (PI * time / 12.).sin().powi(2)
            } else {
                0.
            };
            let before = neurons[0].v[c.module];
            let dw = neurons[0].kick(c.module, 0.5 * c.dt * force);
            writeln!(
                kicks,
                "{tick},{},{before:.17e},{:.17e},{:.17e}",
                i32::from(fluid.tick == tick),
                neurons[0].v[c.module],
                0.5 * c.dt * force
            )?;
            work += dw;
            positive_work += dw.max(0.);
            for port in &mut ports {
                let r = port.rotate(&mut fluid, &mut neurons, 0.5 * c.dt);
                writeln!(
                    exchanges,
                    "{tick},{},{},{},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
                    i32::from(fluid.tick == tick),
                    port.neuron,
                    port.module,
                    r[0],
                    r[1],
                    r[2],
                    r[3],
                    r[4],
                    r[5]
                )?;
            }
            if c.control == "DIRECT" {
                direct_kick(&mut neurons, 0.5 * c.dt);
            }
            fluid.advance()?;
            for neuron in &mut neurons {
                neuron.step(c.dt);
            }
            if c.control == "DIRECT" {
                direct_kick(&mut neurons, 0.5 * c.dt);
            }
            for port in ports.iter_mut().rev() {
                let r = port.rotate(&mut fluid, &mut neurons, 0.5 * c.dt);
                writeln!(
                    exchanges,
                    "{tick},{},{},{},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
                    i32::from(fluid.tick == tick),
                    port.neuron,
                    port.module,
                    r[0],
                    r[1],
                    r[2],
                    r[3],
                    r[4],
                    r[5]
                )?;
            }
            let before = neurons[0].v[c.module];
            let dw = neurons[0].kick(c.module, 0.5 * c.dt * force);
            writeln!(
                kicks,
                "{tick},{},{before:.17e},{:.17e},{:.17e}",
                i32::from(fluid.tick == tick),
                neurons[0].v[c.module],
                0.5 * c.dt * force
            )?;
            work += dw;
            positive_work += dw.max(0.);
        }
        if !neurons
            .iter()
            .flat_map(|n| n.u.iter().chain(&n.v))
            .all(|x| x.is_finite())
        {
            return Err(io::Error::other("nonfinite QR10 neurons"));
        }
        let loss = accurate_sum(neurons.iter().map(|n| n.loss));
        let direct = if c.control == "DIRECT" {
            direct_energy(&neurons)
        } else {
            0.
        };
        let totals = |id: usize| {
            [
                accurate_sum(ports.iter().filter(|p| p.neuron == id).map(|p| p.net)),
                accurate_sum(ports.iter().filter(|p| p.neuron == id).map(|p| p.positive)),
                accurate_sum(ports.iter().filter(|p| p.neuron == id).map(|p| p.negative)),
            ]
        };
        let a = totals(0);
        let b = totals(1);
        writeln!(
            metrics,
            "{tick},{:.17e},{:.17e},{:.17e},{:.17e},{loss:.17e},{work:.17e},{positive_work:.17e},{direct:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
            number(tick) * c.dt,
            fluid.energy(),
            neurons[0].energy(),
            neurons[1].energy(),
            accurate_sum(ports.iter().map(|p| p.cancellation)),
            a[0],
            a[1],
            a[2],
            b[0],
            b[1],
            b[2]
        )?;
        if tick % stride == 0 {
            for m in 0..64 {
                writeln!(
                    history,
                    "{tick},{m},{:.17e},{:.17e}",
                    neurons[1].u[m], neurons[1].v[m]
                )?;
            }
            let p = fluid.sample(positions[1]);
            writeln!(
                probes,
                "{tick},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
                p[0], p[1], p[2], p[3], p[4]
            )?;
        }
        if [0, ticks / 2, ticks].contains(&tick) {
            fs::write(
                dir.join(format!("{tick:06}.q10")),
                fluid.encode(Fixture::Zero)?,
            )?;
            neural_dump(&dir, tick, &neurons)?;
        }
    }
    kicks.flush()?;
    exchanges.flush()?;
    metrics.flush()?;
    history.flush()?;
    probes.flush()?;
    let mut exchange = BufWriter::new(fs::File::create(dir.join("ports.csv"))?);
    writeln!(
        exchange,
        "neuron,module,fluid_net,neural_net,positive,backflow,cancellation"
    )?;
    for p in ports {
        writeln!(
            exchange,
            "{},{},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e}",
            p.neuron, p.module, p.net, p.neural, p.positive, p.negative, p.cancellation
        )?;
    }
    exchange.flush()?;
    fs::write(
        dir.join("COMPLETE"),
        b"Executed, independent verdict pending.\n",
    )?;
    writeln!(events, "{label},COMPLETE")?;
    let mut ledger = fs::OpenOptions::new()
        .append(true)
        .open(root.join("ledger.csv"))?;
    writeln!(
        ledger,
        "{label},{:.6},COMPLETE",
        start.elapsed().as_secs_f64()
    )?;
    println!("{label} {:.3}s", start.elapsed().as_secs_f64());
    Ok(())
}
/// Execute the frozen pilot only after independent numerical Level A.
/// # Errors
/// Rejects absent/failed prerequisite, existing output or simulation/IO failure.
pub fn pilot(root: &Path, numerical: &Path) -> io::Result<()> {
    let receipt = fs::read_to_string(numerical.join("verification.json"))?;
    if !receipt.contains("\"level_A\": \"PASS\"") {
        return Err(io::Error::other("QR10 Level A required"));
    }
    fs::create_dir(root)?;
    fs::write(root.join("events.csv"), "case,status\n")?;
    fs::write(root.join("ledger.csv"), "case,elapsed_seconds,status\n")?;
    let mut plan = Vec::new();
    for module in [9, 27] {
        for (n, dt) in [(48, 0.05), (48, 0.025), (96, 0.025)] {
            plan.push(Condition {
                seed: 211,
                module,
                band: 0,
                distance: 2,
                n,
                dt,
                control: "FLUID".into(),
            });
        }
        for control in [
            "ZERO",
            "OFF",
            "FROZEN",
            "SOURCE_ONLY",
            "RECEIVER_ONLY",
            "DIRECT",
        ] {
            plan.push(Condition {
                seed: 211,
                module,
                band: 0,
                distance: 2,
                n: 48,
                dt: 0.05,
                control: control.into(),
            });
        }
    }
    let mut repeat = plan[0].clone();
    repeat.control = "REPEAT".into();
    plan.push(repeat);
    let mut plan_text = String::from("case,initial_status\n");
    for c in &plan {
        use std::fmt::Write as _;
        writeln!(plan_text, "{},NOT_RUN", c.label()).unwrap();
    }
    fs::write(root.join("plan.csv"), plan_text)?;
    for c in plan {
        if let Err(error) = case(root, &c) {
            fs::write(root.join("FAILED"), format!("{}: {error}", c.label()))?;
            return Err(error);
        }
    }
    fs::write(
        root.join("COMPLETE"),
        b"19 pilot executions; independent verdict pending.\n",
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn isolated_adapter_matches_unmodified_qr6_homogeneous_trajectory() {
        use crate::morphic_0006::Medium;
        let mut baseline =
            Medium::new(211, Configuration::Homogeneous, 0.025, "zero", 9, "parity").unwrap();
        let mut neuron = Neuron::new([1; 64]);
        neuron.u[9] = 0.2;
        for id in 0..4096 {
            baseline.state.u[id * 64 + 9] = 0.2;
        }
        // Public match_energy refreshes the historical force cache after state edits.
        let target = baseline.energy().total();
        baseline.match_energy(target).unwrap();
        for _ in 0..8 {
            baseline.advance(0., false).unwrap();
            neuron.step(0.025);
        }
        for m in 0..64 {
            assert!((neuron.u[m] - baseline.state.u[2182 * 64 + m]).abs() < 1e-14);
            assert!((neuron.v[m] - baseline.state.v[2182 * 64 + m]).abs() < 1e-14);
        }
    }
    #[test]
    fn reciprocal_rotation_preserves_combined_energy_and_has_backreaction() {
        let mut fluid = Fluid::new(24, 0.025).unwrap();
        let mut neurons = vec![Neuron::new([1; 64])];
        neurons[0].v[9] = 1.;
        let mut port = Port::new(&fluid, 0, 9, [10.5, 12.5, 12.5]);
        let before = neurons[0].energy();
        port.rotate(&mut fluid, &mut neurons, 1.);
        assert!(fluid.energy() > 0.);
        assert!(neurons[0].v[9] < 1.);
        assert!((fluid.energy() + neurons[0].energy() - before).abs() < 1e-14);
        assert!((port.net + port.neural).abs() < 1e-14);
    }
}
