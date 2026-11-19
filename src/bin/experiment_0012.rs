//! Execute a preregistered QR12 stage.
use qr_neural_memory_system::experiment_0012;
use std::{io, path::Path};
fn main() -> io::Result<()> {
    let a = std::env::args().collect::<Vec<_>>();
    if a.len() == 3 && a[1] == "matrix" {
        experiment_0012::matrix(Path::new(&a[2]))
    } else {
        Err(io::Error::other("usage: experiment_0012 matrix ROOT"))
    }
}
