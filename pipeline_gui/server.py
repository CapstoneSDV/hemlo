"""
Backend API Server for Pipeline Stepper GUI
===========================================
Exposes intermediate pipeline stages for step-by-step bidirectional inspection:
  Stage 1: ARXML Parsing & Model Indexing
  Stage 2: Multigraph Construction (G_before, G_after)
  Stage 3: 3-Valued SecOC Wire Annotation
  Stage 4: Dual-Graph Diff & Transitive Attack Reachability
  Stage 5: ISO/SAE 21434 Risk Matrix Scoring & Gate Decision
"""
import sys, os, json, http.server, socketserver, urllib.parse, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from arxml_secdiff import parser, graph, secoc, diff, reach, roles, severity, gate, findings

PORT = 8080
SCENARIOS_DIR = ROOT / 'real_time_scenarios'
UPLOAD_DIR = Path(tempfile.gettempdir()) / 'arxml_secdiff_uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

def list_scenarios():
    scenarios = []
    if SCENARIOS_DIR.exists():
        for d in sorted(SCENARIOS_DIR.iterdir()):
            if d.is_dir() and (d / 'before.arxml').exists():
                notes_file = d / 'NOTES.md'
                title = d.name
                if notes_file.exists():
                    lines = notes_file.read_text(encoding='utf-8', errors='ignore').splitlines()
                    for line in lines:
                        if line.strip().startswith('#'):
                            title = line.strip('#').strip()
                            break
                scenarios.append({
                    "id": d.name,
                    "title": title,
                    "path": str(d)
                })
    return scenarios

def run_pipeline_paths(bef_path, aft_path, roles_path=None):
    # --- STAGE 1: PARSE ---
    m_bef = parser.parse([str(bef_path)])
    m_aft = parser.parse([str(aft_path)])

    stage1 = {
        "before": {
            "component_types": len(m_bef.component_types),
            "prototypes": len(m_bef.prototypes),
            "assembly_connectors": len(m_bef.assembly_connectors),
            "ecus": len(m_bef.ecus),
            "interfaces": len(m_bef.interfaces),
            "pdus": len(m_bef.pdus),
            "system_signals": len(m_bef.system_signals),
            "unresolved_refs": len(m_bef.unresolved_refs),
            "prototype_list": [
                {"path": p, "short_name": proto.short_name, "type_ref": proto.type_ref, "ecu": m_bef.swc_to_ecu.get(p, "Unmapped")}
                for p, proto in sorted(m_bef.prototypes.items())
            ],
            "ecu_list": list(m_bef.ecus.keys())
        },
        "updated": {
            "component_types": len(m_aft.component_types),
            "prototypes": len(m_aft.prototypes),
            "assembly_connectors": len(m_aft.assembly_connectors),
            "ecus": len(m_aft.ecus),
            "interfaces": len(m_aft.interfaces),
            "pdus": len(m_aft.pdus),
            "system_signals": len(m_aft.system_signals),
            "unresolved_refs": len(m_aft.unresolved_refs),
            "prototype_list": [
                {"path": p, "short_name": proto.short_name, "type_ref": proto.type_ref, "ecu": m_aft.swc_to_ecu.get(p, "Unmapped")}
                for p, proto in sorted(m_aft.prototypes.items())
            ],
            "ecu_list": list(m_aft.ecus.keys())
        }
    }

    # --- STAGE 2: BUILD GRAPH ---
    g_bef = graph.build(m_bef)
    g_aft = graph.build(m_aft)

    def serialize_raw_graph(g, model):
        nodes = []
        for n, d in g.nodes(data=True):
            ecu = model.swc_to_ecu.get(n, "UnknownECU")
            short_name = n.split('/')[-1]
            nodes.append({
                "id": n,
                "label": short_name,
                "ecu": ecu.split('/')[-1] if ecu else "UnknownECU",
                "kind": d.get("kind", "SWC")
            })
        edges = []
        for u, v, k, d in g.edges(keys=True, data=True):
            edges.append({
                "source": u,
                "target": v,
                "key": k,
                "connector": d.get("connector", k).split('/')[-1],
                "influence": d.get("influence", "data")
            })
        return {"nodes": nodes, "edges": edges, "nodes_count": len(nodes), "edges_count": len(edges)}

    stage2 = {
        "before": serialize_raw_graph(g_bef, m_bef),
        "updated": serialize_raw_graph(g_aft, m_aft)
    }

    # --- STAGE 3: SECOC ANNOTATE ---
    p_bef = secoc.profiles(m_bef)
    p_aft = secoc.profiles(m_aft)
    g_bef_ann = secoc.annotate(g_bef, m_bef, p_bef)
    g_aft_ann = secoc.annotate(g_aft, m_aft, p_aft)

    def serialize_annotated_graph(g, model, profiles_map):
        nodes = []
        for n, d in g.nodes(data=True):
            ecu = model.swc_to_ecu.get(n, "UnknownECU")
            nodes.append({
                "id": n,
                "label": n.split('/')[-1],
                "ecu": ecu.split('/')[-1] if ecu else "UnknownECU"
            })
        edges = []
        for u, v, k, d in g.edges(keys=True, data=True):
            auth = d.get("authenticated")
            state = "RTE_LOCAL" if auth is None else ("AUTHENTICATED" if auth is True else "UNPROTECTED")
            pdus = list(d.get("pdus", ()))
            unprot = list(d.get("unprotected_pdus", ()))
            edges.append({
                "source": u,
                "target": v,
                "key": k,
                "connector": d.get("connector", k).split('/')[-1],
                "bus_visible": bool(d.get("bus_visible", False)),
                "authenticated": auth,
                "security_state": state,
                "pdus": [p.split('/')[-1] for p in pdus],
                "unprotected_pdus": [p.split('/')[-1] for p in unprot],
                "secoc_source": d.get("secoc_source")
            })
        return {
            "nodes": nodes,
            "edges": edges,
            "unprotected_count": sum(1 for e in edges if e["security_state"] == "UNPROTECTED"),
            "authenticated_count": sum(1 for e in edges if e["security_state"] == "AUTHENTICATED"),
            "local_count": sum(1 for e in edges if e["security_state"] == "RTE_LOCAL")
        }

    stage3 = {
        "before": serialize_annotated_graph(g_bef_ann, m_bef, p_bef),
        "updated": serialize_annotated_graph(g_aft_ann, m_aft, p_aft)
    }

    # --- STAGE 4: DIFF & REACHABILITY ---
    roles_cfg = roles.classify(g_aft_ann, str(roles_path) if (roles_path and Path(roles_path).exists()) else None)
    r_bef = reach.analyse(g_bef_ann, roles_cfg)
    r_aft = reach.analyse(g_aft_ann, roles_cfg)
    str_diff = diff.compare(g_bef_ann, g_aft_ann)
    secoc_diff = diff.compare_secoc(m_bef, m_aft)
    r_diff = reach.compare(r_bef, r_aft)

    new_paths = []
    attack_edges_set = set()
    for pc in r_diff.newly_reachable:
        path = pc.path
        hop_details = []
        for h in path.hops:
            attack_edges_set.add((h.source, h.target))
            hop_details.append({
                "source": h.source.split('/')[-1],
                "target": h.target.split('/')[-1],
                "key": h.key.split('/')[-1],
                "bus_visible": h.bus_visible,
                "authenticated": h.authenticated
            })
        new_paths.append({
            "nodes": [n.split('/')[-1] for n in path.nodes],
            "raw_nodes": list(path.nodes),
            "hops": hop_details,
            "unprotected": any(h.authenticated is False for h in path.hops)
        })

    # Attach entry/critical tags and on_attack_path to stage2/3 graph nodes & edges
    entry_set = set(roles_cfg.entry)
    critical_set = set(roles_cfg.critical)

    for g_dict in (stage2["updated"], stage3["updated"]):
        for n in g_dict["nodes"]:
            if n["id"] in entry_set:
                n["role"] = "entry"
            elif n["id"] in critical_set:
                n["role"] = "critical"
                n["asil"] = roles_cfg.asil_of(n["id"]) or "D"
            else:
                n["role"] = "standard"
        for e in g_dict["edges"]:
            e["on_attack_path"] = (e["source"], e["target"]) in attack_edges_set

    stage4 = {
        "roles": {
            "entry_points": [{"node": n, "label": n.split('/')[-1]} for n in sorted(roles_cfg.entry)],
            "critical_targets": [{"node": n, "label": n.split('/')[-1], "asil": roles_cfg.asil_of(n) or "D"} for n in sorted(roles_cfg.critical)]
        },
        "structural_diff": {
            "added_nodes": [n.short_name for n in str_diff.nodes_by(diff.ADDED)],
            "removed_nodes": [n.short_name for n in str_diff.nodes_by(diff.REMOVED)],
            "added_edges": [f"{e.source.split('/')[-1]} -> {e.target.split('/')[-1]}" for e in str_diff.edges_by(diff.ADDED)],
            "removed_edges": [f"{e.source.split('/')[-1]} -> {e.target.split('/')[-1]}" for e in str_diff.edges_by(diff.REMOVED)]
        },
        "reachability": {
            "before_path_count": len(r_bef.paths),
            "updated_path_count": len(r_aft.paths),
            "new_paths": new_paths
        }
    }

    # --- STAGE 5: FINDINGS & GATE DECISION ---
    found = findings.collect(str_diff, r_diff)
    scorer = severity.BuiltinScorer(node_roles=roles_cfg, paths=r_aft)
    scored = severity.score_all(found, scorer)
    decision = gate.evaluate(scored)

    findings_list = []
    for sc_item in scored:
        f = sc_item.finding
        s = sc_item.score
        findings_list.append({
            "category": f.category,
            "title": f.title,
            "detail": f.detail,
            "subject": f.subject,
            "risk": s.risk,
            "impact": s.impact,
            "feasibility": s.feasibility,
            "rationale": list(s.rationale)
        })

    stage5 = {
        "verdict": decision.verdict,
        "exit_code": decision.exit_code,
        "summary": decision.summary(),
        "findings": findings_list,
        "risk_breakdown": {
            "risk_5": sum(1 for f in findings_list if f["risk"] == 5),
            "risk_4": sum(1 for f in findings_list if f["risk"] == 4),
            "risk_3": sum(1 for f in findings_list if f["risk"] == 3),
            "risk_2": sum(1 for f in findings_list if f["risk"] == 2),
            "risk_1": sum(1 for f in findings_list if f["risk"] == 1)
        }
    }

    return {
        "stage1_parse": stage1,
        "stage2_graph": stage2,
        "stage3_secoc": stage3,
        "stage4_reachability": stage4,
        "stage5_gate": stage5
    }

def run_pipeline_stages(scenario_id):
    scenario_path = SCENARIOS_DIR / scenario_id
    bef_path = scenario_path / 'before.arxml'
    aft_path = scenario_path / 'after.arxml'
    roles_path = scenario_path / 'roles.yaml'
    res = run_pipeline_paths(bef_path, aft_path, roles_path)
    res["scenario_id"] = scenario_id
    return res

class PipelineHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).resolve().parent / 'static'), **kwargs)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/upload-and-run':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                req_data = json.loads(body)
                
                bef_content = req_data.get('before_content', '')
                aft_content = req_data.get('after_content', '')
                roles_content = req_data.get('roles_content', '')
                
                bef_file = UPLOAD_DIR / 'custom_before.arxml'
                aft_file = UPLOAD_DIR / 'custom_after.arxml'
                roles_file = UPLOAD_DIR / 'custom_roles.yaml'
                
                bef_file.write_text(bef_content, encoding='utf-8')
                aft_file.write_text(aft_content, encoding='utf-8')
                if roles_content.strip():
                    roles_file.write_text(roles_content, encoding='utf-8')
                    r_path = roles_file
                else:
                    r_path = None
                    
                data = run_pipeline_paths(bef_file, aft_file, r_path)
                data["scenario_id"] = "custom_upload"
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return
        return super().do_POST()
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/scenarios':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(list_scenarios()).encode('utf-8'))
            return
        elif parsed.path == '/api/run':
            qs = urllib.parse.parse_qs(parsed.query)
            scenario_id = qs.get('scenario', ['01_jeep_uconnect'])[0]
            try:
                data = run_pipeline_stages(scenario_id)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
            return
        return super().do_GET()

def start_server():
    os.chdir(Path(__file__).resolve().parent)
    with socketserver.TCPServer(("", PORT), PipelineHandler) as httpd:
        print(f"================================================================")
        print(f"  ARXML SecDiff Pipeline Stepper GUI running at:")
        print(f"  http://localhost:{PORT}")
        print(f"================================================================")
        httpd.serve_forever()

if __name__ == '__main__':
    start_server()
