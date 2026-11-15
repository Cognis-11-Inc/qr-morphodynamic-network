//! Experiment 0007: bounded external operations over the unchanged QR6 medium.
use crate::{
    lattice::Configuration,
    morphic_0006::{Frame, Medium, variant},
    observation::checksum,
};
use std::io;

/// Signed numeric readout dimension, with no identity or condition metadata.
pub const DIM: usize = 120;
/// Output sites, ordered nearest to farthest.
pub const OUTPUTS: [usize; 3] = [2184, 2185, 2186];
/// Registered sample times within each independent read pulse.
pub const TIMES: [f64; 5] = [0.8, 3.2, 8., 16., 32.];
/// Externally requested, truthful checkpoint operation.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Operation {
    /// Virgin external reference measurement.
    Calibrate = 0,
    /// Experience exposure before the single commit.
    Write = 1,
    /// Frozen read, independent of the encoded symbol.
    Read = 2,
}
/// A new checkpoint schema with explicit physical injection port.
#[derive(Clone, Debug, PartialEq)]
pub struct Checkpoint {
    /// Complete signed fields and persistent palette.
    pub frame: Frame,
    /// Port actually stimulated.
    pub port: usize,
    /// Operator command that produced these fields.
    pub operation: Operation,
    /// Adaptation rule, zero only for calibration.
    pub rule: u8,
}
impl Checkpoint {
    /// Encode a bounded QR7 checkpoint. The embedded field body is unchanged QR6.
    /// # Errors
    /// Rejects invalid state or port/operation combinations.
    pub fn encode(&self) -> io::Result<Vec<u8>> {
        if !matches!(self.port, 2182 | 2183)
            || self.port
                != if self.operation == Operation::Write {
                    2182
                } else {
                    2183
                }
            || ![0, 2, 3].contains(&self.rule)
        {
            return Err(io::Error::other("invalid QR7 operation"));
        }
        let body = self.frame.encode()?;
        let mut b = b"QR7FLD01".to_vec();
        for n in [
            1,
            self.port as u64,
            self.operation as u64,
            u64::from(self.rule),
        ] {
            b.extend_from_slice(&n.to_le_bytes());
        }
        b.extend_from_slice(&body);
        b.extend_from_slice(&checksum(&b).to_le_bytes());
        Ok(b)
    }
    /// Decode both independent checksums and validate physical metadata.
    /// # Errors
    /// Rejects corrupt, unsupported or inconsistent checkpoints.
    pub fn decode(b: &[u8]) -> io::Result<Self> {
        if b.len() < 112 || &b[..8] != b"QR7FLD01" {
            return Err(io::Error::other("QR7 header"));
        }
        let n = |i| u64::from_le_bytes(b[i..i + 8].try_into().unwrap_or([0; 8]));
        if n(8) != 1 || checksum(&b[..b.len() - 8]) != n(b.len() - 8) {
            return Err(io::Error::other("QR7 checksum/schema"));
        }
        let out = Self {
            frame: Frame::decode(&b[40..b.len() - 8])?,
            port: usize::try_from(n(16)).map_err(io::Error::other)?,
            operation: match n(24) {
                0 => Operation::Calibrate,
                1 => Operation::Write,
                2 => Operation::Read,
                _ => return Err(io::Error::other("QR7 operation")),
            },
            rule: u8::try_from(n(32)).map_err(io::Error::other)?,
        };
        out.encode()?;
        Ok(out)
    }
}
/// Authentic outcome; arbitrary user-supplied answer palettes are not accepted.
pub struct Outcome {
    before: Vec<[u8; 64]>,
    after: Vec<[u8; 64]>,
    seed: u64,
    rule: u8,
}
/// External operator with a private physical body and external virgin backup.
pub struct Operator {
    body: Medium,
    virgin: Vec<[u8; 64]>,
    rule: u8,
    operation: Option<Operation>,
    committed: bool,
    exposed: bool,
}
impl Operator {
    /// Construct an untouched, heterogeneous, CPU deterministic body.
    /// # Errors
    /// Rejects unregistered grid or rule.
    pub fn new(seed: u64, dt: f64, rule: u8) -> io::Result<Self> {
        if ![0.025, 0.0125].contains(&dt) || ![2, 3].contains(&rule) {
            return Err(io::Error::other("QR7 grid/rule"));
        }
        let body = Medium::new(seed, Configuration::Heterogeneous, dt, "zero", 9, "QR7")?;
        let virgin = body.state.palette.clone();
        Ok(Self {
            body,
            virgin,
            rule,
            operation: None,
            committed: false,
            exposed: false,
        })
    }
    /// Inspect physical evidence without mutable access.
    #[must_use]
    pub const fn body(&self) -> &Medium {
        &self.body
    }
    /// Reset transients/history/audits while retaining persistent morphology.
    /// # Errors
    /// Propagates an invalid underlying reset.
    pub fn reset(&mut self) -> io::Result<()> {
        let p = self.body.state.palette.clone();
        self.body.reset_impulse(9, "zero", 0.)?;
        if self.body.state.palette != p || !self.zero() {
            return Err(io::Error::other("QR7 reset invariant"));
        }
        self.operation = None;
        self.committed = false;
        self.exposed = false;
        Ok(())
    }
    /// Exact transient zero, including eligibility history and energy accounts.
    #[must_use]
    pub fn zero(&self) -> bool {
        self.body.state.tick == 0
            && self
                .body
                .state
                .u
                .iter()
                .chain(&self.body.state.v)
                .chain(self.body.history())
                .chain(self.body.shape_history())
                .all(|x| *x == 0.)
            && [
                self.body.loss,
                self.body.boundary_loss,
                self.body.work,
                self.body.switch_work,
            ]
            .iter()
            .all(|x| *x == 0.)
    }
    /// Restore the external virgin backup; this is not intrinsic forgetting.
    /// # Errors
    /// Propagates failed reset or palette installation.
    pub fn restore(&mut self) -> io::Result<()> {
        self.reset()?;
        self.body.apply_palette(self.virgin.clone())?;
        self.reset()
    }
    /// Begin virgin calibration or one fixed read pulse, energy matched to one.
    /// # Errors
    /// Rejects non-reset state, invalid pulse, or calibration of a written body.
    pub fn read(&mut self, module: usize, calibrate: bool) -> io::Result<f64> {
        if !self.zero()
            || self.operation.is_some()
            || (calibrate && self.body.state.palette != self.virgin)
        {
            return Err(io::Error::other(
                "QR7 READ requires reset; CALIBRATE requires virgin",
            ));
        }
        self.begin(
            module,
            2183,
            if calibrate {
                Operation::Calibrate
            } else {
                Operation::Read
            },
            true,
        )
    }
    /// Begin the externally supplied binary write symbol, or zero-exposure control.
    /// # Errors
    /// Requires a virgin reset body and a legal binary symbol.
    pub fn write(&mut self, symbol: usize, quiet: bool) -> io::Result<f64> {
        if symbol > 1
            || !self.zero()
            || self.operation.is_some()
            || self.body.state.palette != self.virgin
        {
            return Err(io::Error::other(
                "QR7 WRITE requires virgin reset and binary symbol",
            ));
        }
        self.exposed = true;
        self.begin([9, 27][symbol], 2182, Operation::Write, !quiet)
    }
    fn begin(
        &mut self,
        module: usize,
        port: usize,
        operation: Operation,
        excite: bool,
    ) -> io::Result<f64> {
        if ![9, 27].contains(&module) {
            return Err(io::Error::other("QR7 pulse module"));
        }
        self.body.state.module = module;
        self.operation = Some(operation);
        if !excite {
            return Ok(0.);
        }
        self.body.state.u[port * 64 + module] = 1.;
        let a = self.body.match_energy(1.)?;
        if (self.body.energy().total() - 1.).abs() > 1e-12 {
            return Err(io::Error::other("QR7 energy match"));
        }
        Ok(a)
    }
    /// Advance the original integrator with no forcing and write-only eligibility.
    /// # Errors
    /// Rejects idle state, duplicate commits, and steps beyond the fixed window.
    pub fn advance(&mut self) -> io::Result<()> {
        let op = self.operation.ok_or_else(|| io::Error::other("QR7 idle"))?;
        let end = if op == Operation::Write { 8. } else { 32. };
        if self.committed
            || f64::from(u32::try_from(self.body.state.tick).map_err(io::Error::other)?)
                * self.body.state.dt
                >= end - 1e-10
        {
            return Err(io::Error::other("QR7 operation window exhausted"));
        }
        self.body.advance(0., op == Operation::Write)
    }
    /// Commit exactly once at time eight, or retain a frozen exposure control.
    /// # Errors
    /// Requires the completed registered write window.
    pub fn commit(&mut self, frozen: bool) -> io::Result<Outcome> {
        if self.operation != Some(Operation::Write)
            || !self.exposed
            || self.committed
            || (f64::from(u32::try_from(self.body.state.tick).map_err(io::Error::other)?)
                * self.body.state.dt
                - 8.)
                .abs()
                > 1e-10
        {
            return Err(io::Error::other("QR7 commit timing/state"));
        }
        let before = self.body.state.palette.clone();
        if !frozen {
            self.body.adapt_rule(self.rule)?;
        }
        self.committed = true;
        Ok(Outcome {
            before,
            after: self.body.state.palette.clone(),
            seed: self.body.state.seed,
            rule: self.rule,
        })
    }
    /// Install only a registered control derived from an authentic write outcome.
    /// # Errors
    /// Requires reset, same virgin body/seed/rule, and a registered control name.
    pub fn control(&mut self, outcome: &Outcome, kind: &str) -> io::Result<()> {
        if !self.zero()
            || self.operation.is_some()
            || outcome.seed != self.body.state.seed
            || outcome.rule != self.rule
            || outcome.before != self.virgin
        {
            return Err(io::Error::other("QR7 control provenance/reset"));
        }
        let mut p = outcome.before.clone();
        match kind {
            "VIRGIN" | "FROZEN" | "NO_WRITE" => (),
            "ALL" => p.clone_from(&outcome.after),
            "WRITE_PORT_ONLY" => p[2182] = outcome.after[2182],
            "READ_PORT_ONLY" => p[2183] = outcome.after[2183],
            "REMOTE_ONLY" => {
                p.clone_from(&outcome.after);
                p[2182] = outcome.before[2182];
                p[2183] = outcome.before[2183];
            }
            "SHUFFLED" => {
                p = variant(
                    &outcome.before,
                    &outcome.after,
                    "SHUFFLE_POSITION",
                    self.rule,
                    self.body.state.seed,
                )?;
            }
            _ => return Err(io::Error::other("QR7 unknown control")),
        }
        self.body.apply_palette(p)?;
        self.reset()
    }
    /// Export full fields in the new operation/port-aware format.
    /// # Errors
    /// Rejects an idle operator.
    pub fn checkpoint(&self) -> io::Result<Checkpoint> {
        let operation = self
            .operation
            .ok_or_else(|| io::Error::other("QR7 idle checkpoint"))?;
        Ok(Checkpoint {
            frame: self.body.state.clone(),
            port: if operation == Operation::Write {
                2182
            } else {
                2183
            },
            operation,
            rule: if operation == Operation::Calibrate {
                0
            } else {
                self.rule
            },
        })
    }
}
/// Pure numeric nearest-mean template decoder; metadata cannot enter its input.
#[derive(Clone, Debug, PartialEq)]
pub struct Decoder {
    /// W0 and W1 training means in registered feature order.
    pub means: [[f64; DIM]; 2],
}
impl Decoder {
    /// Predict zero/one, with ambiguity represented by `None`.
    /// # Errors
    /// Rejects nonfinite input or model components.
    pub fn predict(&self, x: &[f64; DIM]) -> io::Result<(Option<usize>, [f64; 2])> {
        if x.iter()
            .chain(self.means.iter().flatten())
            .any(|v| !v.is_finite())
        {
            return Err(io::Error::other("nonfinite decoder input"));
        }
        let d = self
            .means
            .each_ref()
            .map(|m| x.iter().zip(m).map(|(a, b)| (a - b).powi(2)).sum::<f64>());
        if !d.iter().all(|v| v.is_finite()) {
            return Err(io::Error::other("decoder distance overflow"));
        }
        Ok((
            if (d[0] - d[1]).abs() <= 1e-12 * d[0].max(d[1]).max(1e-30) {
                None
            } else {
                Some(usize::from(d[1] < d[0]))
            },
            d,
        ))
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn numeric_decoder_rejects_nonfinite_and_abstains_on_ties() {
        let decoder = Decoder {
            means: [[0.; DIM], [1.; DIM]],
        };
        assert_eq!(decoder.predict(&[0.; DIM]).unwrap().0, Some(0));
        assert_eq!(decoder.predict(&[0.5; DIM]).unwrap().0, None);
        assert!(decoder.predict(&[f64::NAN; DIM]).is_err());
    }
    #[test]
    fn operator_ports_reset_restore_and_frozen_physics() {
        let mut op = Operator::new(12345, 0.025, 2).unwrap();
        assert!(op.commit(false).is_err());
        op.read(9, true).unwrap();
        assert_eq!(op.body.state.u[2182 * 64 + 9], 0.);
        assert!(op.body.state.u[2183 * 64 + 9] > 0.);
        let encoded = op.checkpoint().unwrap().encode().unwrap();
        assert_eq!(
            Checkpoint::decode(&encoded).unwrap(),
            op.checkpoint().unwrap()
        );
        let mut corrupt = encoded;
        corrupt[200] ^= 1;
        assert!(Checkpoint::decode(&corrupt).is_err());
        let p = op.body.state.palette.clone();
        op.advance().unwrap();
        op.reset().unwrap();
        assert!(op.zero());
        assert_eq!(op.body.state.palette, p);
        op.write(0, false).unwrap();
        let mut original = Medium::new(
            12345,
            Configuration::Heterogeneous,
            0.025,
            "A",
            9,
            "reference",
        )
        .unwrap();
        original.match_energy(1.).unwrap();
        for _ in 0..3 {
            op.advance().unwrap();
            original.advance(0., true).unwrap();
        }
        assert_eq!(op.body.state.u, original.state.u);
        assert_eq!(op.body.history(), original.history());
        assert!(op.commit(false).is_err());
        op.restore().unwrap();
        assert!(op.zero());
        assert_eq!(op.body.state.palette, p);
        assert!(op.write(2, false).is_err());
        assert!(Operator::new(1, 0.05, 2).is_err());
    }
}
