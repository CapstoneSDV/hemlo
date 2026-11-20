# ARXML SecDiff — Teammate Setup & Runbook

This runbook provides complete, step-by-step instructions to clone, configure, and run the **ARXML SecDiff** cybersecurity release gate and interactive Web GUI on your local laptop.

---

## 1. System Prerequisites

Ensure you have the following installed on your machine:

| Requirement | Supported Version | Check Command | Download Link |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10, 3.11, or 3.12 | `python --version` | [python.org](https://www.python.org/downloads/) |
| **Node.js** | v18.x or v20+ LTS | `node --version` | [nodejs.org](https://nodejs.org/) |
| **pnpm** | v9+ or v12+ | `pnpm --version` | `npm install -g pnpm` |
| **Git** | Any modern version | `git --version` | [git-scm.com](https://git-scm.com/) |

> **Windows Users Note:** When installing Python, make sure to check the box **"Add Python to PATH"**.

---

## 2. Clone the Repository

Open your terminal (PowerShell, Command Prompt, or Bash) and clone the repository:

```bash
git clone https://github.com/CapstoneSDV/hemlo.git
cd hemlo
```

---

## 3. Python Backend Environment Setup

From the repository root directory (`hemlo/`):

### Option A: Using a Virtual Environment (Recommended)

```bash
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate the virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Windows (cmd.exe):
.\.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate

# 3. Upgrade pip and install Python dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Install editable project package
pip install -e .
```

### Quick Dependency Verification
Verify that the core libraries are installed properly:
```bash
python -c "import lxml, networkx, yaml; print('Python backend dependencies OK!')"
```

---

## 4. Frontend Web GUI Setup

The interactive 5-stage visualization interface is built with **Next.js 16**, **React Flow (`@xyflow/react`)**, and **shadcn/ui**.

```bash
# Navigate to the Next.js app directory
cd web_gui/next-app

# Install all frontend dependencies
pnpm install

# Return to root
cd ../..
```

---

## 5. How to Run the Project

You can run ARXML SecDiff in two ways: via the **Interactive Web GUI** or via the **Command-Line Interface (CLI)**.

---

### Option 1: Running the Interactive Web GUI (Recommended for Demos)

1. Set your terminal's environment path and launch the Next.js dev server:

**Windows (PowerShell):**
```powershell
cd web_gui/next-app
$env:PYTHON_PATH = (Get-Command python).Source
pnpm dev --port 3000
```

**Linux / macOS (Bash / Zsh):**
```bash
cd web_gui/next-app
export PYTHON_PATH=$(which python)
pnpm dev --port 3000
```

2. Open your web browser and navigate to:
👉 **[http://localhost:3000](http://localhost:3000)**

#### What You Can Do in the Web GUI:
* **Scenario Dropdown**: Select any of the **13 real-world CVE automotive benchmark scenarios** (e.g., Jeep Cherokee Uconnect remote exploit, BMW ConnectedDrive TCU diagnostic bypass, Toyota CAN injection, Tesla OTA signing fix).
* **Browse Local Files**: Click **"Browse Local Files"** to upload your own pair of `before.arxml` and `after.arxml` files.
* **5-Stage Bidirectional Stepper**:
  * **Stage 1**: Parse & AST Indexing (component prototypes, bus interfaces, ECU mappings).
  * **Stage 2**: Graph Construction (interactive React Flow topological canvas with **Fullscreen**, **Zoom Controls**, and **Horizontal/Vertical layout toggles**).
  * **Stage 3**: SecOC Wire Annotation (breakdown of `RTE_LOCAL`, `AUTHENTICATED`, and `UNPROTECTED` links).
  * **Stage 4**: Dual-Graph Diff & Attack Paths (visualizes newly opened transitive attack chains $\Delta R$).
  * **Stage 5**: ISO/SAE 21434 Gate Decision (displays the automated verdict: `PASS`, `FLAG`, or `BLOCK` with risk scores).

---

### Option 2: Running the CLI Pipeline

You can run individual scenario comparisons or execute the full test suite directly from your terminal.

#### A. Run a Single Scenario Security Diff
```bash
# Compare Jeep Uconnect before and after release
arxml-secdiff real_time_scenarios/01_jeep_uconnect/before.arxml real_time_scenarios/01_jeep_uconnect/after.arxml --roles real_time_scenarios/01_jeep_uconnect/roles.yaml

# Compare BMW ConnectedDrive scenario
arxml-secdiff real_time_scenarios/02_bmw_connecteddrive/before.arxml real_time_scenarios/02_bmw_connecteddrive/after.arxml --roles real_time_scenarios/02_bmw_connecteddrive/roles.yaml
```

#### B. Run the Automated Scenario Test Suite (All 13 Benchmark Scenarios)

Use `test_all_scenarios.py` to run the pipeline across all 13 automotive benchmark scenarios, compare verdicts against ground truth, and display formatted timings and findings:

```bash
# Run all 13 scenarios on the realistic enterprise dataset (default)
python test_all_scenarios.py

# Run across both original and realistic datasets
python test_all_scenarios.py --dataset all

# Export full benchmarking results and timings to a JSON report
python test_all_scenarios.py --json scenario_results.json
```

*(You can also run the legacy runner via `python real_time_scenarios/run_all_scenarios.py`)*

#### C. Run the Comprehensive Unit Test Suite
```bash
pytest -v
```
All unit tests in `tests/` validate AST parsing, multigraph construction, 3-valued SecOC classification, graph diffing, transitive DFS reachability, and release gate decision policies.

---

## 6. Project Directory Map

```text
hemlo/
├── arxml_secdiff/              # Core algorithmic pipeline engine
│   ├── parser.py               # Stage 1: ARXML DOM parsing & path indexing
│   ├── xmlutil.py              # Namespace stripping & deterministic XML loading
│   ├── model.py                # In-memory dataclasses (Prototypes, Ports, Connectors)
│   ├── ecu.py                  # Physical ECU instance mapping
│   ├── signals.py              # System signal & I-PDU mapping
│   ├── graph.py                # Stage 2: Directed Multigraph construction
│   ├── secoc.py                # Stage 3: 3-Valued SecOC wire annotation
│   ├── diff.py                 # Stage 4A: Dual-graph differential
│   ├── reach.py                # Stage 4B: Transitive DFS attack reachability
│   ├── severity.py             # Stage 5A: ISO/SAE 21434 Risk Matrix scoring
│   ├── gate.py                 # Stage 5B: Automated release gate verdict engine
│   └── findings.py             # Audit trail & structured findings generation
├── real_time_scenarios/        # 13 real-world CVE benchmark scenarios (original)
│   ├── 01_jeep_uconnect/       # Jeep remote exploit (2015)
│   ├── 02_bmw_connecteddrive/  # BMW TCU-to-gateway passthrough (2018)
│   ├── 03_tesla_2016_fix/      # Tesla OTA code-signing fix (control case)
│   └── ...                     # Additional OEM real-world benchmark cases
├── real_time_scenarios_realistic/# Enterprise AUTOSAR R20-11 validated benchmark dataset
├── web_gui/
│   └── next-app/               # Modern Next.js + React Flow + shadcn/ui Web GUI
│       ├── app/page.tsx        # 5-stage bidirectional stepper GUI
│       ├── components/
│       │   └── TopologyFlow.tsx# React Flow + Dagre topological architecture canvas
│       └── app/api/pipeline/   # API route executing backend Python pipeline
├── test_all_scenarios.py       # Automated runner for all 13 scenarios with validation & timings
├── RUNBOOK.md                  # This setup and runbook guide
└── PIPELINE_EXPLANATION.md     # 4-part deep-dive presentation guide for teammates
```

---

## 7. Troubleshooting Common Issues

### Issue 1: `python` or `pnpm` command not recognized in PowerShell
**Fix**: Ensure your shell environment knows where Node.js and Python are located:
```powershell
$env:Path = "C:\Program Files\nodejs;C:\Users\purus\AppData\Roaming\npm;C:\Users\purus\AppData\Local\Programs\Python\Python312;" + $env:Path
```

### Issue 2: `ModuleNotFoundError: No module named 'arxml_secdiff'`
**Fix**: Make sure you have installed the package in editable mode from the repository root:
```bash
pip install -e .
```

### Issue 3: Port 3000 is already in use
**Fix**: Start the Web GUI on an alternative port:
```bash
pnpm dev --port 3001
```
Then visit `http://localhost:3001`.
