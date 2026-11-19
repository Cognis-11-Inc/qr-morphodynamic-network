# QR12 composition: definitions, proof obligations and prediction protocol

This formal investigation is independent of the morphology outcome. Its frozen
criteria are in EXPERIMENT_0012.md. No categorical force is added to the engine.

## Typed states and partial transformations

For each configuration type C, X_C contains finite complete machine states:
shared signed acoustic fields with rigid-wall constraints; independently owned QR
palettes,u/v,packets,traces and local controllers; time/split phase; port mappings;
work/loss accounts including compensation. C fixes spatial indexing,grid,dt,
normalized units,boundary rules,port ABI and ownership. Finite colors,histogram
constraints and bounded controller state are predicates, not consequences of
array shape. A physical step is undefined if it violates its preconditions or
returns nonfinite/illegal state. A branch intervention is a distinct declared
arrow with its own work, not an ordinary unforced evolution step.

Let arrows X_C -> X_D be deterministic partial functions with specified domains.
Composition g after f has domain {x in dom(f): f(x) in dom(g)}. The identity has
all X_C as domain and returns the same complete state. Closure follows because
composition is again a deterministic partial function into the required type.
Both associations h after(g after f) and(h after g) after f have domain exactly
those x for which f(x),g(f(x)),h(g(f(x))) are defined. Both return h(g(f(x))).
This proves closure, both identity laws and associativity. State constraints
remain part of each object's definition. A valid arrow never acquires a legal
output by discarding an illegal component or silently clipping it.

This is a general partial-map category, not a theorem unique to QR neurons.
The implemented execution-word representation concatenates the SAME ordered
operations; exact associative-word and empty-word tests are structural. It does
not assert floating sums or matrix products can be algebraically reassociated.
These laws alone would be a potentially trivial path description, providing no
independent prediction or commercial evidence.

## Open interfaces and shared ownership

A neuron is open: current fluid pressure projections affect its velocities, and
its port interaction changes the shared pressure field. Its private u/v state
alone is not a closed autonomous system. Each reciprocal port applies an exact
2x2 rotation to a neural velocity and a normalized fluid-kernel projection, plus
the corresponding weighted pressure increment. In real arithmetic the rotation
preserves their combined energy; numerical cancellation is checked separately.

Two pair components own disjoint neuron registers(0,1) and(2,3). Their boundary
interfaces borrow one common fluid register. Binding requires the same physical
ABI and complete nonduplicated neuron coverage. The compiled forward/reverse
port word preserves node/module ordering; the fluid operator runs ONCE, not once
per borrowed interface. Couplings on a shared body kernel are not freely
commuting. Types reject mismatched grid,dt,units,face orientation,duplicate fluid
ownership and missing node ports. The ordinary noncategorical physical validator
checks those same constraints; no artificial omission is used to make it fail.

This constrained operator construction does not establish arbitrary decorated-
cospan gluing, pushouts, a symmetric monoidal double category, or a reduced-state
Markov functor. General network reconfiguration and boundary-region decomposition
need separate definitions and evidence.

## Independent nontrivial prediction

Before direct seed427 E trajectories exist, Python constructs node coefficient
maps, pair interfaces, port rotations and a vectorized staggered acoustic map
from the registered equations and initial conditions. It composes them through
the ONE fluid register, with declared source input; it never reads direct-run
fields, fitted response traces or output targets. Frozen predictions at0,4,8 and
input/model/source hashes precede direct four-node P/T/F and pair P runs. Pair23
is deliberately forced through its first local member to validate an active pair.

The comparison diagram maps initial detailed state plus input to registered
observables(full fields,u/v and owned temporal traces), either by independently
composed numerical operators or by the direct Rust engine. Commutation is an
APPROXIMATE1e-10 relative test, not an exact categorical identity. P/T/F whole-state
refinement remains separately bounded at10%. The closed-product baseline omits
interfaces and predicts zero unforced-node response. Beating it shows predictive
importance of modeled coupling; it does not show category terminology beats a
correct conventional coupled simulator. Construction cost, runtime and interface
fault rejection are independently reported.

## Literature boundary

[Baez and Pollard, A Compositional Framework for Reaction Networks](https://arxiv.org/abs/1704.02051)
construct categories of open reaction networks and open dynamical systems. Their
framework motivates explicit boundaries and legal composition; it does not prove
this acoustic implementation has their categorical structure.
[Baez, Courser and Vasilakopoulou, Structured versus Decorated Cospans](https://arxiv.org/abs/2101.09363)
make additional categorical hypotheses explicit. QR12 does not assume those
hypotheses merely because its components expose arrays or ports. No novelty or
literature-priority claim follows from this bounded implementation exercise.
