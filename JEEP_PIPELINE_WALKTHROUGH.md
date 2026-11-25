# Complete Pipeline Walkthrough: `01_jeep_uconnect` (4-Node Minimal Scenario)

This document provides a complete, ground-level walkthrough of the **ARXML SecDiff** 5-stage verification pipeline using the minimal 4-node Jeep Cherokee Uconnect scenario (`scenario_runs/01_jeep_uconnect`).

> **Real-World Context**: Based on the 2015 Jeep Cherokee remote exploit (Miller & Valasek, Black Hat USA 2015), where a firmware/configuration update opened an unauthenticated path from the cellular/infotainment head unit across the V850 gateway bridge to the steering controller.

---

## 1. Scenario Architecture Overview

This scenario consists of **4 Software Component Prototypes** deployed across **3 Physical ECUs**:

```
┌───────────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│       TelematicsEcu       │      │     GatewayEcu      │      │     ChassisEcu      │
│                           │      │                     │      │                     │
│  [tel] ──(RTE)──► [ivi]   │ ───► │      [bridge]       │ ───► │       [steer]       │
│  (Entry)         (Entry)  │      │     (V850Bridge)    │      │   (ASIL-D Target)   │
└───────────────────────────┘      └─────────────────────┘      └─────────────────────┘
        Before: 1 edge                     Added in After               Added in After
```

* **Before (`before.arxml`)**: Only `tel` $\to$ `ivi` exists (both on `TelematicsEcu`, isolated from the rest of the vehicle).
* **After (`after.arxml`)**: Two new connectors (`huToBridge` and `bridgeToSteer`) are added, creating an unauthenticated physical bus path from infotainment to steering.
* **Threat Boundaries (`roles.yaml`)**:
  * **Untrusted Entry Points ($S$)**: `/S01UCON/Swc/Root/tel`, `/S01UCON/Swc/Root/ivi`
  * **Safety-Critical Target ($T$)**: `/S01UCON/Swc/Root/steer` (**ASIL-D**)

---

## 2. Stage 1: AST Parsing & Path Indexing (`xmlutil.py` & `parser.py`)

`parser.parse()` strips the AUTOSAR XML namespace (`xmlns="http://autosar.org/schema/r4.0"`), recursively walks the XML DOM, and builds an $\mathcal{O}(1)$ hash dictionary (`model.index`) keyed by canonical `<SHORT-NAME>` paths.

### Extracted from `before.arxml`
* **4 Component Prototypes** (`model.prototypes`):
  * `/S01UCON/Swc/Root/tel` (Type: `/S01UCON/Swc/Telematics`)
  * `/S01UCON/Swc/Root/ivi` (Type: `/S01UCON/Swc/HeadUnit`)
  * `/S01UCON/Swc/Root/bridge` (Type: `/S01UCON/Swc/V850Bridge`)
  * `/S01UCON/Swc/Root/steer` (Type: `/S01UCON/Swc/SteeringCtrl`)
* **3 Physical ECUs** (`model.ecus`):
  * `/S01UCON/Topology/TelematicsEcu`
  * `/S01UCON/Topology/GatewayEcu`
  * `/S01UCON/Topology/ChassisEcu`
* **SWC-to-ECU Mappings** (`model.swc_to_ecu`):
  * `tel`, `ivi` $\to$ `TelematicsEcu`
  * `bridge` $\to$ `GatewayEcu`
  * `steer` $\to$ `ChassisEcu`
* **1 Assembly Connector** (`model.assembly_connectors`):
  * `/S01UCON/Swc/Root/cellToHu`: `tel/cellToHuOut` $\to$ `ivi/cellToHuIn`
* **Signals & PDUs**: `0` SystemSignals, `0` ISignals, `0` PDUs.

### Extracted from `after.arxml` (The Proposed Update)
Contains all entities from `before.arxml`, plus:
* **2 New Assembly Connectors**:
  1. `/S01UCON/Swc/Root/huToBridge`: `ivi/huToBridgeOut` $\to$ `bridge/huToBridgeIn`
  2. `/S01UCON/Swc/Root/bridgeToSteer`: `bridge/bridgeToSteerOut` $\to$ `steer/bridgeToSteerIn`
* **2 New 4-Tier Signal-to-PDU Chains**:
  1. `huToBridgeOut` $\to$ `huToBridgeSSig` (`SYSTEM-SIGNAL`) $\to$ `huToBridgeISig` (`I-SIGNAL`) $\to$ `huToBridgeIPdu` (`I-SIGNAL-I-PDU`)
  2. `bridgeToSteerOut` $\to$ `bridgeToSteerSSig` (`SYSTEM-SIGNAL`) $\to$ `bridgeToSteerISig` (`I-SIGNAL`) $\to$ `bridgeToSteerIPdu` (`I-SIGNAL-I-PDU`)
* **SecOC Profiles (`<SECURED-I-PDU>`)**: `0` (No cryptographic protection configured).

---

## 3. Stage 2: Multigraph Construction (`graph.py` & `ecu.py`)

`graph.build(model)` converts the parsed `Model` into a `networkx.MultiDiGraph` $G = (V, E)$:
* **Node IDs**: Component **prototype** paths (so multiple instances never collapse).
* **Edge Direction**: Encodes **influence** (`Provider -> Requester` for Sender-Receiver).
* **Physical Boundary Check**: Calls `ecu.is_cross_ecu(model, provider, requester)` to determine if the wire stays in local ECU memory (`False`) or crosses a physical vehicle bus (`True`).

| Snapshot | Edge (`source` $\to$ `target`) | Connector Key | `influence` | `cross_ecu` | Physical Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Before** | `tel` $\to$ `ivi` | `cellToHu#data` | `data` | `False` | Both on `TelematicsEcu` (RTE RAM) |
| **After** | `tel` $\to$ `ivi` | `cellToHu#data` | `data` | `False` | Both on `TelematicsEcu` (RTE RAM) |
| **After** | `ivi` $\to$ `bridge` | `huToBridge#data` | `data` | **`True`** | `TelematicsEcu` $\to$ `GatewayEcu` (Bus) |
| **After** | `bridge` $\to$ `steer` | `bridgeToSteer#data` | `data` | **`True`** | `GatewayEcu` $\to$ `ChassisEcu` (Bus) |

---

## 4. Stage 3: 3-Valued SecOC Wire Annotation (`secoc.py` & `signals.py`)

`secoc.annotate(graph, model)` computes `attrs["authenticated"]` for each edge using 3-valued logic (`None`, `False`, `True`):

1. **`tel` $\to$ `ivi` (`cellToHu#data`)**:
   * `cross_ecu == False` (same physical ECU).
   * **State**: `authenticated = None` (**`RTE_LOCAL`** — bus-invisible internal memory; SecOC is not applicable).
2. **`ivi` $\to$ `bridge` (`huToBridge#data`)**:
   * `cross_ecu == True` (crosses physical bus).
   * `signals.py` traces port `huToBridgeOut` via `<SENDER-RECEIVER-TO-SIGNAL-MAPPING>` down to `/S01UCON/Comm/huToBridgeIPdu`.
   * `secoc.py` checks if `huToBridgeIPdu` is referenced by any `<SECURED-I-PDU>`'s `<PAYLOAD-REF>`. It is **not**.
   * **State**: `authenticated = False` (**`UNPROTECTED`** — raw bus frame vulnerable to spoofing/injection).
3. **`bridge` $\to$ `steer` (`bridgeToSteer#data`)**:
   * `cross_ecu == True` (crosses physical bus).
   * `signals.py` traces port `bridgeToSteerOut` down to `/S01UCON/Comm/bridgeToSteerIPdu`.
   * Not wrapped in any `<SECURED-I-PDU>`.
   * **State**: `authenticated = False` (**`UNPROTECTED`**).

---

## 5. Stage 4: Dual-Graph Diff & Pruned DFS Reachability (`diff.py` & `reach.py`)

### A. Structural Diff (`diff.between`)
Comparing $G_{\text{before}}$ and $G_{\text{after}}$ yields:
* `nodes_added`: `0`, `nodes_removed`: `0`
* `edges_added`: **2** (`huToBridge#data`, `bridgeToSteer#data`)
* `newly_unprotected`: **2**

### B. Constrained DFS Reachability (`reach.diff`)
The DFS algorithm starts at untrusted entry points $S = \{\text{tel}, \text{ivi}\}$ and searches for paths to safety-critical target $T = \{\text{steer}\}$. Any edge with `authenticated == True` is **cryptographically pruned** (traversal stops). Edges with `authenticated == False` or `None` are traversable.

* **Before Graph ($R_{\text{before}}$)**:
  * From `tel`: `tel` $\xrightarrow{\text{None}}$ `ivi` (dead end; `ivi` has no outgoing edges).
  * From `ivi`: dead end.
  * **Reachable attack paths**: `0`.

* **After Graph ($R_{\text{after}}$)**:
  1. **From `ivi`**: `ivi` $\xrightarrow{\text{auth=False}}$ `bridge` $\xrightarrow{\text{auth=False}}$ `steer` (**Target Reached — 2 hops**)
  2. **From `tel`**: `tel` $\xrightarrow{\text{auth=None}}$ `ivi` $\xrightarrow{\text{auth=False}}$ `bridge` $\xrightarrow{\text{auth=False}}$ `steer` (**Target Reached — 3 hops**)

* **Newly Opened Attack Paths ($\Delta R = R_{\text{after}} \setminus R_{\text{before}}$)**: **2 newly opened attack chains**.

---

## 6. Stage 5: ISO/SAE 21434 Risk Scoring & Release Gate (`severity.py` & `gate.py`)

### A. Risk Scoring (`severity.score_all`)
Using the ISO/SAE 21434 2D matrix (**Safety Impact $\times$ Attack Feasibility**), `severity.py` produces **4 Critical (Risk 5) findings**:

| # | Category | Subject | Impact | Feasibility | Risk Score | Rationale |
| :-: | :--- | :--- | :--- | :--- | :-: | :--- |
| **1** | `newly-reachable` | `ivi -> steer` | `severe` (ASIL-D) | `high` (2/2 unauth bus hops) | **5 (Critical)** | Direct unauthenticated path from HeadUnit to Steering |
| **2** | `newly-reachable` | `tel -> steer` | `severe` (ASIL-D) | `high` (2/3 unauth bus hops) | **5 (Critical)** | Transitive remote path from Cellular Telematics to Steering |
| **3** | `unprotected-new-hop` | `bridgeToSteer#data` | `severe` (inherited from `steer`) | `high` (no keys/MAC) | **5 (Critical)** | New unauthenticated bus hop lying on a route to ASIL-D `steer` |
| **4** | `unprotected-new-hop` | `huToBridge#data` | `severe` (inherited from `steer`) | `high` (no keys/MAC) | **5 (Critical)** | New unauthenticated bus hop lying on a route to ASIL-D `steer` |

### B. Automated Release Gate (`gate.evaluate`)
* **Policy Rule**: Any unwaived finding with `risk >= 5` triggers a hard `BLOCK`.
* **Blocking Findings**: `4`
* **Final Verdict**: **`BLOCK`**
* **CLI Exit Code**: `3`
* **Gate Reason**: `"4 finding(s) at risk 5 or above, worst: ivi can now reach steer"`
