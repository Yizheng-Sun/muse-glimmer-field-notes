# Coding results recorded so far

Results from the owner-supplied 5090 runs, with separate reviewer reconstruction where stated. Functional outcomes use the unchanged case acceptance checks. Tool counts below are actual calls counted from session exports.

| Case | First autonomous result | Acceptance | Tool calls | Session duration | Evidence |
| --- | --- | --- | --- | --- | --- |
| C01 | FAIL | Six methods; 21 failing subcases; no source edit | 60 | 218.56 s | [Analysis](../evidence/coding/C01/attempt-01-analysis.md) |
| C02 | PASS | All five methods pass; one source patch | 60 | 331.83 s | [Analysis](../evidence/coding/C02/attempt-01-analysis.md) |
| C03 | Pending | No run supplied | — | — | — |
| C04 | Pending | No run supplied | — | — | — |

C01's separate [assisted continuation](../evidence/coding/C01/assisted-continuation-analysis.md) produced a partial fix but still failed four subcases. It does not replace the first autonomous result.

C02 exhausted its tool budget after producing a passing fix. Its remaining focused upstream failure is an old expectation incompatible with the requested new sentence rule; Glimmer identified the conflict but did not update the test. Record functional success and incomplete test maintenance separately.

The chosen Hermes backend is local. Filesystem and public-network isolation were not enforced; the analyses describe the observed scope deviations. Complete frozen runtime records and final remote artifacts remain incomplete.
