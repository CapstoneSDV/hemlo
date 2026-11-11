"""
Automated Generator & Runner for real_time_scenarios/
=====================================================
Builds the 'real_time_scenarios/' directory containing all 13 real-world scenarios
embedded into the 24-node / 8-ECU vehicle ARXML.
"""
import sys, os, copy, json, shutil
from pathlib import Path
from lxml import etree

ROOT = Path(r'D:\arxml-secdiff-main\graph_based_security_validation-main')
sys.path.insert(0, str(ROOT))

from arxml_secdiff import pipeline
from scenario_defs import SCENARIOS

BASE_ARXML_PATH = ROOT / 'large_vehicle_experiment' / 'full_vehicle_24node.arxml'
OUT_DIR = ROOT / 'real_time_scenarios'
OUT_DIR.mkdir(exist_ok=True)

# Copy base architecture into the target directory
shutil.copy2(BASE_ARXML_PATH, OUT_DIR / 'full_vehicle_base.arxml')

NS = 'http://autosar.org/schema/r4.0'

def merge_arxml(base_file, scenario_file, output_file):
    """Merge base 24-node ARXML and scenario ARXML into a single clean AUTOSAR XML document."""
    t_base = etree.parse(str(base_file))
    t_sc = etree.parse(str(scenario_file))
    
    root_base = t_base.getroot()
    pkgs_base = root_base.find(f'{{{NS}}}AR-PACKAGES')
    if pkgs_base is None:
        pkgs_base = root_base.find('AR-PACKAGES')
        
    pkgs_sc = t_sc.getroot().find(f'{{{NS}}}AR-PACKAGES')
    if pkgs_sc is None:
        pkgs_sc = t_sc.getroot().find('AR-PACKAGES')
        
    for p in pkgs_sc:
        pkgs_base.append(copy.deepcopy(p))
        
    t_base.write(str(output_file), encoding='utf-8', xml_declaration=True, pretty_print=True)

def build_and_run_all():
    summary_report = []
    
    for sc in SCENARIOS:
        sc_id = sc.id
        sc_src_dir = ROOT / 'scenario_runs' / sc_id
        sc_target_dir = OUT_DIR / sc_id
        sc_target_dir.mkdir(exist_ok=True)
        
        # 1. Merge before and after with the 24-node base ARXML
        before_merged = sc_target_dir / 'before.arxml'
        after_merged = sc_target_dir / 'after.arxml'
        
        merge_arxml(BASE_ARXML_PATH, sc_src_dir / 'before.arxml', before_merged)
        merge_arxml(BASE_ARXML_PATH, sc_src_dir / 'after.arxml', after_merged)
        
        # 2. Copy and adapt roles.yaml and NOTES.md
        shutil.copy2(sc_src_dir / 'roles.yaml', sc_target_dir / 'roles.yaml')
        shutil.copy2(sc_src_dir / 'NOTES.md', sc_target_dir / 'NOTES.md')
        
        # 3. Execute pipeline on the merged 26-28 node vehicle architecture
        res = pipeline.run(
            before_sources=[str(before_merged)],
            updated_sources=[str(after_merged)],
            roles_config=str(sc_target_dir / 'roles.yaml')
        )
        
        # 4. Generate cli_output.json
        cli_output_data = {
            "scenario": sc_id,
            "title": sc.title,
            "verdict": res.verdict,
            "exit_code": res.exit_code,
            "total_nodes": res.updated.graph.number_of_nodes(),
            "total_edges": res.updated.graph.number_of_edges(),
            "findings_count": len(res.findings),
            "findings": [
                {
                    "category": f.category,
                    "title": f.title,
                    "detail": f.detail,
                    "risk": s.risk,
                    "impact": s.score.impact,
                    "feasibility": s.score.feasibility
                }
                for f, s in zip(res.findings, res.scored)
            ],
            "expected_verdict": sc.expected_after
        }
        
        with open(sc_target_dir / 'cli_output.json', 'w', encoding='utf-8') as f:
            json.dump(cli_output_data, f, indent=2)
            
        summary_report.append({
            "id": sc_id,
            "title": sc.title,
            "nodes": res.updated.graph.number_of_nodes(),
            "edges": res.updated.graph.number_of_edges(),
            "findings": len(res.findings),
            "verdict": res.verdict,
            "expected": sc.expected_after,
            "match": res.verdict == sc.expected_after
        })
        
        print(f"[{sc_id}] Nodes: {res.updated.graph.number_of_nodes()} | Findings: {len(res.findings)} | Verdict: {res.verdict} (Expected: {sc.expected_after})")
        
    print("\n" + "="*80)
    print(f"{'Scenario ID':<32} {'Nodes':>5} {'Findings':>8} {'Verdict':>8} {'Expected':>8} {'Status':>8}")
    print("="*80)
    for r in summary_report:
        status = "MATCH" if r['match'] else "MISMATCH"
        print(f"{r['id']:<32} {r['nodes']:>5} {r['findings']:>8} {r['verdict']:>8} {r['expected']:>8} {status:>8}")
    print("="*80)

if __name__ == '__main__':
    build_and_run_all()
