# real_time_scenarios_realistic

Same 13 scenarios, same folder format as `real_time_scenarios/` (`before.arxml`, `after.arxml`,
`roles.yaml`, `NOTES.md`, `cli_output.json`, plus `full_vehicle_base.arxml` and `run_all_scenarios.py`),
but the ARXML now follows **AUTOSAR_TPS_ARXMLSerializationRules (FO R20-11)** and contains the layers a
real system/ECU extract has. Drop the folder next to `real_time_scenarios/` in the project root and run:

    python real_time_scenarios_realistic/run_all_scenarios.py

## Result

| Check | Result |
|---|---|
| Verdict, findings, node and edge counts vs. the original `cli_output.json` (13 scenarios) | identical |
| `autosar-data` strict load (schema R22-11 / `AUTOSAR_00051`), all 51 `.arxml` files | pass |
| Unresolved references (merged files; split set checked as one model) | 0 |
| Independent rules checker `check_serialization_rules.py`, all 51 files | 0 violations |
| Same checker on the original 27 files | 27 with violations |
| Original 27 files under `autosar-data` strict load | 27 fail (first error: missing `xmlns:xsi`) |
| Multi-file split sets (`split/`, 12 files) for all 13 scenarios vs. merged | identical results |
| Rebuild twice | byte-identical (UUIDs are derived from the AUTOSAR path) |

## Serialization rules applied

| Rule | How |
|---|---|
| 00001-00003 | merged single-file `before/after.arxml` plus a 12-file split example in `01_jeep_uconnect/split/`; `.arxml`, short names |
| 00004-00008 | UTF-8, no BOM, `<?xml version="1.0" encoding="UTF-8"?>` |
| 00011, 00017, 00018 | `http://autosar.org/schema/r4.0` as default namespace, no prefixes, only `xsi` besides it |
| 00012, 00013 | mandatory `xsi:schemaLocation="http://autosar.org/schema/r4.0 AUTOSAR_00051.xsd"` (no path) |
| 00014 | unordered containers sorted by SHORT-NAME (schema says which are unordered) |
| 00015, 00016 | no `<X/>`, no empty wrappers (the originals had empty `<ELEMENTS/>`) |
| 00019 | 2-space indent, one element per block, primitives on one line, attributes alphabetical, root attributes on separate lines |
| references | all absolute short-name paths |

## What was added (scenario 01 `after.arxml`: 1,055 -> 3,069 elements)

- **Data types:** `/Platform` base types and implementation types; every data element is typed (`TYPE-TREF`).
- **Behavior:** `SWC-INTERNAL-BEHAVIOR` per atomic component (28), runnables, timing and data-received events, send/receive points, `SWC-IMPLEMENTATION`.
- **Bus layer:** per package a `CAN-CLUSTER` (CAN FD) with frames, frame triggerings, PDU triggerings; ECUs get a controller, a connector and frame/PDU ports. Which ECU sends and receives each PDU is derived from the original mappings and connectors.
- **SecOC:** schema-valid `SECURE-COMMUNICATION-PROPS` (algorithm, auth-info length, data ID, freshness) and `PAYLOAD-REF` pointing at the authentic PDU's `PDU-TRIGGERING`.
- **System:** `CATEGORY`, `FIBEX-ELEMENTS`; file hygiene: `ADMIN-DATA`, UUIDs, descriptions.

## Things I found in the original files

1. They are not valid ARXML: missing `xmlns:xsi`/`schemaLocation`; `AUTH-INFO-TX-LENGTH` and `FRESHNESS-*` sit directly in `SECURED-I-PDU` (schema puts them in `SECURE-COMMUNICATION-PROPS`); `PAYLOAD-REF` used `DEST="I-SIGNAL-I-PDU"` (schema requires `PDU-TRIGGERING`).
2. In scenarios 03, 04 and 05 `after.arxml`, the 4 SecOC wrappers had an **empty** `PAYLOAD-REF`, so they protected nothing. I wired them to the PDU their name points to (e.g. `icToGwSecuredIPdu` -> `icToGwIPdu`). Verdicts did not change, so those PASS/FLAG results do not depend on that SecOC.
3. `secoc.py` reads `AUTH-INFO-TX-LENGTH` / `FRESHNESS-VALUE-LENGTH` as direct children of `SECURED-I-PDU`. In valid ARXML they are nested, so the tool now reads them as `None`. Nothing consumes those values today (that is also why scenario 12 PASSes), but a MAC-strength check would need `.//` instead of a direct child lookup.

## Limits

- Generated, not vendor output: descriptions are auto-text; all signals are 64-bit `Byte8Array`; one CAN-FD cluster per package.
- Not included: SOME/IP / Ethernet (scenario 08 stays at its original level), ECUC values, I-SIGNAL-TRIGGERINGs, NM/TP/diagnostics, the old header comments.
- `autosar-data` checks structure, enums and references, not mandatory-element completeness or OCL constraints, and I could not download the official XSD. The schema number `AUTOSAR_00051` is one constant (`SCHEMA_HINT`) in `build_realistic.py`.
- The tool ignores most of the new content, so results are unchanged; the content makes the inputs realistic, not the detector stronger.

## Rebuild / audit

    pip install autosar-data lxml pyyaml
    python real_time_scenarios_realistic/build_realistic.py [--split-all]
    python real_time_scenarios_realistic/check_serialization_rules.py real_time_scenarios_realistic
