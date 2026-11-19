//! QR12 four-body shared-fluid physics and local repeated morphology.
// Intrinsic, sensing and reciprocal arithmetic copied unchanged from QR11.
use crate::{
    acoustic_0010::{Fluid, accurate_sum, number},
    listening_0011::Mode,
    observation::checksum,
};
use std::{fs, io, path::Path};
const TRACES: usize = 405;
const WIDTH: usize = 135;
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
#[derive(Clone)]
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
    pub(crate) fn install(&mut self, p: [u8; 64]) -> io::Result<()> {
        if p.iter().any(|&x| x > 4) {
            return Err(io::Error::other("QR12 illegal palette"));
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
#[derive(Clone, Default)]
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
#[derive(Clone, Default)]
struct Controller {
    latch: bool,
    last: usize,
    events: usize,
    attempts: usize,
    work: Sum,
    budget: usize,
    vetoes: usize,
}
impl Controller {
    fn encode(&self, b: &mut Vec<u8>) {
        for x in [
            u64::from(self.latch),
            self.last as u64,
            self.events as u64,
            self.attempts as u64,
            self.work.sum.to_bits(),
            self.work.correction.to_bits(),
            self.budget as u64,
            self.vetoes as u64,
        ] {
            b.extend_from_slice(&x.to_le_bytes());
        }
    }
    fn observe(&mut self, node: &Neuron) {
        let h = node.memory.z[277..341].iter().copied().fold(0., f64::max);
        if h >= 0.02 {
            self.latch = true;
        } else if h < 0.005 {
            self.latch = false;
        }
    }
    fn propose(&self, node: &Neuron, dt: f64) -> Option<(usize, usize)> {
        let time = number(node.memory.age) * dt;
        if !self.latch || self.budget >= 3 || time - number(self.last) * dt < 8. {
            return None;
        }
        candidate(node)
    }
}
fn candidate(node: &Neuron) -> Option<(usize, usize)> {
    let s = node.scores();
    let max = s.iter().copied().fold(0., f64::max);
    let mut edges = Vec::new();
    for m in 0..64 {
        for n in links(m) {
            if m < n
                && node.palette[m] != node.palette[n]
                && node.memory.z[277 + m] >= 0.01
                && node.memory.z[277 + n] >= 0.01
                && s[m] >= 0.01
                && s[n] >= 0.01
                && (s[m] >= 0.05 * max || s[n] >= 0.05 * max)
            {
                edges.push((m, n));
            }
        }
    }
    edges.sort_by(|&(a, b), &(c, d)| {
        (s[c] + s[d])
            .total_cmp(&(s[a] + s[b]))
            .then((a, b).cmp(&(c, d)))
    });
    edges.first().copied()
}
fn external(node: &Neuron) -> Option<(usize, usize)> {
    (0..64)
        .flat_map(|m| links(m).into_iter().map(move |n| (m, n)))
        .find(|&(m, n)| m < n && node.palette[m] != node.palette[n])
}
fn palette(seed: u64, id: usize) -> [u8; 64] {
    std::array::from_fn(|m| {
        let mut x =
            seed.wrapping_add(0x9E37_79B9_7F4A_7C15_u64.wrapping_mul((id * 64 + m + 1) as u64));
        x = (x ^ (x >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        x = (x ^ (x >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        u8::try_from((x ^ (x >> 31)) % 5).unwrap()
    })
}
/// Observer event record; role/policy is external to local proposal generation.
pub(crate) struct Event {
    pub id: usize,
    pub pair: Option<(usize, usize)>,
    pub accepted: bool,
    pub before: [u8; 64],
    pub after: [u8; 64],
    pub score: [f64; 64],
    pub h: [f64; 64],
    pub work: f64,
    pub cause: &'static str,
    pub latch: bool,
}
/// Complete actual population and its single shared-fluid owner.
#[derive(Clone)]
pub(crate) struct World {
    pub fluid: Fluid,
    pub neurons: Vec<Neuron>,
    controllers: Vec<Controller>,
    ports: Vec<Port>,
    pub positions: Vec<[f64; 3]>,
    pub seed: u64,
    pub geometry: usize,
    pub scalar: bool,
    pub mask: usize,
    work: Sum,
    positive: Sum,
    negative: Sum,
    switch: Sum,
    pub kicks: Vec<(usize, usize, usize, f64, f64, f64)>,
    pub exchanges: Vec<(usize, usize, usize, [f64; 6])>,
}
impl World {
    pub fn new(
        seed: u64,
        n: usize,
        dt: f64,
        geometry: usize,
        scalar: bool,
        mask: usize,
    ) -> io::Result<Self> {
        let all = match geometry {
            1 => vec![
                [9., 9., 12.],
                [15., 9., 12.],
                [9., 15., 12.],
                [15., 15., 12.],
            ],
            2 => vec![[10.5, 12.5, 12.5], [14.5, 12.5, 12.5]],
            _ => vec![
                [10., 10., 12.],
                [14., 10., 12.],
                [10., 14., 12.],
                [14., 14., 12.],
            ],
        };
        let selected: Vec<usize> = match geometry {
            10..=13 => vec![geometry - 10],
            20 => vec![0, 1],
            21 => vec![2, 3],
            _ => (0..all.len()).collect(),
        };
        let positions = selected.iter().map(|&i| all[i]).collect::<Vec<_>>();
        let ids = [2182, 2186, 2184, 2188];
        let neurons = selected
            .iter()
            .map(|&i| Neuron::new(palette(seed, ids[i])))
            .collect::<Vec<_>>();
        let fluid = Fluid::new(n, dt)?;
        let mut ports = Vec::new();
        for (id, &pos) in positions.iter().enumerate() {
            for module in [9, 27] {
                ports.push(Port::new(&fluid, id, module, pos));
            }
        }
        Ok(Self {
            controllers: vec![Controller::default(); neurons.len()],
            fluid,
            neurons,
            ports,
            positions,
            seed,
            geometry,
            scalar,
            mask,
            work: Sum::default(),
            positive: Sum::default(),
            negative: Sum::default(),
            switch: Sum::default(),
            kicks: Vec::new(),
            exchanges: Vec::new(),
        })
    }
    pub fn node_energy(&self, id: usize) -> f64 {
        let n = &self.neurons[id];
        if self.scalar {
            accurate_sum([9, 27].map(|m| f64::midpoint(n.u[m] * n.u[m], n.v[m] * n.v[m])))
        } else {
            n.energy()
        }
    }
    fn intrinsic(&mut self) {
        let dt = self.fluid.dt;
        for node in &mut self.neurons {
            if self.scalar {
                for m in [9, 27] {
                    let before = node.v[m];
                    node.v[m] *= (-0.1 * dt * 0.5).exp();
                    node.loss += 0.5 * (before * before - node.v[m] * node.v[m]);
                    node.v[m] -= 0.5 * dt * node.u[m];
                    node.u[m] += dt * node.v[m];
                    node.v[m] -= 0.5 * dt * node.u[m];
                    let before = node.v[m];
                    node.v[m] *= (-0.1 * dt * 0.5).exp();
                    node.loss += 0.5 * (before * before - node.v[m] * node.v[m]);
                }
            } else {
                node.step(dt);
            }
        }
    }
    pub fn kick(&mut self, half: usize, id: usize, module: usize, impulse: f64) {
        let before = self.neurons[id].v[module];
        let dw = self.neurons[id].kick(module, impulse);
        self.work.add(dw);
        self.positive.add(dw.max(0.));
        self.negative.add((-dw).max(0.));
        self.kicks.push((
            half,
            id,
            module,
            before,
            self.neurons[id].v[module],
            impulse,
        ));
    }
    pub fn advance(&mut self, forces: &[(usize, usize, f64)], mode: Mode) -> io::Result<()> {
        self.kicks.clear();
        self.exchanges.clear();
        let dt = self.fluid.dt;
        let mut local_work = vec![0.; self.neurons.len()];
        for half in 0..2 {
            if half == 1 {
                self.fluid.advance()?;
                self.intrinsic();
                for p in self.ports.iter_mut().rev() {
                    if self.mask & (1 << p.neuron) != 0 {
                        let r = p.rotate(&mut self.fluid, &mut self.neurons, 0.5 * dt);
                        local_work[p.neuron] += r[4];
                        self.exchanges.push((half, p.neuron, p.module, r));
                    }
                }
            }
            for &(id, module, f) in forces {
                self.kick(half, id, module, 0.5 * dt * f);
            }
            if half == 0 {
                for p in &mut self.ports {
                    if self.mask & (1 << p.neuron) != 0 {
                        let r = p.rotate(&mut self.fluid, &mut self.neurons, 0.5 * dt);
                        local_work[p.neuron] += r[4];
                        self.exchanges.push((half, p.neuron, p.module, r));
                    }
                }
            }
        }
        for (id, &local_transfer) in local_work.iter().enumerate() {
            let kernel = &self.ports[2 * id].weights;
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
            out[5] = -local_transfer / dt;
            self.neurons[id].record(out, dt, mode);
        }
        if self.neurons.iter().any(|n| {
            !n.u.iter()
                .chain(&n.v)
                .chain(&n.memory.z)
                .chain(&n.memory.packet)
                .all(|x| x.is_finite())
                || n.memory.z.iter().any(|x| x.abs() > 1. + 1e-14)
        }) {
            return Err(io::Error::other("QR12 finite/bounded state"));
        }
        Ok(())
    }
    pub fn events(&mut self, policy: &str) -> io::Result<Vec<Event>> {
        let mut result = Vec::new();
        let dt = self.fluid.dt;
        for id in 0..self.neurons.len() {
            let n = &self.neurons[id];
            let ctl = &mut self.controllers[id];
            ctl.observe(n);
            let time = number(n.memory.age) * dt;
            if ![16., 24., 32.].contains(&time) {
                continue;
            }
            ctl.attempts += 1;
            let pair = if policy == "NONADAPTIVE" || policy == "EXTERNAL_TARGET" {
                external(n)
            } else {
                ctl.propose(n, dt)
            };
            let accepted = pair.is_some()
                && ctl.budget < 3
                && (matches!(policy, "ADAPTIVE" | "NONADAPTIVE")
                    || matches!(policy, "PERMIT" | "EXTERNAL_TARGET") && id == 0);
            let cause = if policy == "NONADAPTIVE" || policy == "EXTERNAL_TARGET" {
                "EXTERNAL"
            } else {
                "LOCAL"
            };
            let before = n.palette;
            let score = n.scores();
            let h = std::array::from_fn(|m| n.memory.z[277 + m]);
            let e0 = n.energy();
            if let Some((a, b)) = pair {
                if accepted {
                    let mut p = before;
                    p.swap(a, b);
                    self.neurons[id].install(p)?;
                    ctl.events += 1;
                    ctl.budget += 1;
                    ctl.last = self.fluid.tick;
                } else {
                    ctl.vetoes += 1;
                }
            }
            let work = self.neurons[id].energy() - e0;
            if accepted {
                ctl.work.add(work);
                self.switch.add(work);
                self.positive.add(work.max(0.));
                self.negative.add((-work).max(0.));
            }
            result.push(Event {
                id,
                pair,
                accepted,
                before,
                after: self.neurons[id].palette,
                score,
                h,
                work,
                cause,
                latch: ctl.latch,
            });
        }
        Ok(result)
    }
    pub fn sham(&mut self, dw: f64) -> io::Result<()> {
        let node = &mut self.neurons[0];
        let k = accurate_sum(node.v.iter().map(|v| 0.5 * v * v));
        if k <= 0. || k + dw < 0. {
            return Err(io::Error::other("QR12 sham infeasible"));
        }
        let a = (1. + dw / k).sqrt();
        let before = node.energy();
        for v in &mut node.v {
            *v *= a;
        }
        let actual = node.energy() - before;
        self.switch.add(actual);
        self.positive.add(actual.max(0.));
        self.negative.add((-actual).max(0.));
        Ok(())
    }
    pub fn totals(&self) -> [f64; 9] {
        [
            self.fluid.energy(),
            accurate_sum((0..self.neurons.len()).map(|i| self.node_energy(i))),
            accurate_sum(self.neurons.iter().map(|n| n.loss)),
            self.work.value(),
            self.switch.value(),
            self.positive.value(),
            self.negative.value(),
            accurate_sum(self.ports.iter().map(|p| p.net)),
            accurate_sum(self.ports.iter().map(|p| p.cancellation)),
        ]
    }
    pub fn nodes_bytes(&self) -> Vec<u8> {
        let mut b = Vec::new();
        for (n, c) in self.neurons.iter().zip(&self.controllers) {
            n.encode(&mut b);
            c.encode(&mut b);
        }
        b
    }
    pub fn frame(&self) -> Vec<u8> {
        let mut b = (self.fluid.tick as u64).to_le_bytes().to_vec();
        b.extend(self.nodes_bytes());
        b.extend(checksum(&b).to_le_bytes());
        b
    }
    pub fn snapshot(&self) -> Vec<u8> {
        let mut b = b"QR12FUL1".to_vec();
        for x in [
            1,
            self.fluid.n as u64,
            self.fluid.tick as u64,
            self.fluid.dt.to_bits(),
            self.seed,
            self.neurons.len() as u64,
            self.geometry as u64,
            u64::from(self.scalar),
            self.mask as u64,
        ] {
            b.extend(x.to_le_bytes());
        }
        for p in &self.positions {
            for x in p {
                b.extend(x.to_le_bytes());
            }
        }
        for x in self.fluid.q.iter().chain(self.fluid.w.iter().flatten()) {
            b.extend(x.to_le_bytes());
        }
        b.extend(self.nodes_bytes());
        for s in [&self.work, &self.positive, &self.negative, &self.switch] {
            b.extend(s.sum.to_le_bytes());
            b.extend(s.correction.to_le_bytes());
        }
        for p in &self.ports {
            for x in [
                p.norm,
                p.net,
                p.positive,
                p.negative,
                p.neural,
                p.cancellation,
            ] {
                b.extend(x.to_le_bytes());
            }
        }
        b.extend(checksum(&b).to_le_bytes());
        b
    }
    #[allow(clippy::many_single_char_names)] // Binary codec uses conventional compact field names.
    pub fn load(path: &Path) -> io::Result<Self> {
        let b = fs::read(path)?;
        if b.len() < 152
            || &b[..8] != b"QR12FUL1"
            || checksum(&b[..b.len() - 8])
                != u64::from_le_bytes(b[b.len() - 8..].try_into().unwrap())
        {
            return Err(io::Error::other("QR12 checkpoint checksum/magic"));
        }
        let mut r = Reader { b: &b, i: 8 };
        if r.word()? != 1 {
            return Err(io::Error::other("QR12 checkpoint version"));
        }
        let n = r.usize()?;
        let tick = r.usize()?;
        let dt = r.float()?;
        let seed = r.word()?;
        let count = r.usize()?;
        let geometry = r.usize()?;
        let scalar = r.word()? != 0;
        let mask = r.usize()?;
        let mut w = Self::new(seed, n, dt, geometry, scalar, mask)?;
        if w.neurons.len() != count || b.len() != 152 + 4600 * count + 32 * n.pow(3) {
            return Err(io::Error::other("QR12 checkpoint layout"));
        }
        for pos in &w.positions {
            for &v in pos {
                if r.float()?.to_bits() != v.to_bits() {
                    return Err(io::Error::other("QR12 geometry ABI"));
                }
            }
        }
        w.fluid.tick = tick;
        for x in w.fluid.q.iter_mut().chain(w.fluid.w.iter_mut().flatten()) {
            *x = r.float()?;
        }
        for (node, c) in w.neurons.iter_mut().zip(&mut w.controllers) {
            let mut p = [0; 64];
            for v in &mut p {
                *v = r.byte()?;
            }
            node.install(p)?;
            for x in node
                .u
                .iter_mut()
                .chain(&mut node.v)
                .chain(&mut node.memory.packet)
                .chain(std::iter::once(&mut node.memory.previous))
            {
                *x = r.float()?;
            }
            node.memory.age = r.usize()?;
            for x in node
                .memory
                .z
                .iter_mut()
                .chain(std::iter::once(&mut node.loss))
            {
                *x = r.float()?;
            }
            node.committed = r.word()? != 0;
            c.latch = r.word()? != 0;
            c.last = r.usize()?;
            c.events = r.usize()?;
            c.attempts = r.usize()?;
            c.work.sum = r.float()?;
            c.work.correction = r.float()?;
            c.budget = r.usize()?;
            c.vetoes = r.usize()?;
            if node.memory.age != tick
                || c.events > 3
                || c.budget > 3
                || node.memory.z.iter().any(|x| x.abs() > 1. + 1e-14)
            {
                return Err(io::Error::other("QR12 controller state"));
            }
        }
        for s in [&mut w.work, &mut w.positive, &mut w.negative, &mut w.switch] {
            s.sum = r.float()?;
            s.correction = r.float()?;
        }
        for p in &mut w.ports {
            if r.float()?.to_bits() != p.norm.to_bits() {
                return Err(io::Error::other("QR12 port ABI"));
            }
            p.net = r.float()?;
            p.positive = r.float()?;
            p.negative = r.float()?;
            p.neural = r.float()?;
            p.cancellation = r.float()?;
        }
        if r.i != b.len() - 8 {
            return Err(io::Error::other("QR12 trailing bytes"));
        }
        Ok(w)
    }
}
struct Reader<'a> {
    b: &'a [u8],
    i: usize,
}
impl Reader<'_> {
    fn byte(&mut self) -> io::Result<u8> {
        let x = *self
            .b
            .get(self.i)
            .ok_or_else(|| io::Error::other("QR12 short input"))?;
        self.i += 1;
        Ok(x)
    }
    fn word(&mut self) -> io::Result<u64> {
        let end = self.i + 8;
        let a = self
            .b
            .get(self.i..end)
            .ok_or_else(|| io::Error::other("QR12 short input"))?;
        self.i = end;
        Ok(u64::from_le_bytes(a.try_into().unwrap()))
    }
    fn usize(&mut self) -> io::Result<usize> {
        usize::try_from(self.word()?).map_err(io::Error::other)
    }
    fn float(&mut self) -> io::Result<f64> {
        let x = f64::from_bits(self.word()?);
        if !x.is_finite() {
            return Err(io::Error::other("QR12 nonfinite checkpoint"));
        }
        Ok(x)
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exact_complete_checkpoint_replay_and_corruption() {
        let mut a = World::new(991, 12, 0.05, 0, false, 15).unwrap();
        for _ in 0..24 {
            a.advance(&[(0, 9, 0.5)], Mode::On).unwrap();
            a.events("FIXED").unwrap();
        }
        let path = std::env::temp_dir().join(format!("qr12-full-{}.bin", std::process::id()));
        let bytes = a.snapshot();
        fs::write(&path, &bytes).unwrap();
        let mut b = World::load(&path).unwrap();
        assert_eq!(bytes, b.snapshot());
        for _ in 0..8 {
            a.advance(&[(0, 9, 0.2)], Mode::On).unwrap();
            b.advance(&[(0, 9, 0.2)], Mode::On).unwrap();
        }
        assert_eq!(a.snapshot(), b.snapshot());
        let mut bad = bytes;
        bad[100] ^= 1;
        fs::write(&path, bad).unwrap();
        assert!(World::load(&path).is_err());
        fs::remove_file(path).unwrap();
    }
    #[test]
    fn repeated_local_events_have_no_minimum_and_permit_is_one_node_only() {
        let mut w = World::new(991, 12, 0.05, 0, false, 15).unwrap();
        for n in &mut w.neurons {
            n.memory.age = 320;
            for x in &mut n.memory.z[277..341] {
                *x = 0.5;
            }
            n.u[0] = 0.2;
        }
        w.fluid.tick = 320;
        let before = w.neurons.iter().map(|n| n.palette).collect::<Vec<_>>();
        let e = w.events("PERMIT").unwrap();
        assert!(e[0].accepted);
        assert!(e[1..].iter().all(|e| !e.accepted));
        for (i, p) in before.iter().enumerate().skip(1) {
            assert_eq!(*p, w.neurons[i].palette);
        }
        assert_eq!(w.neurons[0].u[0], 0.2);
        w.fluid.tick = 480;
        for n in &mut w.neurons {
            n.memory.age = 480;
        }
        let e = w.events("ADAPTIVE").unwrap();
        assert!(e[0].accepted);
        assert_eq!(w.controllers[0].events, 2);
        let mut quiet = World::new(991, 12, 0.05, 0, false, 15).unwrap();
        quiet.fluid.tick = 320;
        for n in &mut quiet.neurons {
            n.memory.age = 320;
        }
        assert!(
            quiet
                .events("ADAPTIVE")
                .unwrap()
                .iter()
                .all(|e| !e.accepted)
        );
    }
    #[test]
    fn passive_trace_modes_and_original_neuron_physics_agree() {
        let mut a = World::new(991, 12, 0.05, 2, false, 3).unwrap();
        let mut original =
            crate::listening_0011::World::new(991, 12, 0.05, 4, false, true).unwrap();
        let mut off = a.clone();
        for _ in 0..40 {
            a.advance(&[(0, 9, 0.7)], Mode::On).unwrap();
            original.advance(&[(0, 9, 0.7)], Mode::On).unwrap();
            off.advance(&[(0, 9, 0.7)], Mode::SensorOff).unwrap();
        }
        assert_eq!(a.fluid.q, original.fluid.q);
        assert_eq!(a.fluid.w, original.fluid.w);
        assert_eq!(a.fluid.q, off.fluid.q);
        for ((n, o), s) in a.neurons.iter().zip(&original.neurons).zip(&off.neurons) {
            assert_eq!(n.u, o.u);
            assert_eq!(n.v, o.v);
            assert_eq!(n.memory.z, o.memory.z);
            assert_eq!(n.v, s.v);
        }
    }
}
