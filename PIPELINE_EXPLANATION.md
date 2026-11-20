# ARXML SecDiff — Core Logic Pipeline & 4-Person Presentation Guide

This document provides a comprehensive, algorithmic breakdown of the **ARXML SecDiff** core verification pipeline. The architecture is partitioned into **4 logical presentation parts** designed for 4 team members to present individually.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             FULL PIPELINE FLOW                                   │
├────────────────────┬────────────────────┬───────────────────┬────────────────────┤
│    PRESENTER 1     │    PRESENTER 2     │    PRESENTER 3    │    PRESENTER 4     │
│   Ingestion &      │  Multigraph Build  │ Dual-Graph Diff & │ ISO/SAE 21434 Risk │
│   Path Indexing    │ & 3-Valued SecOC   │ DFS Reachability  │ Scoring & Gate     │
├────────────────────┼────────────────────┼───────────────────┼────────────────────┤
│ • parser.py        │ • graph.py         │ • diff.py         │ • severity.py      │
│ • xmlutil.py       │ • secoc.py         │ • reach.py        │ • gate.py          │
│ • model.py         │                    │ • roles.py        │ • findings.py      │
│ • ecu.py           │                    │                   │ • report.py        │
│ • signals.py       │                    │                   │                    │
└────────────────────┴────────────────────┴───────────────────┴────────────────────┘
```

---

# Part 1: AUTOSAR Ingestion, Metamodel Parsing & Path Indexing

* **Assigned Team Member**: Presenter 1
* **Core Code Files**:
  * `arxml_secdiff/parser.py` (Main extraction engine & recursive path indexer)
  * `arxml_secdiff/xmlutil.py` (Namespace-agnostic XML loader & element helpers)
  * `arxml_secdiff/model.py` (In-memory AST representation dataclasses)
  * `arxml_secdiff/ecu.py` (ECU instance & SWC-to-ECU mapping parser)
  * `arxml_secdiff/signals.py` (System signal, I-PDU, and Secured-I-PDU parser)

---

### 1.1 The Problem It Solves
AUTOSAR XML (ARXML) models an entire vehicle's electrical and software architecture in an XML Schema Definition (XSD) hierarchy. In large OEM workflows:
1. **Multi-File Separation**: A single vehicle model is split across dozens of files (data types in one file, interfaces in another, topologies in another) as permitted by AUTOSAR rule `[TPS_ASR_00001]`.
2. **Schema Incompatibility**: Different AUTOSAR releases (4.0, 4.2, 4.4) carry varying XML namespaces (e.g., `http://autosar.org/schema/r4.0`).
3. **Complex Cross-Referencing**: Connectors do not contain inline definitions; they use text reference paths (e.g., `/FV/Swc/Root/tcu`) to reference elements declared in other files.

---

### 1.2 Algorithmic Implementation

#### A. Namespace-Agnostic Ingestion (`xmlutil.py`)
To prevent the parser from breaking when comparing files created in different AUTOSAR toolchains, `xmlutil.strip_namespaces()` rewrites every qualified tag and attribute to its local name in-place during parse time:
```python
# arxml_secdiff/xmlutil.py
def strip_namespaces(root: etree._Element) -> etree._Element:
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
        ...
```
This guarantees deterministic, version-independent element matching.

#### B. The Recursive Tree Path Indexing Algorithm (`parser.py`)
AUTOSAR forms canonical references by concatenating the `<SHORT-NAME>` of parent packages. `parser.build_index()` implements a generic recursive traversal:
* Every element containing a `<SHORT-NAME>` (packages, components, ports, connectors) appends a path segment:
  ```text
  path = prefix + "/" + SHORT-NAME
  ```
* Structural packaging wrappers (`<AR-PACKAGES>`, `<ELEMENTS>`, `<PORTS>`) do not add path segments; the recursive accumulator passes the current prefix through unchanged.
* Output: A flat dictionary `index: dict[str, etree._Element]` mapping absolute paths (e.g., `/FV/Swc/Root/tcu`) directly to their parsed XML DOM elements.

```
       <AR-PACKAGE> (SHORT-NAME: FV)           --> /FV
             └── <AR-PACKAGE> (SHORT-NAME: Swc)        --> /FV/Swc
                   └── <SW-COMPONENT-PROTOTYPE> (SHORT-NAME: tcu) --> /FV/Swc/Root/tcu
```

#### C. Extraction of Architectural Primitives
With the global index populated:
1. **Component Prototypes & Types**: Extracted from compositions (`SW-COMPONENT-PROTOTYPE`).
2. **Assembly Connectors**: Maps provider ports (`P-PORT-PROTOTYPE`) to requirer ports (`R-PORT-PROTOTYPE`).
3. **SWC-to-ECU Mapping (`ecu.py`)**: Traverses `<SWC-TO-ECU-MAPPING>` within `<SYSTEM-MAPPING>` to associate each software component with its physical microcontroller host (e.g., `/FV/Ecu/TelematicsEcu`).
4. **I-PDU Signal Binding (`signals.py`)**: Traverses `<I-SIGNAL-TO-PDU-MAPPING>` and `<SECURED-I-PDU>` to register which network frames carry which component data.

---

### 1.3 Speaker Notes / Presentation Script for Presenter 1
> *"Hello everyone. I am covering **Part 1: How we parse and index complex AUTOSAR XML models**.*
>
> *In AUTOSAR, a vehicle system model is distributed across multiple XML files where software components, network signals, and hardware allocations reference each other across file boundaries.*
>
> *Our parser (`parser.py`) treats the entire file set as one atomic package. It uses `xmlutil.py` to strip namespace variations so the tool can accept any AUTOSAR schema version (4.0 through 4.4). It then executes a recursive path-indexing algorithm: whenever an element has a `<SHORT-NAME>`, it builds its absolute canonical path, such as `/FV/Swc/Root/tcu`.*
>
> *Finally, it resolves three critical relationships: component prototypes, the assembly connectors linking them, and the physical ECU instance hosting each component. This clean in-memory model is what feeds Part 2: Multigraph Construction."*

---

# Part 2: Multigraph Construction & 3-Valued SecOC Wire Annotation

* **Assigned Team Member**: Presenter 2
* **Core Code Files**:
  * `arxml_secdiff/graph.py` (Multigraph transformation & topology builder)
  * `arxml_secdiff/secoc.py` (3-Valued SecOC cryptographic wire classification)

---

### 2.1 The Problem It Solves
Raw ARXML files represent connections as software-level port bindings. However, in automotive cybersecurity, **where** the communication takes place physically is critical:
* If Component A and Component B live on the **same ECU**, communication occurs over shared RAM via the **Runtime Environment (RTE)**. A physical CAN bus sniffer cannot observe or inject this data.
* If Component A and Component B live on **different ECUs**, signals must be packaged into frames and sent over a physical automotive wire (CAN, CAN-FD, FlexRay, or Automotive Ethernet).
* We must know: **Is that physical wire cryptographically protected by SecOC (Secure Onboard Communication), or is it raw, unauthenticated plaintext?**

---

### 2.2 Algorithmic Implementation

#### A. Directed Multigraph Transformation (`graph.py`)
The tool constructs a directed multigraph $G = (V, E)$ using NetworkX:
* **Vertices ($V$)**: Every software component prototype represents a node.
  * Attributes: `short_name`, canonical `path`, `type_ref`, physical `ecu`, and security `role` (`entry`, `critical`, or `standard`).
* **Edges ($E$)**: Every assembly connector is converted into a directed communication edge:
  $$u \xrightarrow{\quad (\text{connector}, \text{influence}) \quad} v$$
  Multiple edges can exist between the same two SwCs if they share multiple connectors (hence a Multigraph).

#### B. The 3-Valued Security State Machine (`secoc.py`)
For every communication edge `(u, v) ∈ E`, the engine evaluates a 3-valued security classification function:

```text
SecState(u, v) ∈ { RTE_LOCAL, AUTHENTICATED, UNPROTECTED }
```

```
                          ┌────────────────────────┐
                          │    Edge (u -> v)       │
                          └───────────┬────────────┘
                                      │
                         Are u and v on same ECU?
                                     / \
                              YES   /   \   NO
                                   /     \
                                  ▼       ▼
                     ┌──────────────┐   Is frame carried by
                     │  RTE_LOCAL   │   <SECURED-I-PDU>?
                     └──────────────┘       / \
                                     YES   /   \   NO
                                          /     \
                                         ▼       ▼
                            ┌───────────────┐  ┌─────────────┐
                            │ AUTHENTICATED │  │ UNPROTECTED │
                            └───────────────┘  └─────────────┘
```

1. **`RTE_LOCAL`**:
   * Evaluated when `ECU(u) == ECU(v)`.
   * Communication is bus-invisible. An external attacker with a CAN bus tap cannot manipulate this channel without physical micro-controller firmware exploitation.
2. **`AUTHENTICATED` (SecOC = True)**:
   * Evaluated when `ECU(u) != ECU(v)` AND the underlying signals are mapped to an active `<SECURED-I-PDU>`.
   * The frame includes an AUTOSAR SecOC cryptographic Message Authentication Code (MAC) and freshness counter. Frames cannot be forged or replayed on the bus.
3. **`UNPROTECTED` (SecOC = False)**:
   * Evaluated when `ECU(u) != ECU(v)` AND no `<SECURED-I-PDU>` encapsulates the traffic.
   * **Vulnerability**: Any attacker with bus access (via OBD-II, compromised telematics, or headlight wiring) can trivially inject forged frames to control the receiving component.

---

### 2.3 Speaker Notes / Presentation Script for Presenter 2
> *"Hello, I am presenting **Part 2: Multigraph Construction and 3-Valued SecOC Wire Annotation**.*
>
> *Once the ARXML is parsed, `graph.py` converts the architecture into a directed multigraph $G = (V, E)$. The nodes are software components and the directed edges represent dataflow connectors.*
>
> *The core innovation in this stage is in `secoc.py`, which implements our **3-Valued Wire Security Classification**.*
> * *First, it checks hardware boundaries: if two components are on the same physical ECU, the state is **`RTE_LOCAL`**. This means the message stays inside microcontroller RAM and never touches a physical vehicle wire.*
> * *Second, if the components are on different ECUs, the signal must travel over a physical bus like CAN or Ethernet. The algorithm inspects the communication matrix: if it is wrapped in an AUTOSAR `<SECURED-I-PDU>` with cryptographic MAC authentication, it is labeled **`AUTHENTICATED`**.*
> * *If SecOC is missing, it is labeled **`UNPROTECTED`**. This distinction is fundamental because unauthenticated bus traffic is what enables real-world automotive cyber-attacks. This annotated graph is now passed to Presenter 3 for Differential and Reachability Analysis."*

---

# Part 3: Dual-Graph Differential & Transitive Attack Reachability

* **Assigned Team Member**: Presenter 3
* **Core Code Files**:
  * `arxml_secdiff/diff.py` (Dual-graph structural & semantic differential engine)
  * `arxml_secdiff/reach.py` (Constrained DFS transitive reachability algorithm)
  * `arxml_secdiff/roles.py` (Threat boundary seeds: Entry Points vs Critical Targets)

---

### 3.1 The Problem It Solves
Automotive architectures evolve continuously across software releases. When comparing a baseline release ($G_{\text{before}}$) against an updated candidate ($G_{\text{after}}$):
* Standard file diff tools (`git diff`) produce thousands of lines of meaningless XML formatting noise.
* More importantly, individual connector additions often appear benign in isolation, but in combination with existing topology, they create **transitive attack chains** from external wireless entry points directly to safety-critical brakes or steering.

---

### 3.2 Algorithmic Implementation

#### A. Dual-Graph Differential ($\Delta G$) (`diff.py`)
`diff.compute_diff(G_before, G_after)` performs graph subtraction:
* **Vertex Diff ($\Delta V$)**: Identifies added nodes, removed nodes, and re-hosted nodes ($\text{ECU}_{\text{before}}(v) \ne \text{ECU}_{\text{after}}(v)$).
* **Edge Diff ($\Delta E$)**: Categorizes connectors into:
  * `ADDED` / `REMOVED` connectors.
  * `NEWLY_UNPROTECTED`: Connectors that were SecOC-authenticated or RTE-local in the baseline, but lost their cryptographic protection in the update.
  * `NEWLY_BUS_VISIBLE`: Connectors that were internal to an ECU before, but were moved across physical ECUs without security controls.

#### B. Threat Boundary Seeding (`roles.py`)
The threat model partitions nodes into two critical security sets:
1. **Untrusted Entry Points ($S$)**: Components with external communication surfaces (Telematics/TCU, Bluetooth/Infotainment, Wi-Fi, OBD-II diagnostic gateway).
2. **Safety-Critical Targets ($T$)**: Actuators governed by ISO 26262 functional safety requirements, rated at **ASIL-D** (Braking Control, Steering Actuators, Powertrain).

#### C. Constrained Transitive DFS Reachability Algorithm (`reach.py`)
To discover if an attacker can compromise safety targets, `reach.find_paths()` executes a **pruned Depth-First Search (DFS)** from every seed $s \in S$ to every target $t \in T$:

$$\Delta R = R(G_{\text{after}}) \setminus R(G_{\text{before}})$$

```python
# Algorithmic Concept in arxml_secdiff/reach.py
def find_attack_paths(graph, entry_points, critical_targets):
    attack_paths = []
    for s in entry_points:
        for t in critical_targets:
            # Execute constrained DFS
            for path in dfs_paths(graph, source=s, target=t):
                # An attack route is valid iff it contains >= 1 UNPROTECTED bus hop
                if any(edge.sec_state == "UNPROTECTED" for edge in path.edges):
                    if path not in baseline_paths:
                        attack_paths.append(path)
    return attack_paths
```

* **Pruning Conditions**:
  * Cycles are pruned via path visitation sets.
  * If a path is fully protected (all hops are either `RTE_LOCAL` or `AUTHENTICATED`), it is discarded because cryptographic MACs prevent frame forgery.
  * A route is flagged as an active attack path **if and only if at least one hop crosses an `UNPROTECTED` physical bus link**.

```
[TCU (Entry)] ──(RTE-local)──> [OTA Mgr] ──[UNPROTECTED CAN BUS]──> [CGW] ──(SecOC)──> [Chassis/Brakes (ASIL-D)]
                                           ▲
                                 CRITICAL ATTACK HOP!
                     (Attacker on CAN bus can forge this frame)
```

---

### 3.3 Speaker Notes / Presentation Script for Presenter 3
> *"Hello, I am presenting **Part 3: Dual-Graph Differential and Transitive Attack Reachability**.*
>
> *Once we have both the baseline graph $G_{\text{before}}$ and the proposed release $G_{\text{after}}$, `diff.py` computes the architectural delta ($\Delta G$). It detects added connectors, modified configurations, and security regressions—such as a connection that lost its SecOC encryption.*
>
> *Then, in `reach.py`, we implement a **Constrained Depth-First Search (DFS)** algorithm.*
> * *We seed the search with **Untrusted Entry Points ($S$)**—like Cellular Telematics and Infotainment—and search for paths leading to **ASIL-D Safety Targets ($T$)**—like Electronic Braking and Steering.*
> * *A path is only an exploitable attack chain if it contains at least one **UNPROTECTED bus hop**. If every hop is authenticated by SecOC, the route is safe.*
> * *If a path contains an unprotected bus link, an attacker who compromises the telematics unit can sniff and inject CAN messages to actuate the brakes—exactly what Miller and Valasek did in the famous 2015 Jeep Cherokee hack.*
> * *Our algorithm identifies all newly opened attack chains ($\Delta R$) and passes them to Presenter 4 for risk scoring and gating."*

---

# Part 4: ISO/SAE 21434 Risk Scoring & Automated Release Gate

* **Assigned Team Member**: Presenter 4
* **Core Code Files**:
  * `arxml_secdiff/severity.py` (ISO/SAE 21434 Risk Matrix scoring synthesizer)
  * `arxml_secdiff/gate.py` (Automated CI/CD release gate policy engine)
  * `arxml_secdiff/findings.py` (Formal audit record and rationale synthesizer)
  * `arxml_secdiff/report.py` (Textual and JSON terminal reporting)

---

### 4.1 The Problem It Solves
Finding an attack path is not enough for an automotive OEM. Engineering managers need an automated decision:
* Does this regression violate **ISO/SAE 21434** automotive cybersecurity standards?
* Is the impact life-threatening (**ASIL-D**) or minor convenience?
* **Should the build be blocked in the CI/CD pipeline, or can it be shipped?**

---

### 4.2 Algorithmic Implementation

#### A. The ISO/SAE 21434 2D Risk Matrix (`severity.py`)
The tool synthesizes risk by cross-referencing two formal dimensions:
1. **Impact Rating ($I$)**:
   * Evaluated from the target node's functional safety ASIL rating:
     * **Severe**: Target is ASIL-D (Braking, Steering, Powertrain shutdown).
     * **Major**: Target is ASIL-C / ASIL-B.
     * **Moderate / Negligible**: Infotainment or convenience features (HVAC, ambient lighting).
2. **Attack Feasibility ($F$)**:
   * Evaluated from the vulnerability of the hops along the attack chain:
     * **High Feasibility**: Communication traverses an unauthenticated physical bus (CAN/Ethernet). Injecting raw frames requires commodity hardware ($<\$20$) and no cryptographic keys.
     * **Low / Medium Feasibility**: Cross-gateway filtered hops.

#### B. Risk Level Mapping (1 to 5)
Following ISO/SAE 21434 Table H.8, the engine computes:

```text
Risk Level = Matrix(Impact, Feasibility) ∈ [1, 5]
```

| Impact $\downarrow$ \ Feasibility $\rightarrow$ | Low | Medium | High |
| :--- | :---: | :---: | :---: |
| **Severe (ASIL-D)** | Risk 3 | Risk 4 | **Risk 5 (Critical)** |
| **Major (ASIL-B/C)** | Risk 2 | Risk 3 | **Risk 4** |
| **Moderate** | Risk 1 | Risk 2 | **Risk 3** |
| **Negligible** | Risk 1 | Risk 1 | **Risk 1** |

Every finding generates a structured audit record in `findings.py` documenting the exact route, bus hops, and engineering rationale.

#### C. The Release Gate Decision Policy (`gate.py`)
`gate.evaluate_gate()` acts as the final arbiter, applying policy thresholds:

```python
# Policy in arxml_secdiff/gate.py
if risk_5_count > 0 or blocking_findings > 0:
    verdict = "BLOCK"    # Exit Code 3
elif flagged_findings > 0:
    verdict = "FLAG"     # Exit Code 2
else:
    verdict = "PASS"     # Exit Code 0
```

1. **`BLOCK` (Exit Code 3)**:
   * **Trigger**: Any finding with **Risk $\ge 5$** (e.g., an unauthenticated transitive path from Telematics to an ASIL-D Chassis component).
   * **Action**: Rejects the proposed release immediately in CI/CD pipelines.
2. **`FLAG` (Exit Code 2)**:
   * **Trigger**: Moderate architectural changes or intermediate risk findings (Risk 3–4).
   * **Action**: Requires mandatory manual security review and cryptographic sign-off.
3. **`PASS` (Exit Code 0)**:
   * **Trigger**: Clean release; zero new attack reachability paths opened to safety targets.
   * **Action**: Release approved for vehicle deployment.

---

### 4.3 Speaker Notes / Presentation Script for Presenter 4
> *"Hello, I am presenting **Part 4: ISO/SAE 21434 Risk Scoring and the Automated Release Gate**.*
>
> *Once Presenter 3's algorithm uncovers attack paths, my section turns those paths into an actionable engineering decision using `severity.py` and `gate.py`.*
>
> *We align directly with **ISO/SAE 21434**, the international standard for road vehicle cybersecurity.*
> * *We determine **Impact** from the functional safety classification: an ASIL-D target means life-threatening, Severe impact.*
> * *We determine **Attack Feasibility** from the wire state: an unauthenticated CAN bus link means High feasibility because forging frames requires no encryption keys and commodity hardware.*
> * *Synthesizing Severe Impact with High Feasibility yields a **Risk Level 5 (Critical)**.*
>
> *Finally, `gate.py` enforces the automated gatekeeper verdict:*
> * *If any Risk 5 vulnerability exists, it issues a **`BLOCK`** with exit code 3, failing the CI/CD pipeline and preventing vulnerable software from ever reaching the factory floor.*
> * *If changes are moderate, it issues a **`FLAG`** requiring manual OEM sign-off.*
> * *If no new paths exist, it outputs **`PASS`** with exit code 0.*
>
> *Together, our 4 parts form an end-to-end, mathematically rigorous cybersecurity verification pipeline for software-defined vehicles."*

---

# Presentation Summary Cheat-Sheet

| Presenter | Primary File(s) | Main Responsibility | Key Takeaway Phrase |
| :--- | :--- | :--- | :--- |
| **Presenter 1** | `parser.py`, `xmlutil.py`, `model.py` | Ingestion, Namespace Stripping & AST Indexing | *"We turn disparate XML files into a unified canonical path index."* |
| **Presenter 2** | `graph.py`, `secoc.py` | Multigraph Construction & 3-Valued SecOC | *"We distinguish bus-invisible memory from unauthenticated physical wires."* |
| **Presenter 3** | `diff.py`, `reach.py`, `roles.py` | Dual-Graph Diff & Constrained DFS Reachability | *"We mathematically identify newly opened attack chains from Telematics to Brakes."* |
| **Presenter 4** | `severity.py`, `gate.py`, `findings.py` | ISO/SAE 21434 Risk Matrix & CI/CD Release Gate | *"We translate attack routes into ISO/SAE 21434 Risk 5 verdicts to BLOCK vulnerable releases."* |
