# Evaluation results

Python 3.12.6 on Windows-11-10.0.26200-SP0. Timing: per-case pipeline.run only; excludes corpus generation, process startup and imports.

## Corpus

| before | cases | regression | benign | known-gap | skipped | seeded roles |
|---|---|---|---|---|---|---|
| scenario_b_v1.arxml | 285 | 150 | 93 | 42 | 15 | yes |
| **pooled** | **285** | **150** | **93** | **42** | **15** |  |

## Headline metrics

Label-based: a true positive means the tool produced the findings the mutation declared, not merely that it said something.

| metric | value | denominator |
|---|---|---|
| precision | 0.892 | 167 flagged |
| recall | 0.993 | 150 regressions |
| F1 | 0.940 | - |
| accuracy | 0.927 | 243 judged |
| false-positive rate | 0.0% | 93 benign controls |
| false-negative rate | 0.7% | 150 regressions |
| traps tripped | 18 | forbidden categories declared |
| known gaps confirmed | 42 | 42 declared |
| known gaps closed | 0 | label is stale if non-zero |
| errored cases | 0 | 285 cases |

## Time to detect

Per case, `pipeline.run` only.

| mean | median | p95 | max | total analysis time |
|---|---|---|---|---|
| 16.4 ms | 15.0 ms | 26.5 ms | 51.9 ms | 4.7 s over 285 cases |

## Naive before comparison

Flag-based, computed identically for every row: positives are the regression cases, negatives the benign controls, known gaps excluded from precision and recall and reported separately.

| detector | precision | recall | F1 | FP rate | gaps flagged | median | sees |
|---|---|---|---|---|---|---|---|
| text-diff | 0.62 | 1.00 | 0.77 | 98.9% | 42/42 | 25.2 ms | byte comparison after whitespace canonicalisation (git diff --exit-code) |
| element-diff | 0.64 | 1.00 | 0.78 | 92.5% | 42/42 | 15.5 ms | added / removed / changed AUTOSAR paths, no semantics |
| structural-grep | 0.63 | 0.89 | 0.74 | 84.9% | 12/42 | 7.1 ms | connector / secured-PDU / ECU-mapping pattern match; no reachability, boolean authentication |
| arxml-secdiff | 1.00 | 0.65 | 0.79 | 0.0% | 0/42 | 15.0 ms | component graph, entry-point reachability, three-valued SecOC |

## By mutation family

| family | cases | kinds | detected | missed | detection rate | false positives |
|---|---|---|---|---|---|---|
| add-component | 2 | regression | 2 | 0 | 100.0% | 0 |
| add-unrelated-package | 2 | benign | 0 | 0 | n/a | 0 |
| add-uuids | 4 | benign | 0 | 0 | n/a | 0 |
| bypass | 2 | regression | 2 | 0 | 100.0% | 2 |
| bypass-and-rehost | 12 | regression | 12 | 0 | 100.0% | 12 |
| bypass-and-strip-secoc | 4 | regression | 4 | 0 | 100.0% | 4 |
| reformat | 1 | benign | 0 | 0 | n/a | 0 |
| rehost | 33 | regression | 33 | 0 | 100.0% | 0 |
| rehost-and-strip-secoc | 12 | regression | 12 | 0 | 100.0% | 0 |
| rehost-onto-bus | 18 | regression | 18 | 0 | 100.0% | 0 |
| rehost-onto-bus-and-bypass | 13 | regression | 13 | 0 | 100.0% | 0 |
| remove-and-strip-secoc | 13 | regression | 12 | 1 | 92.3% | 0 |
| remove-component | 16 | regression | 16 | 0 | 100.0% | 0 |
| rename-connector | 48 | benign | 0 | 0 | n/a | 0 |
| rename-secured-pdu | 15 | benign | 0 | 0 | n/a | 0 |
| reorder | 23 | benign | 0 | 0 | n/a | 0 |
| strip-and-rename | 21 | regression | 21 | 0 | 100.0% | 0 |
| strip-secoc | 4 | regression | 4 | 0 | 100.0% | 0 |
| weaken-and-reorder | 21 | known-gap | 0 | 0 | n/a | 0 |
| weaken-freshness | 21 | known-gap | 0 | 0 | n/a | 0 |

## By composition order (Multi-site degradation)

How many mutation families were applied to make the case. Evaluates finding precision decay and spurious side-effect accumulation under compound churn.

| order | cases | finding precision | side-effect rate | mean findings/commit | traps tripped |
|---|---|---|---|---|---|
| 1 | 53 | 97.3% | 2.7% | 1.1 | 1 |
| 2 | 113 | 87.5% | 12.5% | 1.8 | 4 |
| 3 | 107 | 80.9% | 19.1% | 2.6 | 13 |
| 4 | 12 | 75.0% | 25.0% | 3.4 | 0 |

## Labels that did not hold

| case | kind | order | outcome | detail |
|---|---|---|---|---|
| bypass | regression | 1 | true-positive | forbidden unprotected-new-hop |
| bypass-and-strip-secoc__NavSecuredIPdu+reorder | regression | 3 | true-positive | forbidden unprotected-new-hop |
| bypass-and-rehost__trajGuard-to-ChassisEcu | regression | 2 | true-positive | forbidden unprotected-new-hop |
| bypass-and-rehost__diagRouter-to-ChassisEcu | regression | 2 | true-positive | forbidden unprotected-new-hop |
| bypass-and-rehost__btStack-to-AdasEcu | regression | 2 | true-positive | forbidden unprotected-new-hop |
| bypass-and-rehost__brakeCtl-to-GatewayEcu+rename-connector | regression | 3 | true-positive | forbidden unprotected-new-hop |
| bypass-and-rehost__brakeAct-to-IviEcu+reorder | regression | 3 | true-positive | forbidden unprotected-new-hop |
| bypass-and-strip-secoc__DecelSecuredIPdu+reformat | regression | 3 | true-positive | forbidden unprotected-new-hop |
| bypass-and-strip-secoc__NavSecuredIPdu+rename-connector | regression | 3 | true-positive | forbidden unprotected-new-hop |
| remove-and-strip-secoc__trajGuard__DecelSecuredIPdu+rename-connector | regression | 3 | false-negative | missing secoc-removed |
| bypass+rename-connector | regression | 2 | true-positive | forbidden unprotected-new-hop |
| bypass-and-rehost__diagRouter-to-ChassisEcu+rename-connector | regression | 3 | true-positive | forbidden unprotected-new-hop |
| bypass-and-strip-secoc__DecelSecuredIPdu+add-unrelated-package | regression | 3 | true-positive | forbidden unprotected-new-hop |
| bypass-and-rehost__adas-to-ChassisEcu+rename-connector | regression | 3 | true-positive | forbidden unprotected-new-hop |
| bypass-and-rehost__ivi-to-ChassisEcu+reformat | regression | 3 | true-positive | forbidden unprotected-new-hop |
| bypass-and-rehost__trajGuard-to-IviEcu+rename-connector | regression | 3 | true-positive | forbidden unprotected-new-hop |
| bypass-and-rehost__brakeCtl-to-AdasEcu+add-uuids | regression | 3 | true-positive | forbidden unprotected-new-hop |
| bypass-and-rehost__trajGuard-to-IviEcu+reformat | regression | 3 | true-positive | forbidden unprotected-new-hop |
| bypass-and-rehost__btStack-to-GatewayEcu+add-uuids | regression | 3 | true-positive | forbidden unprotected-new-hop |

## Known-gap register

Defects declared undetectable, asserted still undetected. Closing one makes the corpus fail until its label is updated, which is the point.

| family | cases | status | what goes undetected |
|---|---|---|---|
| weaken-freshness | 21 | confirmed missed | SecOC is read as a boolean: the presence of a SECURED-I-PDU wrapper makes the PDU authenticated regardless of its parameters, so a replayable 8-bit MAC scores the same as a sound configuration. The parameter change does reach the SecOC profile diff and is printed in the report, but it produces no finding and so can neither be scored nor gated on. Closing this needs a strength judgement in severity.py, not a parser change. |

## Coverage not exercised

Mutations that found no site in a before. Recorded because partial coverage reads as a clean sweep when it is hidden.

| before | mutation | reason |
|---|---|---|
| scenario_b_v1.arxml | expose-on-bus | no cross-ECU connector is missing its signal chain |
| scenario_b_v1.arxml | bypass-on-bus-and-strip-secoc__NavSecuredIPdu+reorder | no cross-ECU connector is missing its signal chain |
| scenario_b_v1.arxml | bypass-on-bus-and-strip-secoc__DecelSecuredIPdu+reformat | no cross-ECU connector is missing its signal chain |
| scenario_b_v1.arxml | strip-and-rename__all__guardToBrake+rename-secured-pdu | before has no SECURED-I-PDU |
| scenario_b_v1.arxml | strip-and-rename__DecelSecuredIPdu__adasToGuard+rename-secured-pdu | no SECURED-I-PDU at /B/Comm/DecelSecuredIPdu |
| scenario_b_v1.arxml | rehost-and-strip-secoc__gw-to-AdasEcu__all+rename-secured-pdu | before has no SECURED-I-PDU |
| scenario_b_v1.arxml | rehost-and-strip-secoc__btStack-to-ChassisEcu__NavSecuredIPdu+rename-secured-pdu | no SECURED-I-PDU at /B/Comm/NavSecuredIPdu |
| scenario_b_v1.arxml | remove-and-strip-secoc__diagRouter__all+rename-connector | no connector at /B/Swc/ScenarioB/gwToDiag |
| scenario_b_v1.arxml | bypass-on-bus-and-strip-secoc__NavSecuredIPdu+rename-connector | no cross-ECU connector is missing its signal chain |
| scenario_b_v1.arxml | remove-and-strip-secoc__ivi__NavSecuredIPdu+rename-secured-pdu | no SECURED-I-PDU at /B/Comm/NavSecuredIPdu |
| scenario_b_v1.arxml | remove-and-strip-secoc__gw__DecelSecuredIPdu+rename-secured-pdu | no SECURED-I-PDU at /B/Comm/DecelSecuredIPdu |
| scenario_b_v1.arxml | bypass-on-bus-and-strip-secoc__DecelSecuredIPdu+add-unrelated-package | no cross-ECU connector is missing its signal chain |
| scenario_b_v1.arxml | expose-on-bus+rename-secured-pdu | no cross-ECU connector is missing its signal chain |
| scenario_b_v1.arxml | strip-secoc__NavSecuredIPdu+rename-secured-pdu | no SECURED-I-PDU at /B/Comm/NavSecuredIPdu |
| scenario_b_v1.arxml | rehost-and-strip-secoc__diagRouter-to-AdasEcu__NavSecuredIPdu+rename-secured-pdu | no SECURED-I-PDU at /B/Comm/NavSecuredIPdu |
