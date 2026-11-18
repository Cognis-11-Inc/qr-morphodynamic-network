//! Frozen QR10 stationary pilot entry point.
use std::{io, path::Path};
fn main() -> io::Result<()> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 3 {
        return Err(io::Error::other(
            "usage: coupling_0010 NEW_ROOT NUMERICAL_ROOT",
        ));
    }
    qr_neural_memory_system::coupling_0010::pilot(Path::new(&args[1]), Path::new(&args[2]))
}
