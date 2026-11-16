# QR9 standalone acoustic observation schema

`QR9AC001` is independent of QR6/QR7/QR8 and their source-assuming viewer adapters.
All integers are unsigned little-endian64, floating values IEEE754 f64 little
endian. Header length72 bytes: magic8, schema1, cells-per-axisN, tick, dt(f64),
fixture kind0=mode/1=Gaussian/2=zero, integer mode_x,mode_y,mode_z.
Then four contiguous arrays of N³ f64: normalized pressure q, positive-x face w,
positive-y face w, positive-z face w. x-fast indexing i=x+N*(y+N*z).
Finally FNV1a64 of all preceding bytes. Exact total length80+32*N³.
Outer positive face slots are real stored zeros; negative faces implicit zero.
All arrays are co-timed at tick*dt. Complete fields, not a visual amplitude.

Coordinates: pressure centre((x+.5)h,(y+.5)h,(z+.5)h); x-face((x+1)h,
(y+.5)h,(z+.5)h), and cyclic permutations. h=24/N metres. Reference.csv records
rho,c,K,mu. Physical time=t/c seconds; p=q*sqrt(K*E*/1m³),
fluid velocity=w*sqrt(E*/(rho*1m³)), E*=1kg*(1e-6m)²*c²/(1m)².
mu is a reported reference property; material absorption is disabled.

`metrics.csv` has every tick/time, actual acoustic energy, maxima, pressure and
velocity modal projections (0 for nonmodal fixtures). Actual energy includes each
stored face velocity ONCE. Cell display/probe energy instead shares each face
kinetic energy equally between adjacent cells; its integral equals full energy.
Probe.csv contains every-tick21 fixed axis/offset entries, pressure from nearest
cell (lowest-index tie), velocity arithmetic mean of adjacent normal faces, and
cell energy density. Signed q/w are not intensity. Physical pressure in Pa,
velocity m/s, density J/m³ are recovered with the frozen scales.

`plan.csv` freezes17 intended cases; `events.csv` STARTED/COMPLETE records make an
uncompleted folder visible. `ledger.csv` records completed physical executions,
grid, row count and actual wall seconds. An existing output root/case is rejected.
Raw case COMPLETE is a recording marker, never a PASS verdict. Python independently
checks actual fields and outputs gates.csv, modal_errors.csv, case_summary.csv
and verification.json. Failures remain rows with measured value/unchanged limit.
Checkpoints only0,6,12,24; no interpolation of missing fields.

This schema has no neural states. Coupled-stage records are conditional on S1 and
S2 and must use their own documented schema before that execution. No coupled
capability is implied by the standalone interface or proposed registration.
