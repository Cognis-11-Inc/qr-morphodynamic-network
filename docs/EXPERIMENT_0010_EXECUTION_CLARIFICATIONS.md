# QR10 execution clarifications before extended observations

Frozen registration9a3bb58 remains unchanged. Numerical and pilot outcomes already
exist; no new band/distance/seed or held-out outcomes exist at this clarification.
No acceptance criterion, source amplitude, kernel, seed, feature or grid changes.

The phrase "18 two-class nearest-mean templates" has an arithmetic inconsistency:
three bands times three distances equals9 decoders, each with2 class means,
hence18 class-template vectors. Execute these9 decoders and18 vectors, exactly
using the registered features and two calibration/two held-out seeds. Do not
invent extra readouts or duplicate decoders to reach18. Report this count typo.

The pilot supplies two explicit calibration reuses (seed211/LOW/d2 labels9/27).
The extended matrix therefore has34 new calibration,36 held-out primary,
36 held-out fine and8 interference executions=114 new, plus2 pilot reuses.
Fit/freeze all18 class vectors after all calibration and before any held-out case.

The third neuron's palette for interference uses unchanged generator ID2184
at seed211. The existing two use2182/2186. All three exist in every A-only,
B-only,AB+,AB- arm, including unforced emitter states. This preserves the same
linear system for superposition; no arm deletes an unforced transducer.

Coupled metadata schema2 adds third-neuron count/position where applicable;
kicks.csv includes the driven neuron index. source_energy aggregates all emitter
neurons (indices0 and2 for interference), receiver remains1. All neuron fields
and per-port work remain separately recorded. Pilot raw schema1 remains intact.

Physics time observed: standalone277.56s, pilot recorded separately. Remaining
matrix estimated under20min serial and total signed data under8GB. Stop rather
than silently reduce coverage if either registered resource ceiling is exhausted.
