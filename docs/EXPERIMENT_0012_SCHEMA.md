# QR12 schema1 and execution boundary clarifications

Defined before scientific execution. All binary integers are little-endian u64,
all floats IEEE754 little-endian f64, checksums unchanged FNV1a64. Units and equations
are registered in EXPERIMENT_0012.md. Paths preserve project-relative results roots.
No physics or acceptance criterion is amended here.

QR12FUL1 complete-state header: magic8, then version,n,tick,dt bits,seed,node count,
geometry,scalar flag,coupled-node mask (9 words,80 total bytes). Then node positions
3f64 each; fluid q,wx,wy,wz each n³ f64 (x fastest); owned node records4480bytes each;
world compensated accounts8f64 in order force sum/correction,positive sum/correction,
negative sum/correction,switch sum/correction; per-node ports9,27 each6f64:
norm,net fluid work,positive fluid work,backflow,net neural work,cancellation.
Trailing FNV8. Total152+4600*count+32*n³. Derived intrinsic coefficients and kernels
are rebuilt deterministically from palette/positions; restored port norms must
match exact bits. No hidden scratch fluid state exists in Fluid.

Each node record starts with original QR11 record4416bytes (palette64u8,u64f64,
v64f64,packet7f64,previous f64,age u64,405f64 traces,loss f64,legacy committed u64).
QR12 never uses the old one-shot flag to limit its law. Follow with8words:
latch,last successful tick,event count,opportunity count,event-work sum and
correction f64,swap budget used,veto count. All persistent/transient event state
is owned by its own node/controller. Max3successful events is explicit.

QR12OBS1 stream header80bytes: magic,version,count,n,dt bits,start tick,end tick,
seed,geometry,scalar flag. Each frame: ticku64,all owned nodes4480bytes,trailingFNV.
No automatic tick skipping. Raw observations cover every physical step, including
initial post-intervention branch state; branch-before checkpoint separately
preserves EXACT shared ancestor bytes. Controller latches update after sensing;
all later branch opportunities are vetoed, rather than erasing local history.

Plan CSV11fields: case,seed,n,dt,geometry,policy,forcing,horizon,mask,scalar,checkpoint.
Geometry0 SQ,1 ALT,2 original two-node fixture,10..13 actual single original node
in private fluid,20 pair01,21 pair23. Source0 means first LOCAL member of a case;
in the deliberately separate E pair23 validation, original N2 is the externally
forced local member. This validates an active pair rather than an unforced zero
solution. The four-neuron predictive comparison still forces only original N0.

Original QR11 oracle cases execute the UNCHANGED Original World arithmetic with
the same prescribed MID12 forcing supplied by the new external apparatus. Their
fields/owned observations retain QR11AC01/QR11NEU1/QR11OBS1. They are observations
of the original model, not resumable QR12 checkpoints or synthetic replacements.
All other trajectories use QR12 complete state; branches never use the oracle.

Full snapshots at initial/final/halfway, plus opportunities16,24,32 and PRE-event
checkpoints. This adds fixed halfway time20 to B/D; C halfway is20. Fluid and
local observer state refer to the same physical time. Extra deterministic
checkpoints do not change registered common-time acceptance comparisons.

Every event opportunity writes trigger/latch,candidate pair,accepted/veto,cause,
work and edited-position count. scores.csv preserves every module's old/new
palette,H8,score. Kicks log both half kicks plus explicit half2 perturbation;
exchange.csv logs every actual reciprocal rotation. metrics.csv contains fluid,
neural,loss,force work,switch/sham work,all-positive/all-negative work,port-net,
cancellation,energies N0..N3. Missing members in smaller controls have reported
energy0, not invented extra neurons. Metadata and initial NOT RUN plan remain
separate from actual execution-events and completed-trajectory ledger.
