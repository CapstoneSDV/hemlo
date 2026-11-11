"""
Run All Scenarios in real_time_scenarios/
=========================================
Standalone runner to execute arxml-secdiff pipeline across all scenarios
embedded into the full vehicle architecture.
"""
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from arxml_secdiff import pipeline

SCENARIOS_DIR = Path(__file__).resolve().parent

def run_all():
    summary = []
    for sdir in sorted(SCENARIOS_DIR.iterdir()):
        if not sdir.is_dir():
            continue
        bef = sdir / 'before.arxml'
        aft = sdir / 'after.arxml'
        roles = sdir / 'roles.yaml'
        if not (bef.exists() and aft.exists()):
            continue
            
        res = pipeline.run(
            before_sources=[str(bef)],
            updated_sources=[str(aft)],
            roles_config=str(roles) if roles.exists() else None
        )
        summary.append({
            "scenario": sdir.name,
            "nodes": res.updated.graph.number_of_nodes(),
            "findings": len(res.findings),
            "verdict": res.verdict
        })
        print(f"[{sdir.name}] Nodes: {res.updated.graph.number_of_nodes()} | Findings: {len(res.findings)} | Verdict: {res.verdict}")

    print("\n" + "="*65)
    print(f"{'Scenario':<32} {'Nodes':>6} {'Findings':>10} {'Verdict':>10}")
    print("="*65)
    for r in summary:
        print(f"{r['scenario']:<32} {r['nodes']:>6} {r['findings']:>10} {r['verdict']:>10}")
    print("="*65)

if __name__ == '__main__':
    run_all()
