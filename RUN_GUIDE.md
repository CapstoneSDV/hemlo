# AUTOSAR SecDiff – Run Guide

Complete setup instructions for anyone who has just cloned/pulled this repository
on a **fresh machine** and wants to run the full evaluation.

---

## ✅ Prerequisites (install once)

| Requirement | Minimum version | Check command |
|-------------|-----------------|---------------|
| Python | **3.10 or higher** | `python --version` |
| pip | bundled with Python | `pip --version` |
| Git | any recent version | `git --version` |

> **Windows users:** make sure Python is on your PATH (tick "Add Python to PATH"
> during installation, or add it manually).

---

## 1 – Clone / Pull the Repository

```bash
# Clone for the first time
git clone <your-repo-url>

# --- OR, if you already cloned it, just pull latest changes ---
git pull
```

Then enter the project folder:

```bash
cd hello_world-main
```

---

## 2 – Create a Virtual Environment

A virtual environment keeps project dependencies isolated from your system Python.

```bash
# Create the venv (only once per machine)
python -m venv venv
```

Activate it:

```bash
# Windows (PowerShell / CMD)
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

You should now see `(venv)` at the start of your terminal prompt.

---

## 3 – Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Install the arxml_secdiff package itself in editable/dev mode
pip install -e .
```

This installs:
- `lxml` – XML/ARXML parsing
- `networkx` – graph-based ECU reachability analysis
- `PyYAML` – roles/config parsing
- `matplotlib` + `seaborn` – figure generation
- `pytest` – unit testing

Verify the install succeeded:

```bash
pip list | grep -E "lxml|networkx|PyYAML|matplotlib|seaborn|pytest"
```

---

## 4 – (Optional) Verify the Setup Before Full Evaluation

Run the unit tests alone to confirm everything is installed correctly:

```bash
python -m pytest tests/ -v
```

Expected output: all tests **PASSED** (401 cases).

---

## 5 – Run the Full Evaluation

```bash
python run_full_evaluation.py
```

This single command runs **4 stages** automatically:

| Stage | What it does | Output location |
|-------|--------------|-----------------|
| **1. Unit Tests** | Runs 401 pytest cases | terminal |
| **2. CVE Scenarios** | Replicates + mutates ARXML for 11 real-world CVE scenarios | `scenario_runs/` |
| **3. Evaluation Corpus** | Runs ~300 auto-generated mutation cases | `docs/results.md`, `docs/results.json` |
| **4. IEEE Figures** | Generates publication-quality charts | `out/figures/` |

Total runtime: approximately **1–3 minutes** on a modern laptop.

---

## 6 – View the Results

| Result | Location |
|--------|----------|
| CVE scenario verdicts | `scenario_runs/RESULTS.md` |
| Full evaluation report (Markdown) | `docs/results.md` |
| Full evaluation metrics (JSON) | `docs/results.json` |
| IEEE figures (PNG/PDF) | `out/figures/` |

---

## Other Useful Commands

### Run only the 11 CVE scenarios
```bash
python run_scenarios.py
```

### Run only unit tests
```bash
python -m pytest tests/ -v
```

### Use the CLI tool directly
```bash
# Compare two ARXML snapshots
arxml-secdiff before.arxml after.arxml

# With a roles config file
arxml-secdiff before.arxml after.arxml --roles data/roles.yaml
```

### Launch the GUI
```bash
python gui.py
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `python` not found | Try `python3` instead; or re-install Python with "Add to PATH" ticked |
| `ModuleNotFoundError: lxml` | Virtual env not activated, or `pip install -r requirements.txt` not run |
| `ModuleNotFoundError: arxml_secdiff` | Run `pip install -e .` from the project root |
| `pytest: command not found` | Use `python -m pytest tests/` instead |
| Permission error on `venv\Scripts\activate` (Windows) | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` in PowerShell |

---

## Quick Copy-Paste Block (Windows PowerShell)

```powershell
git clone <your-repo-url>
cd hello_world-main
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
python run_full_evaluation.py
```

## Quick Copy-Paste Block (macOS / Linux)

```bash
git clone <your-repo-url>
cd hello_world-main
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
python run_full_evaluation.py
```

---

*Generated for AUTOSAR SecDiff – ARXML Security Regression Analysis Tool.*
