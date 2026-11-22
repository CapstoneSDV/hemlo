# Part 4 Master Study Guide: ISO/SAE 21434 Risk Scoring & 4-Verdict Release Gate

**Assigned Presenter:** Presenter 4 (Cybersecurity Decision Engineering & Standards Compliance)  
**Modules Owned:** `arxml_secdiff/severity.py`, `arxml_secdiff/gate.py`, `arxml_secdiff/findings.py`  
**Relevant Paper Sections:** Section 4.4 (*Provenance-Aware Risk Scoring*), Section 4.5 (*The Four-Verdict Release Gate*), Section 5.4 (*External Scorer and Reporting*)

---

## 1. Paper Jargon Decoded: Plain-English Translation

When reading the research paper (`sections_4_5.tex`), several dense academic terms are used. Here is what they actually mean in plain English:

| Research Paper Term | Academic Definition in Paper | Plain-English Software Reality | Why It Is Brilliant (Defense Point) |
| :--- | :--- | :--- | :--- |
| **"Provenance-Aware Risk Scoring"** | Tracking the origin and evidence chain of every calculated risk value. | The tool doesn't just output a number like `Risk: 5`. It records **how** that 5 was computed, what formulas were used, and whether the input was a fact or a guess. | If a judge asks *"Why did your tool block this release?"*, you can show the exact mathematical trail rather than a black-box score. |
| **"Assumed Input Tainting"** (`Score.assumed = True`) | Marking a score as derived from heuristics rather than verified ground truth. | If the tool identified a component as a brake because its name had the letters `"brake"` (heuristic guess) rather than from an official signed TARA file, it taints the score with `assumed = True`. | **Prevents developer revolt.** A tool that blocks a release based on a name guess gets turned off by engineers. We downgrade assumed risks to `FLAG` by default. |
| **"Downstream Impact Inheritance"** | Intermediate hops in an attack path borrowing the highest impact of any reachable safety target. | An unencrypted wire between a Modem and a Central Gateway seems minor (a Gateway is not an actuator). But because that Gateway connects directly to the Brakes, the Modem-to-Gateway wire **inherits the severe ASIL-D impact of the Brakes**! | Stops attackers from exploiting intermediate non-critical ECUs to reach critical actuators. |
| **"Absence of Evidence $\ne$ Evidence of Absence"** | A clean scan does not imply safety if the analysis failed to run. | If an engineer forgets to provide a `roles.yaml` file, the search finds 0 attack paths. A naive tool says `PASS`. Our tool says **`INCONCLUSIVE`** because no search was actually possible. | Prevents releasing an unconfigured, untested car into production. |
| **"Unwaivable Findings"** | Security violations that no human manager or policy waiver is allowed to suppress. | You can waive a known low-risk finding, but you **cannot waive** `NOT_ANALYSED`. You cannot tell CI/CD: *"Ignore the fact that we didn't run the security test."* | Enforces regulatory compliance under UN ECE R155. |
| **"External Scorer Seam"** (`ExternalScorer`) | A decoupled IPC interface over JSON stdin/stdout. | If an OEM (like BMW or Ford) has their own proprietary risk calculator (e.g., VERA or corporate TARA tool), they don't have to rewrite our code. They just plug in a small script. | Makes the tool enterprise-ready and vendor-agnostic. |

---

## 2. Core Technical Deep-Dive

### A. The 2-Dimensional Risk Matrix (ISO/SAE 21434 Annex H)

In ISO/SAE 21434, Cybersecurity Risk is defined as:
$$\text{Risk Level} \in \{1, 2, 3, 4, 5\} = M(\text{Impact}, \text{Feasibility})$$

Implemented in `arxml_secdiff/severity.py`:

```
               FEASIBILITY (Ease of Exploitation)
IMPACT         Very-Low    Low      Medium    High
─────────────────────────────────────────────────
Severe (ASIL-D)   2         3         4        5   <-- BLOCK THRESHOLD
Major  (ASIL-C)   1         2         3        4   <-- FLAG THRESHOLD
Moderate(ASIL-B/A)1         2         2        3
Negligible (QM)   1         1         1        1
```

#### 1. How Impact is Derived:
* **ASIL-D Actuators** (Brakes, Steering, Powertrain) $\rightarrow$ **`severe`**
* **ASIL-C Actuators** (Suspension, Radar/Vision Safety) $\rightarrow$ **`major`**
* **ASIL-B / ASIL-A** (Airbags, Body Domain, Lighting) $\rightarrow$ **`moderate`**
* **QM (Quality Management / Non-Safety)** (Infotainment, Radio) $\rightarrow$ **`negligible`**
* *Unannotated safety targets default to `major` so they are never quietly ignored.*

#### 2. How Attack Feasibility is Derived:
Feasibility evaluates how much effort and hardware an attacker needs:
* **`high` Feasibility**: Communication traverses an unauthenticated physical bus wire (CAN, CAN-FD, Automotive Ethernet) with no SecOC. An attacker with a $20 OBD dongle or clipped CAN wire can inject frames.
* **`medium` Feasibility**: Partially exposed bus with gateway filtering.
* **`low` Feasibility**: Protected by AUTOSAR SecOC cryptographic MAC and Freshness Value Management (FVM). Attacker needs the AES-128 secret key.
* **`very-low` Feasibility**: `RTE_LOCAL` internal ECU memory copy. Attacker needs physical chip decapping or kernel root.
* **Remote Surface Boost**: If the path originates from a wireless interface (Cellular 4G/5G, Wi-Fi, Bluetooth), feasibility is automatically incremented by +1 level up to `high`.

---

### B. Downstream Impact Inheritance (The Gateway Problem)

**The Flaw in Naive Tools:**
Suppose an attacker compromises the Cellular Telematics Unit (`TCU`). The `TCU` talks to the `Central Gateway (CGW)`. The `CGW` talks to the `Electronic Stability Control (ESC / Brakes)`.
* If you evaluate the `TCU -> CGW` wire in isolation: the `CGW` is just a router (QM rating, negligible impact).
* A naive tool would score `TCU -> CGW` as **Risk 1 (Negligible)**!

**How ARXML SecDiff Solves It (`severity.py:BuiltinScorer`):**
1. When evaluating any intermediate edge, the scorer inspects the entire reachable path downstream in graph $G_{\text{after}}$.
2. It discovers that downstream of `CGW` lies `ESC` (rated **ASIL-D**).
3. The `TCU -> CGW` edge **inherits the `severe` impact rating** from the downstream brake target!
4. The rationale explicitly states: `"borrowed severe impact from downstream target /V/Swc/Actuators/Brake"`.

---

### C. The Four-Verdict Release Gate (`gate.py`)

Why are 3 verdicts (`PASS`, `FLAG`, `BLOCK`) insufficient?

```
                     +---------------------------------------+
                     |         Scored Findings List          |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     | 1. Filter Accepted (Waived) Findings  |
                     |    (Refuse UNWAIVABLE: NOT_ANALYSED)  |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     | 2. Set Aside Informational Findings   |
                     |    (e.g., pure component additions)   |
                     +---------------------------------------+
                                         |
                                         v
                         /-------------------------------\
                        /  Any non-assumed finding with   \  YES
                       <      Risk >= 5 (Block At)?        >-----> [ BLOCK (Exit 3) ]
                        \                                 /
                         \-------------------------------/
                                         | NO
                                         v
                         /-------------------------------\
                        /     Did analysis fail to run    \  YES
                       <    (Category == NOT_ANALYSED)?   >-----> [ INCONCLUSIVE (Exit 2) ]
                        \                                 /
                         \-------------------------------/
                                         | NO
                                         v
                         /-------------------------------\
                        /     Any finding with Risk >= 3  \  YES
                       <        OR downgraded assumed?    >-----> [ FLAG (Exit 1) ]
                        \                                 /
                         \-------------------------------/
                                         | NO
                                         v
                                 [ PASS (Exit 0) ]
```

#### Precedence Order:
$$\text{BLOCK (3)} > \text{INCONCLUSIVE (2)} > \text{FLAG (1)} > \text{PASS (0)}$$

* **Why `BLOCK` outranks `INCONCLUSIVE`**: If we already found a verified unauthenticated attack path to the steering wheel, that is an immediate critical emergency. We must BLOCK the release immediately, even if some other subsystem was missing role configurations!
* **Why `INCONCLUSIVE` outranks `FLAG` and `PASS`**: If you didn't configure your roles, you cannot claim your car is safe. A missing test can never yield a `PASS`.

---

## 3. Step-by-Step Presentation Script for Presenter 4

When it is your turn to speak, follow this exact talk track:

### Slide 1: Moving from Graph Analysis to Automated Release Decision
> *"Thank you, Presenter 3. My teammates have shown how we parse AUTOSAR XML, build the system multigraph, and compute newly opened attack paths $\Delta R$.*  
> *My role is to turn these complex graph paths into a deterministic, automated release decision: **Can this automotive software release safely ship to production or not?**"*

### Slide 2: The ISO/SAE 21434 Risk Engine (`severity.py`)
> *"We do not use arbitrary numbers or vague risk guesses. We implemented the standardized **ISO/SAE 21434 Annex H 2D Risk Matrix**.*  
> *Every finding is mapped to two orthogonal axes:*  
> 1. *First, **Safety Impact**: Derived directly from ISO 26262 Automotive Safety Integrity Levels (ASIL). ASIL-D actuators like Steering and Braking are rated **Severe**; non-safety QM components are **Negligible**.*  
> 2. *Second, **Attack Feasibility**: Evaluated based on physical bus access. An unauthenticated CAN-FD bus has **High Feasibility** because an attacker with a $20 OBD tool can inject frames. If SecOC encryption is added, feasibility drops to **Low**.*  
> *Combining Impact and Feasibility yields a standardized Risk Score from 1 to 5."*

### Slide 3: Two Algorithmic Innovations in Scoring
> *"We introduced two critical innovations in `severity.py`:*  
> *First, **Downstream Impact Inheritance**: An unencrypted wire between a Telematics modem and a Central Gateway might look harmless in isolation. But our scorer traverses downstream, sees that the Gateway can command the Brakes, and elevates the intermediate wire to **Severe Impact**.*  
> *Second, **Assumed Input Tainting**: In continuous integration, false alarms kill tools. If an asset was classified as critical based on a regex name guess rather than an official TARA file, we taint the score with `assumed=True`. By default, assumed findings are downgraded from `BLOCK` to `FLAG`. This prevents blocking factory builds on a guess while still requiring human verification."*

### Slide 4: The 4-Verdict Release Gate (`gate.py`)
> *"Finally, in `gate.py`, we apply our decision policy. Most industry tools only have three verdicts: Pass, Warning, and Fail. **We proved that three verdicts are mathematically insufficient.***  
> *If an engineer forgets to provide security roles, a 3-verdict tool finds zero paths and returns a false `PASS`. This is a catastrophic failure mode.*  
> *We introduced **`INCONCLUSIVE` (Exit Code 2)**. If the analysis could not run, the gate returns Inconclusive. Under our policy, **`NOT_ANALYSED` is unwaivable**—no human is allowed to sign a waiver ignoring an unexecuted security analysis.*  
> *The result is a clean, automated gate for GitHub Actions or GitLab CI that returns:  
> - `BLOCK` (Exit 3): Critical risk $\ge 5$ found.  
> - `INCONCLUSIVE` (Exit 2): Incomplete evaluation.  
> - `FLAG` (Exit 1): Human triage required.  
> - `PASS` (Exit 0): Mathematically verified clean release."*

---

## 4. Brutal Examiner Q&A Specifically for Part 4

#### Q1: "Why did you use ASIL ratings for Impact instead of the ISO/SAE 21434 Damage Scenarios (Safety, Financial, Operational, Privacy)?"
**The Brutal Angle:** ISO 21434 defines SFOP (Safety, Financial, Operational, Privacy). Why did you only focus on safety ASIL?  
**Bulletproof Defense:**  
> *"In theoretical TARA workshops, analysts evaluate all four SFOP dimensions. However, in automotive software engineering, what development teams **actually have machine-readable in component manifests** is the ASIL allocation from the ISO 26262 safety case.  
> Furthermore, in connected vehicles, safety impact strictly dominates all other factors—a remote steering compromise is life-threatening.  
> However, we did not hardcode this limitation: we built the `ExternalScorer` seam. If an OEM wants to evaluate financial or privacy impacts using their enterprise TARA tool (like VERA or Ansys medini), they can plug it directly into our JSON interface without modifying a single line of our pipeline code."*

#### Q2: "What prevents a lazy developer from simply adding all finding IDs to the `accepted` waiver list in `policy.yaml` to force a `PASS`?"
**The Brutal Angle:** Can developers cheat the gate?  
**Bulletproof Defense:**  
> *"Two technical mechanisms prevent this:  
> 1. **Unwaivable Categories (`UNWAIVABLE`)**: The category `NOT_ANALYSED` is hardcoded as an immutable frozenset. If a developer attempts to add `not-analysed` to the accepted list, `gate.py` detects it, logs a `refused_acceptance`, and preserves the `INCONCLUSIVE` verdict.  
> 2. **Stale Waiver Tracking**: In `Decision.stale_acceptances`, the tool reports any waiver whose corresponding finding is no longer present in the architecture. This forces security architects to audit and retire obsolete waivers during pull request code reviews."*

#### Q3: "What if a company doesn't agree with your 5-point risk matrix?"
**The Brutal Angle:** Every carmaker has their own corporate risk guidelines.  
**Bulletproof Defense:**  
> *"Our architecture is fully decoupled via Python `Protocol` interfaces:  
> - `Policy` is loaded dynamically from YAML (`block_at`, `flag_at`, `block_on_assumed`).  
> - If an OEM uses a 4-level or 7-level risk matrix, they instantiate an `ExternalScorer` or subclass `Scorer`. The gate logic is completely independent of the scoring engine."*

#### Q4: "Why does `BLOCK` have higher precedence than `INCONCLUSIVE`?"
**The Brutal Angle:** If the analysis didn't finish, how can you make a decision?  
**Bulletproof Defense:**  
> *"Precedence is `BLOCK` > `INCONCLUSIVE` > `FLAG` > `PASS`.  
> If an architecture has 10 subsystems, and Subsystem 10 was missing configuration (yielding inconclusive), BUT Subsystem 1 had a confirmed, unencrypted remote cellular route to the Electronic Brakes, that release **must be stopped immediately**. A confirmed critical vulnerability is immediately actionable regardless of incomplete data elsewhere."*

---

## 5. Part 4 Quick Reference Formula Sheet

```
+-----------------------------------------------------------------------------------+
|                           PART 4 FORMULA & LOGIC SHEET                            |
+-----------------------------------------------------------------------------------+
| 1. RISK FORMULA:                                                                  |
|    Risk = RISK_MATRIX[(Impact, Feasibility)] in {1, 2, 3, 4, 5}                   |
|                                                                                   |
| 2. IMPACT MAPPING:                                                                |
|    ASIL-D -> severe | ASIL-C -> major | ASIL-B/A -> moderate | QM -> negligible   |
|                                                                                   |
| 3. FEASIBILITY MAPPING:                                                           |
|    Physical wire (Unprotected) = high | SecOC protected = low | RTE_LOCAL = v-low |
|    Remote surface (Cellular/Wi-Fi/BT) = +1 Feasibility level                      |
|                                                                                   |
| 4. VERDICT THRESHOLDS (Default Policy):                                           |
|    Risk >= 5 (and not assumed) -> BLOCK        (Exit Code 3)                      |
|    Unanalysed / Missing Roles   -> INCONCLUSIVE (Exit Code 2)                      |
|    Risk >= 3 (or assumed)      -> FLAG         (Exit Code 1)                      |
|    Clean analysis               -> PASS         (Exit Code 0)                      |
|                                                                                   |
| 5. PRECEDENCE:                                                                    |
|    BLOCK > INCONCLUSIVE > FLAG > PASS                                             |
+-----------------------------------------------------------------------------------+
```
