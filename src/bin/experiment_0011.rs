//! Preregistered QR11 execution entry points.
use qr_neural_memory_system::experiment_0011;
use std::{io, path::Path};
fn main() -> io::Result<()> {
    let a: Vec<_> = std::env::args().collect();
    match a.get(1).map(String::as_str) {
        Some("matrix") if a.len() == 3 => experiment_0011::matrix(Path::new(&a[2])),
        Some("commit") if a.len() == 6 => experiment_0011::commit(
            Path::new(&a[2]),
            Path::new(&a[3]),
            a[4] == "1",
            Path::new(&a[5]),
        ),
        _ => Err(io::Error::other(
            "usage: experiment_0011 matrix ROOT | commit INPUT OUTPUT ENABLED FLUID",
        )),
    }
}
