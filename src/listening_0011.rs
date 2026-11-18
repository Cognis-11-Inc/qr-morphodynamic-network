//! QR11 owned online sensory/trace state and explicit isolated-neuron physics.
use crate::{
    acoustic_0010::{Fluid, accurate_sum, number},
    lattice::{Case, Configuration, Drive, Lattice},
    observation::checksum,
};
use std::{
    fs,
    io::{self, Read},
    path::Path,
};

/// Number of fixed-size trace entries in each independently owned neuron.
pub const TRACES: usize = 405;
const WIDTH: usize = 135;
/// Causal observation controls; no source or class identity is represented.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mode {
    /// Online local observation and traces.
    On,
    /// Sensing active, no trace updates.
    Off,
    /// Causal permutation of anatomical eligibility traces.
    Scrambled,
    /// Read-only observer disabled entirely.
    SensorOff,
}
impl Mode {
    pub(crate) fn parse(s: &str) -> io::Result<Self> {
        match s {
            "ON" => Ok(Self::On),
            "OFF" => Ok(Self::Off),
            "SCRAMBLED" => Ok(Self::Scrambled),
            "SENSOR_OFF" => Ok(Self::SensorOff),
            _ => Err(io::Error::other("QR11 trace mode")),
        }
    }
}
#[derive(Clone)]
pub(crate) struct Memory {
    pub(crate) z: [f64; TRACES],
    pub(crate) packet: [f64; 7],
    pub(crate) previous: f64,
    pub(crate) age: usize,
}
impl Default for Memory {
    fn default() -> Self {
        Self {
            z: [0.; TRACES],
            packet: [0.; 7],
            previous: 0.,
            age: 0,
        }
    }
}
fn bound(x: f64, scale: f64) -> f64 {
    x / (scale + x.abs())
}
#[derive(Clone)]
pub(crate) struct Neuron {
    pub(crate) palette: [u8; 64],
    pub(crate) u: [f64; 64],
    pub(crate) v: [f64; 64],
    omega: [f64; 64],
    gamma: [f64; 64],
    edges: Vec<(usize, usize, f64)>,
    pub(crate) loss: f64,
    pub(crate) memory: Memory,
    pub(crate) committed: bool,
}
fn links(m: usize) -> Vec<usize> {
    (0..64)
        .filter(|&j| (m / 8).abs_diff(j / 8) + (m % 8).abs_diff(j % 8) == 1)
        .collect()
}
impl Neuron {
    pub(crate) fn new(palette: [u8; 64]) -> Self {
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
            memory: Memory::default(),
            committed: false,
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
    pub(crate) fn energy(&self) -> f64 {
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
impl Neuron {
    fn record(&mut self, local: [f64; 6], dt: f64, mode: Mode) {
        self.memory.age += 1;
        if mode == Mode::SensorOff {
            return;
        }
        let derivative = (local[0] - self.memory.previous) / dt;
        self.memory.previous = local[0];
        self.memory.packet = [
            local[0], local[1], local[2], local[3], local[4], local[5], derivative,
        ];
        if mode == Mode::Off {
            return;
        }
        let scales = [0.01, 0.01, 0.01, 0.01, 0.0001, 0.0001, 0.01];
        let mut phi = [0.; WIDTH];
        for j in 0..7 {
            phi[j] = bound(self.memory.packet[j], scales[j]);
        }
        for m in 0..64 {
            let adjacent = links(m);
            let strain = accurate_sum(adjacent.iter().map(|&j| (self.u[m] - self.u[j]).powi(2)))
                / number(adjacent.len());
            phi[7 + m] = bound(self.v[m].powi(2) + 0.25 * strain, 1e-8);
            phi[71 + m] = bound(self.v[m] * local[0], 1e-6);
        }
        for (k, tau) in [0.5, 2., 8.].into_iter().enumerate() {
            let a = (-dt / tau).exp();
            for (j, value) in phi.iter().enumerate() {
                self.memory.z[k * WIDTH + j] = a * self.memory.z[k * WIDTH + j] + (1. - a) * value;
            }
        }
        if mode == Mode::Scrambled && (number(self.memory.age) * dt).fract().abs() < 1e-12 {
            for k in 0..3 {
                self.memory.z[k * WIDTH + 7..k * WIDTH + 71].rotate_right(1);
                self.memory.z[k * WIDTH + 71..(k + 1) * WIDTH].rotate_right(1);
            }
        }
    }
    pub(crate) fn scores(&self) -> [f64; 64] {
        std::array::from_fn(|m| {
            self.memory.z[2 * WIDTH + 7 + m]
                + 0.5 * (self.memory.z[2 * WIDTH + 71 + m] - self.memory.z[71 + m]).abs()
        })
    }
    pub(crate) fn commit(
        &mut self,
        enabled: bool,
        dt: f64,
    ) -> io::Result<(f64, Vec<(usize, usize)>)> {
        if self.committed || number(self.memory.age) * dt < 48. - 1e-12 {
            return Err(io::Error::other(
                "QR11 commit requires end48 uncommitted state",
            ));
        }
        let s = self.scores();
        let maximum = s.iter().copied().fold(0., f64::max);
        let old = self.palette;
        let mut candidates = Vec::new();
        for m in 0..64 {
            for n in links(m) {
                if m < n
                    && old[m] != old[n]
                    && self.memory.z[2 * WIDTH + 7 + m] >= 0.01
                    && self.memory.z[2 * WIDTH + 7 + n] >= 0.01
                    && s[m] >= 0.01
                    && s[n] >= 0.01
                    && (s[m] >= 0.05 * maximum || s[n] >= 0.05 * maximum)
                {
                    candidates.push((m, n));
                }
            }
        }
        candidates.sort_by(|&(a, b), &(c, d)| {
            (s[c] + s[d])
                .total_cmp(&(s[a] + s[b]))
                .then((a, b).cmp(&(c, d)))
        });
        let mut chosen = Vec::new();
        let mut used = [false; 64];
        let mut after = old;
        for (m, n) in candidates {
            if enabled && chosen.len() < 4 && !used[m] && !used[n] {
                after[m] = old[n];
                after[n] = old[m];
                used[m] = true;
                used[n] = true;
                chosen.push((m, n));
            }
        }
        let before = self.energy();
        self.install(after)?;
        self.committed = true;
        Ok((self.energy() - before, chosen))
    }
    pub(crate) fn install(&mut self, p: [u8; 64]) -> io::Result<()> {
        if p.iter().any(|&x| x > 4) {
            return Err(io::Error::other("QR11 illegal palette"));
        }
        let rebuilt = Self::new(p);
        self.palette = p;
        self.omega = rebuilt.omega;
        self.gamma = rebuilt.gamma;
        self.edges = rebuilt.edges;
        Ok(())
    }
    pub(crate) fn encode(&self, out: &mut Vec<u8>) {
        out.extend_from_slice(&self.palette);
        for x in self
            .u
            .iter()
            .chain(&self.v)
            .chain(&self.memory.packet)
            .chain(std::iter::once(&self.memory.previous))
        {
            out.extend_from_slice(&x.to_le_bytes());
        }
        out.extend_from_slice(&(self.memory.age as u64).to_le_bytes());
        for x in self.memory.z.iter().chain(std::iter::once(&self.loss)) {
            out.extend_from_slice(&x.to_le_bytes());
        }
        out.extend_from_slice(&u64::from(self.committed).to_le_bytes());
    }
}
#[derive(Default)]
struct Sum {
    sum: f64,
    correction: f64,
}
impl Sum {
    fn add(&mut self, x: f64) {
        let next = self.sum + x;
        self.correction += if self.sum.abs() >= x.abs() {
            (self.sum - next) + x
        } else {
            (x - next) + self.sum
        };
        self.sum = next;
    }
    fn value(&self) -> f64 {
        self.sum + self.correction
    }
}
/// Isolated stationary body and reciprocal fluid; global state belongs to apparatus.
pub(crate) struct World {
    pub(crate) fluid: Fluid,
    pub(crate) neurons: Vec<Neuron>,
    ports: Vec<Port>,
    kernels: Vec<Vec<(usize, f64)>>,
    positions: Vec<[f64; 3]>,
    work: Sum,
    positive: Sum,
    negative: Sum,
    pub(crate) kicks: Vec<(usize, usize, f64, f64, f64)>,
    pub(crate) exchanges: Vec<(usize, usize, usize, [f64; 6])>,
}
impl World {
    pub(crate) fn new(
        seed: u64,
        n: usize,
        dt: f64,
        distance: usize,
        three: bool,
        coupled: bool,
    ) -> io::Result<Self> {
        let lattice = Lattice::new(Case {
            seed,
            configuration: Configuration::Heterogeneous,
            drive: Drive::Zero,
            ..Case::default()
        })?
        .observe();
        let ids = if three {
            vec![2182, 2186, 2184]
        } else {
            vec![2182, 2186]
        };
        let neurons = ids
            .into_iter()
            .map(|id| Neuron::new(lattice.neurons[id].palette))
            .collect();
        let fluid = Fluid::new(n, dt)?;
        let mut positions = vec![[10.5, 12.5, 12.5], [10.5 + number(distance), 12.5, 12.5]];
        if three {
            positions.push([10.5, 14.5, 12.5]);
        }
        let mut ports = Vec::new();
        let mut kernels = Vec::new();
        for (id, position) in positions.iter().copied().enumerate() {
            let base = Port::new(&fluid, id, 9, position);
            kernels.push(base.weights.clone());
            if coupled {
                ports.push(base);
                ports.push(Port::new(&fluid, id, 27, position));
            }
        }
        Ok(Self {
            fluid,
            neurons,
            ports,
            kernels,
            positions,
            work: Sum::default(),
            positive: Sum::default(),
            negative: Sum::default(),
            kicks: Vec::new(),
            exchanges: Vec::new(),
        })
    }
    pub(crate) fn advance(&mut self, forces: &[(usize, usize, f64)], mode: Mode) -> io::Result<()> {
        self.kicks.clear();
        self.exchanges.clear();
        let dt = self.fluid.dt;
        let mut local_work = vec![0.; self.neurons.len()];
        for half in 0..2 {
            if half == 1 {
                self.fluid.advance()?;
                for neuron in &mut self.neurons {
                    neuron.step(dt);
                }
                for p in self.ports.iter_mut().rev() {
                    let r = p.rotate(&mut self.fluid, &mut self.neurons, 0.5 * dt);
                    local_work[p.neuron] += r[4];
                    self.exchanges.push((half, p.neuron, p.module, r));
                }
            }
            for &(id, module, f) in forces {
                let before = self.neurons[id].v[module];
                let impulse = 0.5 * dt * f;
                let dw = self.neurons[id].kick(module, impulse);
                self.work.add(dw);
                self.positive.add(dw.max(0.));
                self.negative.add((-dw).max(0.));
                self.kicks
                    .push((half, id, before, self.neurons[id].v[module], impulse));
            }
            if half == 0 {
                for p in &mut self.ports {
                    let r = p.rotate(&mut self.fluid, &mut self.neurons, 0.5 * dt);
                    local_work[p.neuron] += r[4];
                    self.exchanges.push((half, p.neuron, p.module, r));
                }
            }
        }
        let packets = self
            .kernels
            .iter()
            .enumerate()
            .map(|(id, kernel)| {
                let mut out = [0.; 6];
                out[0] = accurate_sum(kernel.iter().map(|&(i, w)| w * self.fluid.q[i]));
                for axis in 0..3 {
                    let stride = self.fluid.n.pow(u32::try_from(axis).unwrap());
                    out[1 + axis] = accurate_sum(kernel.iter().map(|&(i, w)| {
                        let left = if (i / stride).is_multiple_of(self.fluid.n) {
                            0.
                        } else {
                            self.fluid.w[axis][i - stride]
                        };
                        w * f64::midpoint(self.fluid.w[axis][i], left)
                    }));
                }
                out[4] = accurate_sum(kernel.iter().map(|&(i, w)| w * self.fluid.cell_energy(i)));
                out[5] = -local_work[id] / dt;
                out
            })
            .collect::<Vec<_>>();
        for (neuron, packet) in self.neurons.iter_mut().zip(packets) {
            neuron.record(packet, dt, mode);
        }
        if !self.neurons.iter().all(|node| {
            node.u
                .iter()
                .chain(&node.v)
                .chain(&node.memory.packet)
                .chain(&node.memory.z)
                .all(|x| x.is_finite())
                && node.memory.z.iter().all(|x| x.abs() <= 1. + 1e-14)
        }) {
            return Err(io::Error::other("QR11 finite/bounded state"));
        }
        Ok(())
    }
    pub(crate) fn totals(&self) -> [f64; 11] {
        [
            self.fluid.energy(),
            accurate_sum(self.neurons.iter().map(Neuron::energy)),
            self.neurons[1].energy(),
            accurate_sum(self.neurons.iter().map(|n| n.loss)),
            self.work.value(),
            self.positive.value(),
            self.negative.value(),
            accurate_sum(self.ports.iter().filter(|p| p.neuron != 1).map(|p| p.net)),
            accurate_sum(
                self.ports
                    .iter()
                    .filter(|p| p.neuron != 1)
                    .map(|p| p.positive),
            ),
            accurate_sum(
                self.ports
                    .iter()
                    .filter(|p| p.neuron != 1)
                    .map(|p| p.negative),
            ),
            accurate_sum(self.ports.iter().map(|p| p.cancellation)),
        ]
    }
    pub(crate) fn fluid_bytes(&self) -> io::Result<Vec<u8>> {
        let mut b = self.fluid.encode(crate::acoustic_0010::Fixture::Zero)?;
        b[..8].copy_from_slice(b"QR11AC01");
        let end = b.len() - 8;
        let sum = checksum(&b[..end]);
        b[end..].copy_from_slice(&sum.to_le_bytes());
        Ok(b)
    }
    pub(crate) fn frame(&self) -> Vec<u8> {
        let mut b = (self.fluid.tick as u64).to_le_bytes().to_vec();
        for neuron in &self.neurons {
            neuron.encode(&mut b);
        }
        let c = checksum(&b);
        b.extend_from_slice(&c.to_le_bytes());
        b
    }
    pub(crate) fn snapshot(&self) -> Vec<u8> {
        let mut b = b"QR11NEU1".to_vec();
        for x in [
            1,
            self.neurons.len() as u64,
            self.fluid.tick as u64,
            self.fluid.dt.to_bits(),
        ] {
            b.extend_from_slice(&x.to_le_bytes());
        }
        for neuron in &self.neurons {
            neuron.encode(&mut b);
        }
        b.extend_from_slice(&checksum(&b).to_le_bytes());
        b
    }
    pub(crate) fn stream_header(&self, ticks: usize) -> Vec<u8> {
        let mut b = b"QR11OBS1".to_vec();
        for x in [
            1,
            self.neurons.len() as u64,
            self.fluid.n as u64,
            self.fluid.dt.to_bits(),
            ticks as u64,
        ] {
            b.extend_from_slice(&x.to_le_bytes());
        }
        b
    }
    pub(crate) fn reset(&mut self) -> io::Result<f64> {
        let removed = self.fluid.energy() + accurate_sum(self.neurons.iter().map(Neuron::energy));
        self.fluid = Fluid::new(self.fluid.n, self.fluid.dt)?;
        for n in &mut self.neurons {
            *n = Neuron::new(n.palette);
        }
        let mut ports = Vec::new();
        for (id, pos) in self.positions.iter().copied().enumerate() {
            for module in [9, 27] {
                ports.push(Port::new(&self.fluid, id, module, pos));
            }
        }
        self.ports = ports;
        self.work = Sum::default();
        self.positive = Sum::default();
        self.negative = Sum::default();
        self.kicks.clear();
        self.exchanges.clear();
        Ok(removed)
    }
}
fn read_u64(cursor: &mut io::Cursor<&[u8]>) -> io::Result<u64> {
    let mut b = [0; 8];
    cursor.read_exact(&mut b)?;
    Ok(u64::from_le_bytes(b))
}
fn read_f64(cursor: &mut io::Cursor<&[u8]>) -> io::Result<f64> {
    Ok(f64::from_bits(read_u64(cursor)?))
}
pub(crate) fn load_neurons(path: &Path) -> io::Result<(usize, f64, Vec<Neuron>)> {
    let b = fs::read(path)?;
    if b.len() < 48
        || &b[..8] != b"QR11NEU1"
        || checksum(&b[..b.len() - 8]) != u64::from_le_bytes(b[b.len() - 8..].try_into().unwrap())
    {
        return Err(io::Error::other("QR11 neuron snapshot checksum"));
    }
    let mut cursor = io::Cursor::new(&b[8..b.len() - 8]);
    let version = read_u64(&mut cursor)?;
    let count = usize::try_from(read_u64(&mut cursor)?).map_err(io::Error::other)?;
    let tick = usize::try_from(read_u64(&mut cursor)?).map_err(io::Error::other)?;
    let dt = read_f64(&mut cursor)?;
    if version != 1
        || ![2, 3].contains(&count)
        || b.len() != 48 + 4416 * count
        || ![0.05, 0.025].contains(&dt)
    {
        return Err(io::Error::other("QR11 neuron dimensions"));
    }
    let mut nodes = Vec::new();
    for _ in 0..count {
        let mut p = [0; 64];
        cursor.read_exact(&mut p)?;
        if p.iter().any(|&x| x > 4) {
            return Err(io::Error::other("QR11 palette"));
        }
        let mut node = Neuron::new(p);
        for x in node
            .u
            .iter_mut()
            .chain(&mut node.v)
            .chain(&mut node.memory.packet)
            .chain(std::iter::once(&mut node.memory.previous))
        {
            *x = read_f64(&mut cursor)?;
        }
        node.memory.age = usize::try_from(read_u64(&mut cursor)?).map_err(io::Error::other)?;
        for x in node
            .memory
            .z
            .iter_mut()
            .chain(std::iter::once(&mut node.loss))
        {
            *x = read_f64(&mut cursor)?;
        }
        let flag = read_u64(&mut cursor)?;
        if flag > 1
            || !node
                .u
                .iter()
                .chain(&node.v)
                .chain(&node.memory.packet)
                .chain(&node.memory.z)
                .chain(std::iter::once(&node.memory.previous))
                .chain(std::iter::once(&node.loss))
                .all(|x| x.is_finite())
            || node.memory.z.iter().any(|x| x.abs() > 1. + 1e-14)
        {
            return Err(io::Error::other("QR11 invalid bounded neuron state"));
        }
        node.committed = flag == 1;
        nodes.push(node);
    }
    Ok((tick, dt, nodes))
}
/// Save a committed owned state without representing it as a new fluid trajectory.
/// # Errors
/// Reports file creation failures.
pub(crate) fn write_nodes(path: &Path, tick: usize, dt: f64, nodes: &[Neuron]) -> io::Result<()> {
    let mut b = b"QR11NEU1".to_vec();
    for x in [1, nodes.len() as u64, tick as u64, dt.to_bits()] {
        b.extend_from_slice(&x.to_le_bytes());
    }
    for n in nodes {
        n.encode(&mut b);
    }
    b.extend_from_slice(&checksum(&b).to_le_bytes());
    fs::write(path, b)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn passive_sensing_is_owned_bounded_and_does_not_change_physics() {
        let mut on = World::new(997, 24, 0.05, 4, false, true).unwrap();
        let mut off = World::new(997, 24, 0.05, 4, false, true).unwrap();
        for _ in 0..80 {
            on.advance(&[(0, 9, 0.7)], Mode::On).unwrap();
            off.advance(&[(0, 9, 0.7)], Mode::SensorOff).unwrap();
        }
        assert_eq!(on.fluid_bytes().unwrap(), off.fluid_bytes().unwrap());
        for (a, b) in on.neurons.iter().zip(&off.neurons) {
            assert_eq!(a.u, b.u);
            assert_eq!(a.v, b.v);
            assert!(a.memory.z.iter().all(|x| x.abs() <= 1.));
            assert!(b.memory.z.iter().all(|&x| x == 0.));
        }
        assert!(on.neurons[0].memory.z.iter().any(|&x| x != 0.));
        let other = on.neurons[1].memory.z;
        on.neurons[0].memory.z[0] = 0.42;
        assert_eq!(other, on.neurons[1].memory.z);
    }
    #[test]
    fn bounded_state_roundtrip_and_complete_reset() {
        let mut w = World::new(991, 24, 0.05, 4, false, true).unwrap();
        for _ in 0..12 {
            w.advance(&[(0, 9, 1.)], Mode::On).unwrap();
        }
        let path = std::env::temp_dir().join(format!("qr11-state-{}.n11", std::process::id()));
        let bytes = w.snapshot();
        fs::write(&path, &bytes).unwrap();
        let (tick, dt, nodes) = load_neurons(&path).unwrap();
        assert_eq!(tick, 12);
        assert_eq!(dt, 0.05);
        let mut restored = Vec::new();
        for n in nodes {
            n.encode(&mut restored);
        }
        assert_eq!(&bytes[40..bytes.len() - 8], restored);
        let mut corrupt = bytes;
        corrupt[50] ^= 1;
        fs::write(&path, corrupt).unwrap();
        assert!(load_neurons(&path).is_err());
        fs::remove_file(path).unwrap();
        let palettes: Vec<_> = w.neurons.iter().map(|n| n.palette).collect();
        assert!(w.reset().unwrap() > 0.);
        assert!(
            w.fluid
                .q
                .iter()
                .chain(w.fluid.w.iter().flatten())
                .all(|&x| x == 0.)
        );
        for (n, p) in w.neurons.iter().zip(palettes) {
            assert_eq!(n.palette, p);
            assert_eq!(n.memory.age, 0);
            assert!(!n.committed);
            assert!(
                n.u.iter()
                    .chain(&n.v)
                    .chain(&n.memory.z)
                    .chain(&n.memory.packet)
                    .all(|&x| x == 0.)
            );
        }
        assert!(w.totals().iter().all(|&x| x == 0.));
    }
    #[test]
    fn eligible_swaps_are_local_histogram_preserving_and_account_work() {
        let p = std::array::from_fn(|m| u8::try_from(m % 5).unwrap());
        let mut n = Neuron::new(p);
        n.memory.age = 960;
        n.memory.z[277 + 9] = 0.5;
        n.memory.z[277 + 10] = 0.4;
        n.u[9] = 0.2;
        let before = n.energy();
        let (work, edges) = n.commit(true, 0.05).unwrap();
        assert_eq!(edges, vec![(9, 10)]);
        assert_eq!(n.palette[9], p[10]);
        assert_eq!(n.palette[10], p[9]);
        assert_eq!(work, n.energy() - before);
        assert_eq!(n.u[9], 0.2);
        let mut a = p;
        let mut b = n.palette;
        a.sort_unstable();
        b.sort_unstable();
        assert_eq!(a, b);
        assert!(n.commit(true, 0.05).is_err());
        let mut quiet = Neuron::new(p);
        quiet.memory.age = 960;
        assert_eq!(quiet.commit(true, 0.05).unwrap().1, []);
        assert_eq!(quiet.palette, p);
    }
}
