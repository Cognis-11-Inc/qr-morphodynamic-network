//! QR9 stationary conservative acoustic container, independent of neural graphs.
use crate::observation::checksum;
use std::{f64::consts::PI, io};

/// Container side in metres and normalized length units.
pub const SIDE: f64 = 24.;
/// Bounded integer conversion for registered grid dimensions.
/// # Panics
/// Panics if a dimension exceeds the supported 32-bit range.
#[must_use]
pub fn number(n: usize) -> f64 {
    f64::from(u32::try_from(n).expect("bounded QR9 dimension"))
}
/// Reference density, sound speed, adiabatic bulk modulus and dynamic viscosity.
#[must_use]
pub fn reference() -> [f64; 4] {
    let (t, s) = (20_f64, 0.035_f64);
    let rho = 999.922_932_95 + 0.020_341_179_217 * t - 0.006_162_459_159_8 * t.powi(2)
        + 0.000_022_614_664_708 * t.powi(3)
        - 0.000_000_046_570_659_168 * t.powi(4)
        + s * (802.002_408_91 - 2.000_518_348_8 * t + 0.016_771_024_982 * t.powi(2)
            - 0.000_030_600_536_746 * t.powi(3))
        - 0.000_016_132_224_742 * s.powi(2) * t.powi(2);
    let c = 1448.96 + 4.591 * t - 0.053_04 * t.powi(2) + 0.000_237_4 * t.powi(3);
    let mu = (0.000_042_844_324_477
        + 1. / (0.157_003_864_64 * (t + 64.992_620_050).powi(2) - 91.296_496_657))
        * (1.
            + (1.540_913_604 + 0.019_981_117_208 * t - 0.000_095_203_865_864 * t.powi(2)) * s
            + (7.973_931_822_3 - 0.075_614_568_881 * t + 0.000_472_370_110_74 * t.powi(2))
                * s.powi(2));
    [rho, c, rho * c * c, mu]
}
/// Analytic standing-wave, Gaussian or exact-zero validation fixture.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Fixture {
    /// Neumann standing wave with integer mode indices.
    Mode([usize; 3]),
    /// Unit-energy isotropic pressure Gaussian.
    Gaussian,
    /// No excitation.
    Zero,
}
impl Fixture {
    /// Stable name, independent of numerical grid.
    #[must_use]
    pub fn name(self) -> String {
        match self {
            Self::Mode(m) => format!("mode{}-{}-{}", m[0], m[1], m[2]),
            Self::Gaussian => "gaussian".into(),
            Self::Zero => "zero".into(),
        }
    }
}
/// Co-timed full pressure and positive-face velocity state in normalized units.
#[derive(Clone)]
pub struct Fluid {
    /// Cells per axis.
    pub n: usize,
    /// Spatial step, metres.
    pub h: f64,
    /// Time step in units of one metre divided by reference sound speed.
    pub dt: f64,
    /// Completed integration steps.
    pub tick: usize,
    /// Cell-centred normalized pressure, x fastest.
    pub q: Vec<f64>,
    /// Positive-face normalized velocities; outer slots identically zero.
    pub w: [Vec<f64>; 3],
}
impl Fluid {
    /// Construct an initially stationary, lossless closed container.
    /// # Errors
    /// Rejects unresolved dimensions or unsafe sufficient CFL.
    pub fn new(n: usize, dt: f64) -> io::Result<Self> {
        if !(4..=128).contains(&n) || !dt.is_finite() || dt <= 0. {
            return Err(io::Error::other("QR9 dimensions/time step"));
        }
        let h = SIDE / number(n);
        if dt * 3_f64.sqrt() * (7. / 6.) / h > 1. {
            return Err(io::Error::other("QR9 acoustic CFL"));
        }
        Ok(Self {
            n,
            h,
            dt,
            tick: 0,
            q: vec![0.; n.pow(3)],
            w: std::array::from_fn(|_| vec![0.; n.pow(3)]),
        })
    }
    /// Cell-centre coordinates in physical metres.
    #[must_use]
    pub fn position(&self, i: usize) -> [f64; 3] {
        [i % self.n, (i / self.n) % self.n, i / self.n.pow(2)].map(|x| (number(x) + 0.5) * self.h)
    }
    /// Cosine pressure and signed vector velocity spatial mode shapes.
    /// # Panics
    /// Panics for a cell index outside this container.
    #[must_use]
    #[allow(clippy::many_single_char_names)] // Conventional analytic mode notation.
    pub fn mode(&self, m: [usize; 3], i: usize) -> (f64, [f64; 3]) {
        let x = self.position(i);
        let k = m.map(|a| number(a) * PI / SIDE);
        let norm = k.iter().map(|a| a * a).sum::<f64>().sqrt();
        let c = std::array::from_fn::<_, 3, _>(|a| (k[a] * x[a]).cos());
        let p = c.iter().product();
        let v = std::array::from_fn(|a| {
            if m[a] == 0 || (i / self.n.pow(u32::try_from(a).unwrap())) % self.n == self.n - 1 {
                0.
            } else {
                k[a] / norm
                    * (k[a] * (x[a] + 0.5 * self.h)).sin()
                    * (0..3).filter(|&b| b != a).map(|b| c[b]).product::<f64>()
            }
        });
        (p, v)
    }
    /// Set one frozen analytic validation initial state.
    pub fn initialize(&mut self, fixture: Fixture) {
        self.tick = 0;
        for v in &mut self.w {
            v.fill(0.);
        }
        for i in 0..self.q.len() {
            self.q[i] = match fixture {
                Fixture::Mode(m) => self.mode(m, i).0,
                Fixture::Gaussian => {
                    let r2 = self
                        .position(i)
                        .map(|x| (x - 12.).powi(2))
                        .iter()
                        .sum::<f64>();
                    (-r2 / (2. * 0.75_f64.powi(2))).exp()
                }
                Fixture::Zero => 0.,
            };
        }
        if fixture == Fixture::Gaussian {
            let scale = self.energy().sqrt().recip();
            for q in &mut self.q {
                *q *= scale;
            }
        }
    }
    /// Exact quadratic energy of the current co-timed discrete state.
    #[must_use]
    pub fn energy(&self) -> f64 {
        0.5 * self.h.powi(3)
            * self
                .q
                .iter()
                .chain(self.w.iter().flatten())
                .map(|x| x * x)
                .sum::<f64>()
    }
    fn pressure(&mut self, dt: f64) {
        let a = dt / self.h;
        for axis in 0..3 {
            let stride = self.n.pow(axis);
            for i in 0..self.q.len() {
                let x = (i / stride) % self.n;
                if x + 1 == self.n {
                    continue;
                }
                let next = i + stride;
                let back = if x == 0 { i } else { i - stride };
                let ahead = if x + 2 == self.n { next } else { next + stride };
                let v = a * self.w[usize::try_from(axis).unwrap()][i];
                self.q[i] -= (9. / 8.) * v;
                self.q[next] += (9. / 8.) * v;
                self.q[ahead] -= v / 24.;
                self.q[back] += v / 24.;
            }
        }
    }
    fn velocity(&mut self, dt: f64) {
        let a = dt / self.h;
        for axis in 0..3 {
            let stride = self.n.pow(axis);
            for i in 0..self.q.len() {
                let x = (i / stride) % self.n;
                if x + 1 == self.n {
                    continue;
                }
                let next = i + stride;
                let back = if x == 0 { i } else { i - stride };
                let ahead = if x + 2 == self.n { next } else { next + stride };
                self.w[usize::try_from(axis).unwrap()][i] -= a
                    * ((9. / 8.) * (self.q[next] - self.q[i])
                        - (self.q[ahead] - self.q[back]) / 24.);
            }
        }
    }
    /// One symmetric pressure/velocity/pressure step; no clipping or damping.
    /// # Errors
    /// Rejects nonfinite values instead of normalizing them.
    pub fn advance(&mut self) -> io::Result<()> {
        self.pressure(self.dt * 0.5);
        self.velocity(self.dt);
        self.pressure(self.dt * 0.5);
        self.tick += 1;
        if !self
            .q
            .iter()
            .chain(self.w.iter().flatten())
            .all(|x| x.is_finite())
        {
            return Err(io::Error::other("QR9 nonfinite state"));
        }
        Ok(())
    }
    /// Sample nearest pressure cell and average adjacent normal faces.
    /// # Panics
    /// Panics for coordinates outside the physical container.
    #[must_use]
    pub fn sample(&self, point: [f64; 3]) -> [f64; 5] {
        assert!(point.iter().all(|&x| (0. ..SIDE).contains(&x)));
        // Selection by enumeration avoids any float-to-index truncation policy.
        let xyz = point.map(|x| {
            (0..self.n)
                .min_by(|&a, &b| {
                    ((number(a) + 0.5) * self.h - x)
                        .abs()
                        .total_cmp(&((number(b) + 0.5) * self.h - x).abs())
                })
                .unwrap()
        });
        let i = xyz[0] + self.n * (xyz[1] + self.n * xyz[2]);
        let velocity: [f64; 3] = std::array::from_fn(|axis| {
            f64::midpoint(
                self.w[axis][i],
                if xyz[axis] == 0 {
                    0.
                } else {
                    self.w[axis][i - self.n.pow(u32::try_from(axis).unwrap())]
                },
            )
        });
        [
            self.q[i],
            velocity[0],
            velocity[1],
            velocity[2],
            self.cell_energy(i),
        ]
    }
    /// Cell energy density with symmetric sharing of incident face kinetic energy.
    /// # Panics
    /// Panics for a cell index outside this container.
    #[must_use]
    pub fn cell_energy(&self, i: usize) -> f64 {
        let mut e = 0.5 * self.q[i].powi(2);
        for axis in 0..3 {
            let stride = self.n.pow(u32::try_from(axis).unwrap());
            e += 0.25 * self.w[axis][i].powi(2);
            if !(i / stride).is_multiple_of(self.n) {
                e += 0.25 * self.w[axis][i - stride].powi(2);
            }
        }
        e
    }
    /// Encode complete fields, not a presentation proxy.
    /// # Errors
    /// Rejects invalid values or unsupported geometry.
    pub fn encode(&self, fixture: Fixture) -> io::Result<Vec<u8>> {
        if !self
            .q
            .iter()
            .chain(self.w.iter().flatten())
            .all(|x| x.is_finite())
        {
            return Err(io::Error::other("QR9 nonfinite checkpoint"));
        }
        let (kind, m) = match fixture {
            Fixture::Mode(m) => (0, m),
            Fixture::Gaussian => (1, [0; 3]),
            Fixture::Zero => (2, [0; 3]),
        };
        let mut b = b"QR9AC001".to_vec();
        for x in [
            1,
            self.n as u64,
            self.tick as u64,
            self.dt.to_bits(),
            kind,
            m[0] as u64,
            m[1] as u64,
            m[2] as u64,
        ] {
            b.extend_from_slice(&x.to_le_bytes());
        }
        for x in self.q.iter().chain(self.w.iter().flatten()) {
            b.extend_from_slice(&x.to_le_bytes());
        }
        b.extend_from_slice(&checksum(&b).to_le_bytes());
        Ok(b)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn cfl_zero_and_reference_properties() {
        assert!(Fluid::new(48, 0.5).is_err());
        let mut f = Fluid::new(4, 0.05).unwrap();
        f.advance().unwrap();
        assert_eq!(f.energy(), 0.);
        let [rho, c, k, mu] = reference();
        assert!((1024. ..1026.).contains(&rho));
        assert!((c - 1521.4632).abs() < 1e-8);
        assert_eq!(k, rho * c * c);
        assert!((0.00107..0.00108).contains(&mu));
    }
    #[test]
    fn derivative_is_negative_divergence_transpose_at_walls() {
        let mut f = Fluid::new(5, 0.05).unwrap();
        for i in 0..f.q.len() {
            f.q[i] = (number(i) * 0.7).sin();
            for axis in 0..3 {
                if (i / f.n.pow(u32::try_from(axis).unwrap())) % f.n != f.n - 1 {
                    f.w[axis][i] = (number(i + axis) * 0.3).cos();
                }
            }
        }
        let old = f.clone();
        f.pressure(1.);
        let a: f64 = f.q.iter().zip(&old.q).map(|(q, p)| p * (q - p)).sum();
        f.q.clone_from(&old.q);
        f.velocity(1.);
        let b: f64 =
            f.w.iter()
                .flatten()
                .zip(old.w.iter().flatten())
                .map(|(v, w)| w * (v - w))
                .sum();
        assert!((a + b).abs() < 1e-12);
    }
}
