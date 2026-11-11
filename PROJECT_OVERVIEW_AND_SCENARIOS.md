# ARXML SecDiff: Project Core Working, Algorithms & Real-Time Scenarios Reference

---

## Part 1: Core Working & Architecture of the Project

### High-Level Architecture Flow

```text
[before.arxml] ──┐
                 ├──> [1. Parser & Model] ──> [2. Graph Builder & SecOC Annotator]
[after.arxml]  ──┘                                        │
                                                          ▼
                                              [3. Dual-Graph Diff Engine]
                                                          │
                                                          ▼
                                              [4. Constrained Reachability Engine]
                                                          │
                                                          ▼
                                              [5. ISO/SAE 21434 Risk Scoring & Gate] ──> [BLOCK / FLAG / PASS]
```

### 5-Step Pipeline Breakdown

1. **AST Parsing & Entity Indexing (`parser.py`, `model.py`)**:
   * Uses recursive depth-first traversals over the AUTOSAR XML DOM to map paths into a global index (`index: dict[str, Element]`).
   * Extracts strongly-typed dataclasses: `ComponentType`, `Prototype`, `AssemblyConnector`, `DelegationConnector`, `EcuInstance`, `SwcToEcuMapping`, `SystemSignal`, `ISignal`, `Pdu`, and `SecuredIPdu`.
2. **Semantic Graph Construction & SecOC Annotation (`graph.py`, `secoc.py`)**:
   * Builds a directed multigraph $G = (V, E)$ where vertices are SWC prototypes and edges are port connectors.
   * Annotates every communication edge with 3-valued security states:
     * `None`: RTE-Internal hop (on the same physical ECU; no network frame generated).
     * `True`: Authenticated bus hop (`I-PDU` wrapped by a valid `SECURED-I-PDU`).
     * `False`: Unauthenticated bus hop (transmitted across physical vehicle bus without cryptographic MAC — vulnerable to spoofing/injection).
3. **Dual-Graph Semantic Diff Engine (`diff.py`)**:
   * Compares $G_{\text{before}} = (V_B, E_B)$ against $G_{\text{after}} = (V_A, E_A)$.
   * Detects added/removed connectors, component re-hosting across ECUs, and SecOC profile downgrades.
4. **Constrained Transitive Reachability Analysis (`reach.py`)**:
   * Computes simple directed paths from untrusted Entry Points ($S$, e.g., Cellular, Wi-Fi, BT, OBD) to Safety-Critical Targets ($T$, e.g., Steering, Brakes, Immobilizer) using depth-first search with path cutoff ($k \le 12$).
   * Calculates differential reachability: $\Delta R = \text{Paths}(G_{\text{after}}) \setminus \text{Paths}(G_{\text{before}})$.
   * Flags any attack path where at least one hop is unauthenticated.
5. **ISO/SAE 21434 Risk Scoring & Gate Enforcement (`severity.py`, `gate.py`)**:
   * Maps safety target ASIL ratings to impact levels (ASIL-D $\to$ Severe, ASIL-C $\to$ Major, ASIL-B $\to$ Moderate, QM $\to$ Negligible).
   * Combines impact with attack feasibility to determine Risk Levels (1 to 5).
   * Issues automated gating verdicts:
     * **`BLOCK`**: High/Severe risk regression (e.g., newly reachable ASIL-D target over unauthenticated hops). Fails CI/CD build.
     * **`FLAG`**: Moderate risk architectural modification requiring human review.
     * **`PASS`**: Safe release, zero unauthenticated attack routes.

---

## Part 2: Quick Explanation of the 13 Real-Time Scenarios

| # | Scenario Name | Real-World Attack / Incident Context | What Happens in ARXML & Verdict |
| :---: | :--- | :--- | :--- |
| **01** | **Jeep Uconnect (2015)** | Miller & Valasek Black Hat exploit (1.4M recall). Cellular access to head unit abused to reflash the V850 chip and control steering/brakes over CAN. | An unauthenticated head-unit-to-bridge hop is added, establishing a direct multi-hop path from cellular to steering. $\to$ **BLOCK** |
| **02** | **BMW ConnectedDrive (2018)** | Tencent Keen Lab exploit. Remote code execution on the Telematics Control Unit (TCU) bypassed the Central Gateway to send UDS diagnostic commands to chassis ECUs. | Added unauthenticated UDS passthrough across the Central Gateway down to chassis actuators. $\to$ **BLOCK** |
| **03** | **Tesla 2016 OTA Fix** | Control / benign test case. Tesla pushed an over-the-air update enforcing cryptographic code-signing on the Gateway to prevent tampering. | Connectors and components are added with full cryptographic protection in place; no unauthenticated routes created. $\to$ **PASS** |
| **04** | **Mitsubishi Outlander (2016)** | Wi-Fi module had a weak pre-shared key (PSK) letting attackers disable theft alarms. The fix migrated control to an encrypted GSM cellular module. | Replaces the local Wi-Fi link with a cellular link, modifying the attack surface without directly introducing an unauthenticated safety breach. $\to$ **FLAG** |
| **05** | **FCA Network Fix (2015)** | Control / fix case. Sprint and Chrysler blocked cellular port 6667 at the network level, severing the path to the head unit. | The unauthenticated wireless entry link is severed/re-fenced; critical nodes are unreachable. $\to$ **PASS** |
| **06** | **Curry Nissan API (2023)** | Sam Curry disclosure. Vulnerability in telematics backend API permitted unauthorized HTTP commands to trigger vehicle ignition. | Telematics API is granted an unauthenticated connection to the powertrain ignition controller. $\to$ **BLOCK** |
| **07** | **Spireon Fleet Admin (2023)** | Misconfigured fleet administration portal allowed unauthorized remote vehicle disablement / starter interruption across fleets. | Entry point at the fleet portal establishes an unauthenticated path to the engine starter. $\to$ **BLOCK** |
| **08** | **SOME/IP De-association (2021)** | Academic attack (Zelle et al.). Exploited unauthenticated SOME/IP Service Discovery (SD) to spoof services and hijack Ethernet communication. | Service-oriented hop is added without authentication, enabling service spoofing between provider and consumer. $\to$ **BLOCK** |
| **09** | **Supply Chain SDK Backdoor** | Third-party navigation/media SDK added during a software update contained hidden debug backdoors communicating with the body control bus. | The SDK component introduces an unauthenticated bridge from the infotainment domain into the body/door locks. $\to$ **BLOCK** |
| **10** | **Kia Telematics API (2024)** | Researchers proved that querying dealer web APIs allowed remote vehicle unlocking, tracking, and honking using only the license plate. | Web portal endpoint reaches door lock and body control actuators over an unauthenticated route. $\to$ **BLOCK** |
| **11** | **Toyota CAN Injection (2023)** | Thieves accessed CAN wiring behind the front headlight bumper to inject fake "smart key verified" frames and steal Lexus/Toyota vehicles. | An externally accessible physical node (`headlight`) injects unauthenticated frames directly into the immobilizer (`immob`). $\to$ **BLOCK** |
| **12** | **SecOC Weak MAC (FM-1)** | Parameter downgrade boundary test. SecOC is present, but configured with an insecurely short MAC (truncation flaw). | The connector is authenticated with a valid SecOC wrapper; basic topological checks pass cleanly, highlighting where graph diffing hands off to cryptographic policy checks. $\to$ **PASS** |
| **13** | **Unannotated Boundary (FM-4)** | Heuristic stress test. Component names are obfuscated / non-standard, without explicit ASIL metadata in the ARXML. | Name matching heuristics successfully identify the safety-critical motion actuator and detect the newly opened attack path. $\to$ **BLOCK** |

---

## Part 3: 30-Second Panel Pitch

> *"Our project automates cybersecurity regression testing for connected vehicles during software updates. Instead of treating AUTOSAR XML as static text, our tool constructs semantic data-flow graphs of the release snapshots. It applies constrained graph reachability analysis to verify whether a software change inadvertently exposes safety-critical actuators (like steering or brakes at ASIL-D) to untrusted wireless entry points (such as telematics or infotainment) across unauthenticated bus hops. If an unauthenticated route is introduced, our ISO/SAE 21434 risk engine automatically generates a **BLOCK** verdict to prevent cyber-physical safety incidents before firmware is deployed."*
