"""
24-Node Full Vehicle Experiment
================================
Integrates 3 real-world attack scenarios into a 24-node / 8-ECU vehicle ARXML,
runs the arxml-secdiff pipeline, and compares findings vs isolated small scenarios.

Scenarios injected via cross-domain connectors through the Central Gateway:
  01_jeep_uconnect:     ivi -> cgw -> bridge -> steerCtl (using existing chassis steerCtl)
  02_bmw_connecteddrive: tcu -> cgw -> chassis (using existing brakeCtl as chassis target)
  11_toyota_can_injection: headlight -> cgw -> bcm -> doorLock (CAN injection via light bus)
"""
import sys, os, copy, json
from pathlib import Path
from lxml import etree

ROOT = Path(r'D:\arxml-secdiff-main\graph_based_security_validation-main')
sys.path.insert(0, str(ROOT))

from arxml_secdiff import pipeline

BASE_ARXML = ROOT / 'large_vehicle_experiment' / 'full_vehicle_24node.arxml'
OUT_DIR = ROOT / 'large_vehicle_experiment' / 'results'
OUT_DIR.mkdir(exist_ok=True)

NS = 'http://autosar.org/schema/r4.0'

def parse_arxml(path):
    return etree.parse(str(path))

def local_name(el):
    if not isinstance(el.tag, str):
        return ""
    return el.tag.split('}')[-1] if '}' in el.tag else el.tag

def get_child_by_local(parent, name):
    for c in parent:
        if local_name(c) == name:
            return c
    return None

def find_composition(tree):
    for el in tree.iter():
        if local_name(el) == 'COMPOSITION-SW-COMPONENT-TYPE':
            return el
    return None

def find_connectors(comp):
    for child in comp:
        if local_name(child) == 'CONNECTORS':
            return child
    return None

def add_assembly_connector(connectors_el, name, prov_comp, prov_port, req_comp, req_port):
    conn = etree.SubElement(connectors_el, 'ASSEMBLY-SW-CONNECTOR')
    sn = etree.SubElement(conn, 'SHORT-NAME')
    sn.text = name

    prov = etree.SubElement(conn, 'PROVIDER-IREF')
    cc = etree.SubElement(prov, 'CONTEXT-COMPONENT-REF')
    cc.set('DEST', 'SW-COMPONENT-PROTOTYPE')
    cc.text = prov_comp
    tp = etree.SubElement(prov, 'TARGET-P-PORT-REF')
    tp.set('DEST', 'P-PORT-PROTOTYPE')
    tp.text = prov_port

    req = etree.SubElement(conn, 'REQUESTER-IREF')
    cc2 = etree.SubElement(req, 'CONTEXT-COMPONENT-REF')
    cc2.set('DEST', 'SW-COMPONENT-PROTOTYPE')
    cc2.text = req_comp
    tr = etree.SubElement(req, 'TARGET-R-PORT-REF')
    tr.set('DEST', 'R-PORT-PROTOTYPE')
    tr.text = req_port

def add_port_to_swc(tree, swc_short_name, port_name, port_kind, interface_ref):
    for el in tree.iter():
        if local_name(el).endswith('-SW-COMPONENT-TYPE'):
            sn_el = get_child_by_local(el, 'SHORT-NAME')
            if sn_el is not None and sn_el.text == swc_short_name:
                ports = get_child_by_local(el, 'PORTS')
                if ports is None:
                    ports = etree.SubElement(el, 'PORTS')
                if port_kind == 'P':
                    port = etree.SubElement(ports, 'P-PORT-PROTOTYPE')
                    pn = etree.SubElement(port, 'SHORT-NAME')
                    pn.text = port_name
                    tref = etree.SubElement(port, 'PROVIDED-INTERFACE-TREF')
                    tref.set('DEST', 'SENDER-RECEIVER-INTERFACE')
                    tref.text = interface_ref
                else:
                    port = etree.SubElement(ports, 'R-PORT-PROTOTYPE')
                    pn = etree.SubElement(port, 'SHORT-NAME')
                    pn.text = port_name
                    tref = etree.SubElement(port, 'REQUIRED-INTERFACE-TREF')
                    tref.set('DEST', 'SENDER-RECEIVER-INTERFACE')
                    tref.text = interface_ref
                return True
    return False

def add_signal_chain(tree, pkg_name, prefix):
    for el in tree.iter():
        if local_name(el) == 'AR-PACKAGE':
            sn = get_child_by_local(el, 'SHORT-NAME')
            if sn is not None and sn.text == 'Comm':
                elements = get_child_by_local(el, 'ELEMENTS')
                if elements is None:
                    elements = etree.SubElement(el, 'ELEMENTS')
                
                ssig = etree.SubElement(elements, 'SYSTEM-SIGNAL')
                etree.SubElement(ssig, 'SHORT-NAME').text = f'{prefix}SSig'
                
                isig = etree.SubElement(elements, 'I-SIGNAL')
                etree.SubElement(isig, 'SHORT-NAME').text = f'{prefix}ISig'
                ref = etree.SubElement(isig, 'SYSTEM-SIGNAL-REF')
                ref.set('DEST', 'SYSTEM-SIGNAL')
                ref.text = f'/{pkg_name}/Comm/{prefix}SSig'
                
                pdu = etree.SubElement(elements, 'I-SIGNAL-I-PDU')
                etree.SubElement(pdu, 'SHORT-NAME').text = f'{prefix}IPdu'
                mappings = etree.SubElement(pdu, 'I-SIGNAL-TO-PDU-MAPPINGS')
                m = etree.SubElement(mappings, 'I-SIGNAL-TO-I-PDU-MAPPING')
                etree.SubElement(m, 'SHORT-NAME').text = f'{prefix}Map'
                iref = etree.SubElement(m, 'I-SIGNAL-REF')
                iref.set('DEST', 'I-SIGNAL')
                iref.text = f'/{pkg_name}/Comm/{prefix}ISig'
                return True
    return False

def add_data_mapping(tree, pkg_name, system_name, root_name, port_ref, data_ref, ssig_ref):
    for el in tree.iter():
        if local_name(el) == 'DATA-MAPPINGS':
            m = etree.SubElement(el, 'SENDER-RECEIVER-TO-SIGNAL-MAPPING')
            iref = etree.SubElement(m, 'DATA-ELEMENT-IREF')
            cc = etree.SubElement(iref, 'CONTEXT-COMPOSITION-REF')
            cc.set('DEST', 'ROOT-SW-COMPOSITION-PROTOTYPE')
            cc.text = f'/{pkg_name}/Topology/{system_name}/{root_name}'
            cp = etree.SubElement(iref, 'CONTEXT-PORT-REF')
            cp.set('DEST', 'P-PORT-PROTOTYPE')
            cp.text = port_ref
            td = etree.SubElement(iref, 'TARGET-DATA-PROTOTYPE-REF')
            td.set('DEST', 'VARIABLE-DATA-PROTOTYPE')
            td.text = data_ref
            sr = etree.SubElement(m, 'SYSTEM-SIGNAL-REF')
            sr.set('DEST', 'SYSTEM-SIGNAL')
            sr.text = ssig_ref
            return True
    return False


def write_arxml(tree, path):
    tree.write(str(path), encoding='utf-8', xml_declaration=True, pretty_print=True)


# ============================================================================
# SCENARIO 01: Jeep Uconnect — IVI -> CGW bridge -> Steering
# Attack: HU gets new port that bridges D-Bus to CAN, reaching steerCtl
# Injection: Add huToBridgeOut on InfotainmentHU, bridgeIn on CentralGateway,
#            then gwToSteer connector (unauthenticated bus hop to steerCtl)
# ============================================================================
def inject_jeep(base_path, out_before, out_after):
    # Before = base (no exploit path)
    import shutil
    shutil.copy2(base_path, out_before)
    
    tree = parse_arxml(base_path)
    
    # Add new interface for the D-Bus bridge
    add_port_to_swc(tree, 'InfotainmentHU', 'huToBridgeOut', 'P', '/FV/If/SteerAngle')
    
    # Add connector: ivi -> steerCtl (bypasses gateway isolation via unauthenticated hop)
    comp = find_composition(tree)
    conns = find_connectors(comp)
    add_assembly_connector(conns, 'jeepBridgeToSteer',
        '/FV/Swc/FullVehicle/ivi', '/FV/Swc/InfotainmentHU/huToBridgeOut',
        '/FV/Swc/FullVehicle/steerCtl', '/FV/Swc/SteeringController/SteerIn')
    
    # Add signal chain (no SecOC = unauthenticated)
    add_signal_chain(tree, 'FV', 'jeepBridge')
    
    # Add data mapping for the bridge hop
    add_data_mapping(tree, 'FV', 'FullVeh', 'Root',
        '/FV/Swc/InfotainmentHU/huToBridgeOut',
        '/FV/If/SteerAngle/angle',
        '/FV/Comm/jeepBridgeSSig')
    
    write_arxml(tree, out_after)


# ============================================================================
# SCENARIO 02: BMW ConnectedDrive — TCU -> CGW -> UDS diag to chassis
# Attack: Gateway gets diagnostic passthrough port, bridging TCU to brakeCtl
# ============================================================================
def inject_bmw(base_path, out_before, out_after):
    import shutil
    shutil.copy2(base_path, out_before)
    
    tree = parse_arxml(base_path)
    
    # Add new interface for UDS diagnostic
    for el in tree.iter():
        if not isinstance(el.tag, str):
            continue
        sn = el.find('SHORT-NAME')
        if sn is not None and sn.text == 'If':
            elements = el.find('ELEMENTS')
            iface = etree.SubElement(elements, 'SENDER-RECEIVER-INTERFACE')
            etree.SubElement(iface, 'SHORT-NAME').text = 'UdsDiag'
            de = etree.SubElement(iface, 'DATA-ELEMENTS')
            vdp = etree.SubElement(de, 'VARIABLE-DATA-PROTOTYPE')
            etree.SubElement(vdp, 'SHORT-NAME').text = 'val'
            break
    
    # Add ports
    add_port_to_swc(tree, 'CentralGateway', 'gwToChassisOut', 'P', '/FV/If/UdsDiag')
    add_port_to_swc(tree, 'BrakeController', 'gwToChassisIn', 'R', '/FV/If/UdsDiag')
    
    # Add connector: cgw -> brakeCtl (unauthenticated UDS passthrough)
    comp = find_composition(tree)
    conns = find_connectors(comp)
    add_assembly_connector(conns, 'bmwGwToChassis',
        '/FV/Swc/FullVehicle/cgw', '/FV/Swc/CentralGateway/gwToChassisOut',
        '/FV/Swc/FullVehicle/brakeCtl', '/FV/Swc/BrakeController/gwToChassisIn')
    
    # Signal chain (no SecOC)
    add_signal_chain(tree, 'FV', 'bmwUds')
    add_data_mapping(tree, 'FV', 'FullVeh', 'Root',
        '/FV/Swc/CentralGateway/gwToChassisOut',
        '/FV/If/UdsDiag/val',
        '/FV/Comm/bmwUdsSSig')
    
    write_arxml(tree, out_after)


# ============================================================================  
# SCENARIO 11: Toyota CAN Injection — Headlight ECU -> CAN bus -> BCM -> DoorLock
# Attack: Headlight CAN controller gets exploited, injects frames to body domain
# ============================================================================
def inject_toyota(base_path, out_before, out_after):
    import shutil
    shutil.copy2(base_path, out_before)
    
    tree = parse_arxml(base_path)
    
    # Add new interface for CAN injection
    for el in tree.iter():
        if not isinstance(el.tag, str):
            continue
        sn = el.find('SHORT-NAME')
        if sn is not None and sn.text == 'If':
            elements = el.find('ELEMENTS')
            iface = etree.SubElement(elements, 'SENDER-RECEIVER-INTERFACE')
            etree.SubElement(iface, 'SHORT-NAME').text = 'CanInject'
            de = etree.SubElement(iface, 'DATA-ELEMENTS')
            vdp = etree.SubElement(de, 'VARIABLE-DATA-PROTOTYPE')
            etree.SubElement(vdp, 'SHORT-NAME').text = 'frame'
            break
    
    # Add ports: headlight provides injected CAN frames, doorLock receives
    add_port_to_swc(tree, 'HeadlightCtrl', 'canInjectOut', 'P', '/FV/If/CanInject')
    add_port_to_swc(tree, 'DoorLockActuator', 'canInjectIn', 'R', '/FV/If/CanInject')
    
    # Add connector: headlight -> doorLock (cross-bus CAN injection)
    comp = find_composition(tree)
    conns = find_connectors(comp)
    add_assembly_connector(conns, 'toyotaCanInject',
        '/FV/Swc/FullVehicle/headlight', '/FV/Swc/HeadlightCtrl/canInjectOut',
        '/FV/Swc/FullVehicle/doorLock', '/FV/Swc/DoorLockActuator/canInjectIn')
    
    # Signal chain (no SecOC)
    add_signal_chain(tree, 'FV', 'toyotaCan')
    add_data_mapping(tree, 'FV', 'FullVeh', 'Root',
        '/FV/Swc/HeadlightCtrl/canInjectOut',
        '/FV/If/CanInject/frame',
        '/FV/Comm/toyotaCanSSig')
    
    write_arxml(tree, out_after)


# ============================================================================
# RUN EXPERIMENTS
# ============================================================================
def run_scenario(name, before_path, after_path, roles_config):
    """Run pipeline and return findings."""
    print(f'\n{"="*70}')
    print(f'SCENARIO: {name}')
    print(f'  Before: {before_path}')
    print(f'  After:  {after_path}')
    print(f'{"="*70}')
    
    result = pipeline.run(
        before_sources=[str(before_path)],
        updated_sources=[str(after_path)],
        roles_config=roles_config,
    )
    
    print(f'\n  Verdict: {result.verdict}')
    print(f'  Before nodes: {result.before.graph.number_of_nodes()}, edges: {result.before.graph.number_of_edges()}')
    print(f'  After  nodes: {result.updated.graph.number_of_nodes()}, edges: {result.updated.graph.number_of_edges()}')
    print(f'  Findings: {len(result.findings)}')
    print(f'  Scored:   {len(result.scored)}')
    
    for i, s in enumerate(result.scored):
        print(f'    [{i+1}] risk={s.risk} [{s.score.impact}/{s.score.feasibility}] {s.finding.category}: {s.finding.title} ({s.finding.detail})')
    
    return result


def run_small_scenario(name, scenario_dir):
    """Run the original small isolated scenario."""
    before = scenario_dir / 'before.arxml'
    after = scenario_dir / 'after.arxml'
    roles = scenario_dir / 'roles.yaml'
    
    result = pipeline.run(
        before_sources=[str(before)],
        updated_sources=[str(after)],
        roles_config=str(roles) if roles.exists() else None,
    )
    return result


# Main execution
if __name__ == '__main__':
    scenarios = {
        '01_jeep_uconnect': {
            'inject': inject_jeep,
            'roles': {
                'entry_points': [
                    {'node': '/FV/Swc/FullVehicle/btStack', 'reason': 'BT entry (Jeep Uconnect)'},
                    {'node': '/FV/Swc/FullVehicle/ivi', 'reason': 'IVI entry (Jeep Uconnect)'},
                ],
                'critical': [
                    {'node': '/FV/Swc/FullVehicle/steerCtl', 'asil': 'D', 'reason': 'Steering actuator'},
                    {'node': '/FV/Swc/FullVehicle/brakeAct', 'asil': 'D', 'reason': 'Brake actuator'},
                    {'node': '/FV/Swc/FullVehicle/brakeCtl', 'asil': 'D', 'reason': 'Brake controller'},
                    {'node': '/FV/Swc/FullVehicle/engineCtl', 'asil': 'C', 'reason': 'Engine controller'},
                    {'node': '/FV/Swc/FullVehicle/doorLock', 'asil': 'B', 'reason': 'Door lock actuator'},
                ],
            },
        },
        '02_bmw_connecteddrive': {
            'inject': inject_bmw,
            'roles': {
                'entry_points': [
                    {'node': '/FV/Swc/FullVehicle/tcu', 'reason': 'TCU entry (BMW ConnectedDrive)'},
                ],
                'critical': [
                    {'node': '/FV/Swc/FullVehicle/brakeCtl', 'asil': 'D', 'reason': 'Brake controller'},
                    {'node': '/FV/Swc/FullVehicle/brakeAct', 'asil': 'D', 'reason': 'Brake actuator'},
                    {'node': '/FV/Swc/FullVehicle/steerCtl', 'asil': 'D', 'reason': 'Steering actuator'},
                    {'node': '/FV/Swc/FullVehicle/engineCtl', 'asil': 'C', 'reason': 'Engine controller'},
                    {'node': '/FV/Swc/FullVehicle/doorLock', 'asil': 'B', 'reason': 'Door lock actuator'},
                ],
            },
        },
        '11_toyota_can_injection': {
            'inject': inject_toyota,
            'roles': {
                'entry_points': [
                    {'node': '/FV/Swc/FullVehicle/headlight', 'reason': 'Headlight CAN entry (Toyota)'},
                ],
                'critical': [
                    {'node': '/FV/Swc/FullVehicle/doorLock', 'asil': 'D', 'reason': 'Door lock (immobilizer)'},
                    {'node': '/FV/Swc/FullVehicle/brakeCtl', 'asil': 'D', 'reason': 'Brake controller'},
                    {'node': '/FV/Swc/FullVehicle/brakeAct', 'asil': 'D', 'reason': 'Brake actuator'},
                    {'node': '/FV/Swc/FullVehicle/steerCtl', 'asil': 'D', 'reason': 'Steering actuator'},
                ],
            },
        },
    }

    results_summary = {}

    # Run each scenario on the 24-node vehicle
    for name, cfg in scenarios.items():
        before_path = OUT_DIR / f'{name}_24node_before.arxml'
        after_path = OUT_DIR / f'{name}_24node_after.arxml'
        
        # Inject the attack
        cfg['inject'](BASE_ARXML, before_path, after_path)
        
        # Run pipeline
        result = run_scenario(f'{name} (24-node)', before_path, after_path, cfg['roles'])
        
        results_summary[name] = {
            'nodes': result.updated.graph.number_of_nodes(),
            'edges': result.updated.graph.number_of_edges(),
            'findings_24node': len(result.findings),
            'scored_24node': len(result.scored),
            'verdict': result.verdict,
            'findings_detail': [
                {'risk': s.risk, 'impact': s.score.impact, 'feasibility': s.score.feasibility, 'category': s.finding.category, 'title': s.finding.title, 'detail': s.finding.detail}
                for s in result.scored
            ],
        }

    # Run the small isolated scenarios for comparison
    print('\n\n' + '='*70)
    print('COMPARISON: Small Isolated Scenarios')
    print('='*70)
    
    for name in scenarios:
        scenario_dir = ROOT / 'scenario_runs' / name
        if scenario_dir.exists():
            small = run_small_scenario(name, scenario_dir)
            results_summary[name]['findings_small'] = len(small.findings)
            results_summary[name]['scored_small'] = len(small.scored)
            print(f'  {name}: {len(small.findings)} findings (small) vs {results_summary[name]["findings_24node"]} findings (24-node)')

    # Summary table
    print('\n\n' + '='*70)
    print('FINAL COMPARISON TABLE')
    print('='*70)
    print(f'{"Scenario":<30} {"Small":>6} {"24-Node":>8} {"Delta":>6} {"Verdict":<10}')
    print('-'*70)
    for name, r in results_summary.items():
        small = r.get('findings_small', '?')
        large = r['findings_24node']
        delta = f'+{large - small}' if isinstance(small, int) else '?'
        print(f'{name:<30} {small:>6} {large:>8} {delta:>6} {r["verdict"]:<10}')

    # Save JSON
    with open(OUT_DIR / 'experiment_results.json', 'w') as f:
        json.dump(results_summary, f, indent=2, default=str)
    print(f'\nResults saved to {OUT_DIR / "experiment_results.json"}')
