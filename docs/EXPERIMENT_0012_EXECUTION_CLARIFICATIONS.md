# QR12 execution clarification: original-oracle aggregate label

Recorded after the Stage A executions and first independent audit, before B/C/D/E.
First audit reports are preserved under ignored post-outcome-oracle-label/ with
original gate INDETERMINATE and400/798 oracle aggregate failures. Do not erase them.

The unchanged original QR11 World.totals()[7] is SOURCE-port net transfer (excludes
node1), whereas new QR12 World.totals()[7] is ALL-port net transfer. The QR12
observer adapter placed the original value under the generic port_net heading
in ORACLE_P/F. This is a mislabeled legacy column, not missing underlying data:
exchange.csv contains every real signed per-port transfer; fluid/neural energy,
work, loss and every step/trace audit pass, and direct old/new physical arrays agree.

For ORACLE metadata only, the verifier now reconstructs that column from ports
whose neuron index differs from1, exactly the original QR11 quantity. It still
checks EVERY port rotation, energy cancellation, node update, trace update and
full stored-energy balance at the unchanged tolerances. All normal QR12 cases
retain all-port semantics. No raw bytes, physical trajectory, input, seed,
acceptance threshold, registration or old source is changed or rerun. No invalid
legacy aggregate is asserted to be a valid all-port total. Complete raw records
support independent reconstruction of the actual all-port quantity.

The original aggregate-heading defect remains a delivery/observability limitation
and is separately reported. This semantic correction does not repair or replace
a failed physical convergence test. The first audit's sole failed category was
this oracle aggregate interpretation; all registered refinement/reference/control
comparisons and all11 genuine new-engine A case audits already passed.
