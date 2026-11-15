//! Experiment 0008: frozen excitation and passive mechanical-energy observations.
use crate::{
    lattice::Configuration,
    morphic_0006::{FIELDS, Frame, Medium},
    observation::checksum,
    topology::{POPULATION, Topology},
};
use std::{collections::BTreeSet, io};
/// Fixed nonzero measurement times.
pub const TIMES: [f64; 5] = [0.8, 3.2, 8., 16., 32.];
/// Registered external graph distances.
pub const DISTANCES: [usize; 5] = [1, 2, 3, 4, 6];
/// Every-tick probe modules, including two unstimulated channels.
pub const MODULES: [usize; 4] = [9, 27, 10, 18];
/// Scalars per region and tick.
pub const REGION_VALUES: usize = 12;
fn num(n: usize) -> f64 {
    f64::from(u32::try_from(n).expect("bounded lattice count"))
}
fn internal(m: usize) -> Vec<usize> {
    (0..64)
        .filter(|&q| (m / 8).abs_diff(q / 8) + (m % 8).abs_diff(q % 8) == 1)
        .collect()
}
/// The complete fixed input alphabet, including independent B and zero controls.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum Signal {
    /// Positive single at A/module9.
    S9p = 0,
    /// Positive single at A/module27.
    S27p = 1,
    /// Negative single at A/module9.
    S9m = 2,
    /// Negative single at A/module27.
    S27m = 3,
    /// Equal-sign dual at module27.
    ABp = 4,
    /// Opposite-sign dual at module27.
    ABm = 5,
    /// Exact zero-input control.
    Zero = 6,
    /// Positive independent B/module27 basis.
    B27p = 7,
}
impl Signal {
    /// Registered execution order.
    pub const ALL: [Self; 8] = [
        Self::S9p,
        Self::S27p,
        Self::S9m,
        Self::S27m,
        Self::ABp,
        Self::ABm,
        Self::Zero,
        Self::B27p,
    ];
    /// Stable physical signal name.
    #[must_use]
    pub const fn name(self) -> &'static str {
        match self {
            Self::S9p => "S9p",
            Self::S27p => "S27p",
            Self::S9m => "S9m",
            Self::S27m => "S27m",
            Self::ABp => "ABp",
            Self::ABm => "ABm",
            Self::Zero => "ZERO",
            Self::B27p => "B27p",
        }
    }
    /// Directly stimulated module; ZERO uses27 as metadata only.
    #[must_use]
    pub const fn module(self) -> usize {
        if matches!(self, Self::S9p | Self::S9m) {
            9
        } else {
            27
        }
    }
    fn decode(n: u64) -> io::Result<Self> {
        Self::ALL
            .get(usize::try_from(n).map_err(io::Error::other)?)
            .copied()
            .ok_or_else(|| io::Error::other("QR8 signal"))
    }
}
/// Fixed receiver membership and geometry-selected six-sensor subset.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Region {
    /// A-only(false) or minimum-distance-to-both(true).
    pub far: bool,
    /// Exact shell distance.
    pub distance: usize,
    /// Full receiver IDs, excluding both potential sources.
    pub ids: Vec<usize>,
    /// Six selected probe IDs in increasing order.
    pub probes: Vec<usize>,
}
/// Derive registered regions using only the fixed topology.
/// # Panics
/// Panics if a future incompatible topology provides fewer than six receivers.
#[must_use]
pub fn regions() -> Vec<Region> {
    let graph = Topology::Cubic6;
    let mut out = Vec::new();
    for far in [false, true] {
        for distance in DISTANCES {
            let ids: Vec<_> = (0..POPULATION)
                .filter(|&i| {
                    ![2182, 2186].contains(&i)
                        && (if far {
                            graph.hops(i, 2182).min(graph.hops(i, 2186))
                        } else {
                            graph.hops(i, 2182)
                        }) == distance
                })
                .collect();
            let mut selected = vec![ids[0]];
            while selected.len() < 6 {
                let next = ids
                    .iter()
                    .copied()
                    .filter(|i| !selected.contains(i))
                    .max_by_key(|&i| {
                        (
                            selected
                                .iter()
                                .map(|&j| graph.hops(i, j))
                                .min()
                                .unwrap_or(0),
                            std::cmp::Reverse(i),
                        )
                    })
                    .expect("at least six receivers");
                selected.push(next);
            }
            selected.sort_unstable();
            out.push(Region {
                far,
                distance,
                ids,
                probes: selected,
            });
        }
    }
    out
}
/// Every-tick probe union; no activity-dependent selection.
#[must_use]
pub fn probes(regions: &[Region]) -> Vec<usize> {
    let mut ids: BTreeSet<_> = [0, 4095, 2182, 2186, 2184].into_iter().collect();
    for r in regions {
        ids.extend(r.probes.iter().copied());
    }
    ids.into_iter().collect()
}
struct Edge {
    i: usize,
    j: usize,
    k: f64,
}
/// Passive full-module partition, entirely separate from state advancement.
pub struct Observer {
    omega2: Vec<f64>,
    edges: Vec<Edge>,
    /// Per-module kinetic energy.
    pub kinetic: Vec<f64>,
    /// Per-module onsite plus half-edge potential.
    pub potential: Vec<f64>,
    /// Per-module kinetic plus onsite, excluding edge allocation.
    pub motion: Vec<f64>,
    /// Per-neuron total mechanical partition.
    pub neuron: Vec<f64>,
    /// Per-neuron actual motion energy.
    pub neuron_motion: Vec<f64>,
    /// Per-neuron energy outside injected module.
    pub other: Vec<f64>,
    /// Per-neuron motion outside injected module.
    pub other_motion: Vec<f64>,
    /// Per-neuron energy outside9/27.
    pub cross: Vec<f64>,
    /// Per-neuron motion outside9/27.
    pub cross_motion: Vec<f64>,
    /// Global kinetic, onsite and coupling energy.
    pub components: [f64; 3],
    /// Full-field displacement/velocity absolute maxima.
    pub peaks: [f64; 2],
}
impl Observer {
    /// Build observation coefficients from the fixed actual palette.
    #[must_use]
    pub fn new(palette: &[[u8; 64]]) -> Self {
        let mut omega2 = vec![0.; FIELDS];
        let mut conductance = vec![0.; FIELDS];
        let mut edges = Vec::new();
        for (id, p) in palette.iter().enumerate() {
            for m in 0..64 {
                let occupied = internal(m).iter().filter(|&&q| p[q] != 0).count();
                let omega = 0.8
                    + 0.08 * f64::from(p[m])
                    + 0.04 * num(occupied)
                    + if p[m] == 1 { 0.12 } else { 0. };
                omega2[id * 64 + m] = omega * omega;
                conductance[id * 64 + m] = match p[m] {
                    0 => 0.5,
                    1 => 1.,
                    _ => 0.75,
                };
            }
        }
        for id in 0..POPULATION {
            for m in 0..64 {
                let i = id * 64 + m;
                for n in internal(m) {
                    if m < n {
                        let j = id * 64 + n;
                        edges.push(Edge {
                            i,
                            j,
                            k: 0.15 * conductance[i] * conductance[j],
                        });
                    }
                }
                for n in Topology::Cubic6.neighbors(id) {
                    if id < n {
                        let j = n * 64 + m;
                        edges.push(Edge {
                            i,
                            j,
                            k: (0.4 / 6.) * conductance[i] * conductance[j],
                        });
                    }
                }
            }
        }
        Self {
            omega2,
            edges,
            kinetic: vec![0.; FIELDS],
            potential: vec![0.; FIELDS],
            motion: vec![0.; FIELDS],
            neuron: vec![0.; POPULATION],
            neuron_motion: vec![0.; POPULATION],
            other: vec![0.; POPULATION],
            other_motion: vec![0.; POPULATION],
            cross: vec![0.; POPULATION],
            cross_motion: vec![0.; POPULATION],
            components: [0.; 3],
            peaks: [0.; 2],
        }
    }
    /// Reconstruct actual quadratic energy without modifying the medium.
    pub fn observe(&mut self, frame: &Frame) {
        self.components = [0.; 3];
        self.peaks = [0.; 2];
        for i in 0..FIELDS {
            let k = 0.5 * frame.v[i] * frame.v[i];
            let q = 0.5 * self.omega2[i] * frame.u[i] * frame.u[i];
            self.kinetic[i] = k;
            self.potential[i] = q;
            self.motion[i] = k + q;
            self.components[0] += k;
            self.components[1] += q;
            self.peaks[0] = self.peaks[0].max(frame.u[i].abs());
            self.peaks[1] = self.peaks[1].max(frame.v[i].abs());
        }
        for edge in &self.edges {
            let delta = frame.u[edge.j] - frame.u[edge.i];
            let energy = 0.5 * edge.k * delta * delta;
            self.components[2] += energy;
            self.potential[edge.i] += 0.5 * energy;
            self.potential[edge.j] += 0.5 * energy;
        }
        for a in [
            &mut self.neuron,
            &mut self.neuron_motion,
            &mut self.other,
            &mut self.other_motion,
            &mut self.cross,
            &mut self.cross_motion,
        ] {
            a.fill(0.);
        }
        for id in 0..POPULATION {
            for m in 0..64 {
                let i = id * 64 + m;
                let e = self.kinetic[i] + self.potential[i];
                self.neuron[id] += e;
                self.neuron_motion[id] += self.motion[i];
                if m != frame.module {
                    self.other[id] += e;
                    self.other_motion[id] += self.motion[i];
                }
                if ![9, 27].contains(&m) {
                    self.cross[id] += e;
                    self.cross_motion[id] += self.motion[i];
                }
            }
        }
    }
    /// Total mechanical energy, including coupling once per edge.
    #[must_use]
    pub fn total(&self) -> f64 {
        self.components.iter().sum()
    }
    /// Global participation, non-source active count and cross-channel energies.
    #[must_use]
    pub fn global(&self) -> [f64; 6] {
        let total = self.total();
        let squares = self.neuron.iter().map(|e| e * e).sum::<f64>();
        [
            if squares > 0. {
                total * total / squares
            } else {
                0.
            },
            num((0..POPULATION)
                .filter(|&i| ![2182, 2186].contains(&i) && self.neuron_motion[i] >= 1e-8)
                .count()),
            self.other.iter().sum(),
            self.other_motion.iter().sum(),
            self.cross.iter().sum(),
            self.cross_motion.iter().sum(),
        ]
    }
    /// Twelve registered region measurements in documented stream order.
    #[must_use]
    pub fn region(&self, r: &Region) -> [f64; REGION_VALUES] {
        let sum = |a: &[f64]| r.ids.iter().map(|&i| a[i]).sum::<f64>();
        let e = sum(&self.neuron);
        let mean = e / num(r.ids.len());
        let variance = r
            .ids
            .iter()
            .map(|&i| (self.neuron[i] - mean).powi(2))
            .sum::<f64>()
            / num(r.ids.len());
        let full = e + if !r.far && r.distance == 4 {
            self.neuron[2186]
        } else {
            0.
        };
        [
            full,
            e,
            if self.total() > 0. {
                e / self.total()
            } else {
                0.
            },
            sum(&self.neuron_motion),
            sum(&self.other),
            sum(&self.other_motion),
            sum(&self.cross),
            sum(&self.cross_motion),
            r.ids
                .iter()
                .map(|&i| self.neuron[i])
                .fold(f64::INFINITY, f64::min),
            r.ids.iter().map(|&i| self.neuron[i]).fold(0., f64::max),
            mean,
            variance.sqrt(),
        ]
    }
}
/// Frozen primary body; contains no adaptation or mutable-palette operation.
pub struct Frozen {
    body: Medium,
    observer: Observer,
    signal: Signal,
    amplitudes: [f64; 2],
    unit_energy: f64,
}
impl Frozen {
    /// Initialize one registered input from the unchanged heterogeneous generator.
    /// # Errors
    /// Rejects grids, invalid initialization or mismatched energy.
    pub fn new(seed: u64, dt: f64, signal: Signal) -> io::Result<Self> {
        if ![0.025, 0.0125].contains(&dt) {
            return Err(io::Error::other("QR8 grid"));
        }
        let arm = match signal {
            Signal::ABp => "AB+",
            Signal::ABm => "AB-",
            Signal::Zero => "zero",
            Signal::B27p => "B",
            _ => "A",
        };
        let mut body = Medium::new(
            seed,
            Configuration::Heterogeneous,
            dt,
            arm,
            signal.module(),
            &format!("s{seed}_{}", signal.name()),
        )?;
        if matches!(signal, Signal::S9m | Signal::S27m) {
            body.state.u[2182 * 64 + signal.module()] = -1.;
        }
        let unit_energy = body.energy().total();
        if signal != Signal::Zero {
            body.match_energy(1.)?;
            if (body.energy().total() - 1.).abs() > 1e-12 {
                return Err(io::Error::other("QR8 energy match"));
            }
        }
        let amplitudes = [
            body.state.u[2182 * 64 + signal.module()],
            body.state.u[2186 * 64 + signal.module()],
        ];
        let mut observer = Observer::new(&body.state.palette);
        observer.observe(&body.state);
        if (observer.total() - body.energy().total()).abs() > 1e-12 {
            return Err(io::Error::other("QR8 energy instrumentation"));
        }
        Ok(Self {
            body,
            observer,
            signal,
            amplitudes,
            unit_energy,
        })
    }
    /// Immutable authoritative physical body.
    #[must_use]
    pub const fn body(&self) -> &Medium {
        &self.body
    }
    /// Immutable passive observations.
    #[must_use]
    pub const fn observer(&self) -> &Observer {
        &self.observer
    }
    /// Energy of the actual unscaled initial pattern.
    #[must_use]
    pub const fn unit_energy(&self) -> f64 {
        self.unit_energy
    }
    /// Signed initial amplitudes at A and B.
    #[must_use]
    pub const fn amplitudes(&self) -> [f64; 2] {
        self.amplitudes
    }
    /// Advance exactly the original frozen integrator, with no histories or drive.
    /// # Errors
    /// Rejects completed windows or numerical violations.
    pub fn advance(&mut self) -> io::Result<()> {
        if f64::from(u32::try_from(self.body.state.tick).map_err(io::Error::other)?)
            * self.body.state.dt
            >= 32. - 1e-10
        {
            return Err(io::Error::other("QR8 window exhausted"));
        }
        self.body.advance(0., false)?;
        self.observer.observe(&self.body.state);
        Ok(())
    }
    /// Capture signed fields and actual module energy partitions together.
    #[must_use]
    pub fn record(&self) -> Record {
        Record {
            frame: self.body.state.clone(),
            signal: self.signal,
            amplitudes: self.amplitudes,
            kinetic: self.observer.kinetic.clone(),
            potential: self.observer.potential.clone(),
        }
    }
}
/// QR8 schema1 field record; its body carries the complete physical condition ID.
#[derive(Clone, Debug, PartialEq)]
pub struct Record {
    /// Exact signed state and actual P.
    pub frame: Frame,
    /// Input pattern.
    pub signal: Signal,
    /// Signed initial A/B amplitudes.
    pub amplitudes: [f64; 2],
    /// Actual full kinetic partition.
    pub kinetic: Vec<f64>,
    /// Actual full onsite/half-edge partition.
    pub potential: Vec<f64>,
}
impl Record {
    fn valid(&self) -> bool {
        self.frame.configuration == Configuration::Heterogeneous
            && self.frame.tick
                <= u64::from(if self.frame.dt.to_bits() == 0.025_f64.to_bits() {
                    1280_u32
                } else {
                    2560_u32
                })
            && [0.025, 0.0125].contains(&self.frame.dt)
            && self.frame.tick <= 2560
            && self.frame.module == self.signal.module()
            && self.frame.label == format!("s{}_{}", self.frame.seed, self.signal.name())
            && self.amplitudes.iter().all(|a| a.is_finite())
            && self.kinetic.len() == FIELDS
            && self.potential.len() == FIELDS
            && self
                .kinetic
                .iter()
                .chain(&self.potential)
                .all(|e| e.is_finite() && *e >= 0.)
    }
    /// Encode the nested signed body, explicit ports and full energy fields.
    /// # Errors
    /// Rejects invalid fields or metadata.
    pub fn encode(&self) -> io::Result<Vec<u8>> {
        if !self.valid() {
            return Err(io::Error::other("invalid QR8 record"));
        }
        let body = self.frame.encode()?;
        let mut b = b"QR8FLD01".to_vec();
        for x in [
            1,
            self.signal as u64,
            2182,
            2186,
            self.amplitudes[0].to_bits(),
            self.amplitudes[1].to_bits(),
            u64::try_from(body.len()).map_err(io::Error::other)?,
            u64::try_from(FIELDS).map_err(io::Error::other)?,
        ] {
            b.extend_from_slice(&x.to_le_bytes());
        }
        b.extend_from_slice(&body);
        for a in [&self.kinetic, &self.potential] {
            for x in a {
                b.extend_from_slice(&x.to_le_bytes());
            }
        }
        b.extend_from_slice(&checksum(&b).to_le_bytes());
        Ok(b)
    }
    /// Decode exact metadata/dimensions, fields and both checksums.
    /// # Errors
    /// Rejects corruption, inconsistent grids or unsupported schema.
    pub fn decode(b: &[u8]) -> io::Result<Self> {
        let bad = || io::Error::other("QR8 schema/field/checksum");
        if b.len() < 72 || &b[..8] != b"QR8FLD01" {
            return Err(bad());
        }
        let n = |i| u64::from_le_bytes(b[i..i + 8].try_into().unwrap_or([0; 8]));
        let length = usize::try_from(n(56)).map_err(io::Error::other)?;
        if n(8) != 1
            || n(24) != 2182
            || n(32) != 2186
            || n(64) != u64::try_from(FIELDS).map_err(io::Error::other)?
            || length > 5_000_000
            || b.len() != 72 + length + 16 * FIELDS + 8
            || checksum(&b[..b.len() - 8]) != n(b.len() - 8)
        {
            return Err(bad());
        }
        let start = 72 + length;
        let out = Self {
            frame: Frame::decode(&b[72..start])?,
            signal: Signal::decode(n(16))?,
            amplitudes: [f64::from_bits(n(40)), f64::from_bits(n(48))],
            kinetic: (0..FIELDS)
                .map(|i| f64::from_bits(n(start + 8 * i)))
                .collect(),
            potential: (0..FIELDS)
                .map(|i| f64::from_bits(n(start + 8 * FIELDS + 8 * i)))
                .collect(),
        };
        if !out.valid() {
            return Err(bad());
        }
        Ok(out)
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn geometry_and_half_edge_quadratic_meaning() {
        let r = regions();
        assert_eq!(
            r.iter().map(|r| r.ids.len()).collect::<Vec<_>>(),
            [6, 18, 38, 65, 146, 12, 35, 70, 114, 225]
        );
        assert_eq!(r[1].probes, [1670, 2150, 2180, 2184, 2214, 2694]);
        assert_eq!(probes(&r).len(), 50);
        for region in &r {
            assert_eq!(region.probes.len(), 6);
            assert!(region.probes.iter().all(|i| region.ids.contains(i)));
            assert!(!region.ids.contains(&2186));
        }
        let p = vec![[0; 64]; POPULATION];
        let mut o = Observer::new(&p);
        let mut body = Medium::new(
            202_608,
            Configuration::Heterogeneous,
            0.025,
            "zero",
            9,
            "analytic",
        )
        .unwrap();
        body.state.palette.clone_from(&p);
        body.state.u[9] = 1.;
        body.state.u[10] = -1.;
        o.observe(&body.state);
        let k = 0.15 * 0.5 * 0.5;
        assert!((0.5 * k * (body.state.u[9] - body.state.u[10]).powi(2) - 0.075).abs() < 1e-15);
        assert!(o.potential[8] > 0. && o.motion[8] == 0.);
        assert!(o.total() > 0.);
    }
    #[test]
    fn frozen_sign_ports_partition_and_codec() {
        let mut plus = Frozen::new(202_608, 0.025, Signal::S9p).unwrap();
        let mut minus = Frozen::new(202_608, 0.025, Signal::S9m).unwrap();
        let p = plus.body.state.palette.clone();
        for _ in 0..3 {
            plus.advance().unwrap();
            minus.advance().unwrap();
        }
        assert!(
            plus.body
                .state
                .u
                .iter()
                .zip(&minus.body.state.u)
                .all(|(a, b)| (a + b).abs() < 1e-14)
        );
        assert_eq!(plus.observer.potential, minus.observer.potential);
        let e = plus.body.energy();
        assert!((plus.observer.total() - e.total()).abs() < 1e-12);
        assert!(
            plus.observer
                .neuron
                .iter()
                .zip(e.local)
                .all(|(a, b)| (a - b).abs() < 1e-12)
        );
        assert_eq!(p, plus.body.state.palette);
        assert!(
            plus.body
                .history()
                .iter()
                .chain(plus.body.shape_history())
                .all(|x| *x == 0.)
        );
        let rec = plus.record();
        let b = rec.encode().unwrap();
        assert_eq!(Record::decode(&b).unwrap(), rec);
        let mut corrupt = b;
        corrupt[200] ^= 1;
        assert!(Record::decode(&corrupt).is_err());
        let basis = Frozen::new(202_608, 0.025, Signal::B27p).unwrap();
        assert_eq!(basis.body.state.u[2182 * 64 + 27], 0.);
        assert!(basis.body.state.u[2186 * 64 + 27] > 0.);
        assert!(Frozen::new(202_608, 0.05, Signal::Zero).is_err());
    }
}
