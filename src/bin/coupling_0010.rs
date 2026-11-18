//! Frozen QR10 stationary coupling stage entry point.
use std::{io, path::Path};
fn main() -> io::Result<()> {
    let args: Vec<_> = std::env::args().collect();
    match args.len() {
        3 => {
            qr_neural_memory_system::coupling_0010::pilot(Path::new(&args[1]), Path::new(&args[2]))
        }
        4 => qr_neural_memory_system::coupling_0010::extended(
            Path::new(&args[2]),
            Path::new(&args[3]),
            &args[1],
        ),
        _ => Err(io::Error::other(
            "usage: coupling_0010 [train|evaluate|interference] NEW_ROOT PREREQUISITE_ROOT",
        )),
    }
}
