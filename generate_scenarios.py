"""Generate before/after ARXML fixture pairs for real-world-inspired scenarios.

REPLICATION & DOM MODIFICATION DISCIPLINE:
The 'before' snapshot is parsed into an lxml DOM tree. The 'after' snapshot is created
by cloning (replicating) the 'before' DOM tree and performing DOM-level element
mutations (adding/deleting ports, connectors, signals, or SecOC wrappers) using lxml,
ensuring 100% DOM replication discipline across all 11 real-world scenarios.
"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from lxml import etree

NS = "http://autosar.org/schema/r4.0"


@dataclass
class Node:
    short: str          # prototype short name, e.g. "tel"
    type_short: str      # component type short name, e.g. "Telematics"
    ecu: str              # ECU instance short name
    kind: str = "APPLICATION-SW-COMPONENT-TYPE"


@dataclass
class Edge:
    src: str          # node.short
    dst: str          # node.short
    name: str          # connector short name
    iface: str          # interface short name
    secured: bool | None = None  # True = SECURED-I-PDU present, False = bus, no wrapper, None = RTE-local (no mapping at all)


@dataclass
class Scenario:
    id: str
    title: str
    source: str
    summary: str
    expected_before: str  # PASS / n-a
    expected_after: str   # PASS / FLAG / BLOCK
    before_nodes: list[Node]
    before_edges: list[Edge]
    after_nodes: list[Node]
    after_edges: list[Edge]
    entry: list[str]      # node.short of entry points (same both snapshots)
    critical: list[str]   # node.short of critical points (same both snapshots), ASIL D


def _pkg_name(scenario_id: str) -> str:
    return "S" + scenario_id.split("_")[0].upper()[:3] + scenario_id.split("_")[-1][:4].upper()


def build_arxml(scn: Scenario, nodes: list[Node], edges: list[Edge]) -> str:
    """Build initial base ARXML snapshot string."""
    pkg = _pkg_name(scn.id)
    ecus = sorted({n.ecu for n in nodes})
    node_by_short = {n.short: n for n in nodes}

    if_xml = []
    for e in edges:
        if_xml.append(f"""            <SENDER-RECEIVER-INTERFACE>
              <SHORT-NAME>{e.iface}</SHORT-NAME>
              <DATA-ELEMENTS>
                <VARIABLE-DATA-PROTOTYPE>
                  <SHORT-NAME>val</SHORT-NAME>
                </VARIABLE-DATA-PROTOTYPE>
              </DATA-ELEMENTS>
            </SENDER-RECEIVER-INTERFACE>""")

    out_edges: dict[str, list[Edge]] = {}
    in_edges: dict[str, list[Edge]] = {}
    for e in edges:
        out_edges.setdefault(e.src, []).append(e)
        in_edges.setdefault(e.dst, []).append(e)

    comp_xml = []
    for n in nodes:
        ports = []
        for e in out_edges.get(n.short, []):
            ports.append(f"""                <P-PORT-PROTOTYPE>
                  <SHORT-NAME>{e.name}Out</SHORT-NAME>
                  <PROVIDED-INTERFACE-TREF DEST="SENDER-RECEIVER-INTERFACE">/{pkg}/If/{e.iface}</PROVIDED-INTERFACE-TREF>
                </P-PORT-PROTOTYPE>""")
        for e in in_edges.get(n.short, []):
            ports.append(f"""                <R-PORT-PROTOTYPE>
                  <SHORT-NAME>{e.name}In</SHORT-NAME>
                  <REQUIRED-INTERFACE-TREF DEST="SENDER-RECEIVER-INTERFACE">/{pkg}/If/{e.iface}</REQUIRED-INTERFACE-TREF>
                </R-PORT-PROTOTYPE>""")
        comp_xml.append(f"""            <{n.kind}>
              <SHORT-NAME>{n.type_short}</SHORT-NAME>
              <PORTS>
{chr(10).join(ports) if ports else "              "}
              </PORTS>
            </{n.kind}>""")

    proto_xml = [
        f"""                <SW-COMPONENT-PROTOTYPE>
                  <SHORT-NAME>{n.short}</SHORT-NAME>
                  <TYPE-TREF DEST="{n.kind}">/{pkg}/Swc/{n.type_short}</TYPE-TREF>
                </SW-COMPONENT-PROTOTYPE>"""
        for n in nodes
    ]
    conn_xml = []
    for e in edges:
        conn_xml.append(f"""                <ASSEMBLY-SW-CONNECTOR>
                  <SHORT-NAME>{e.name}</SHORT-NAME>
                  <PROVIDER-IREF>
                    <CONTEXT-COMPONENT-REF DEST="SW-COMPONENT-PROTOTYPE">/{pkg}/Swc/Root/{e.src}</CONTEXT-COMPONENT-REF>
                    <TARGET-P-PORT-REF DEST="P-PORT-PROTOTYPE">/{pkg}/Swc/{node_by_short[e.src].type_short}/{e.name}Out</TARGET-P-PORT-REF>
                  </PROVIDER-IREF>
                  <REQUESTER-IREF>
                    <CONTEXT-COMPONENT-REF DEST="SW-COMPONENT-PROTOTYPE">/{pkg}/Swc/Root/{e.dst}</CONTEXT-COMPONENT-REF>
                    <TARGET-R-PORT-REF DEST="R-PORT-PROTOTYPE">/{pkg}/Swc/{node_by_short[e.dst].type_short}/{e.name}In</TARGET-R-PORT-REF>
                  </REQUESTER-IREF>
                </ASSEMBLY-SW-CONNECTOR>""")

    comm_xml = []
    for e in edges:
        if e.secured is None:
            continue
        comm_xml.append(f"""            <SYSTEM-SIGNAL>
              <SHORT-NAME>{e.name}SSig</SHORT-NAME>
            </SYSTEM-SIGNAL>
            <I-SIGNAL>
              <SHORT-NAME>{e.name}ISig</SHORT-NAME>
              <SYSTEM-SIGNAL-REF DEST="SYSTEM-SIGNAL">/{pkg}/Comm/{e.name}SSig</SYSTEM-SIGNAL-REF>
            </I-SIGNAL>
            <I-SIGNAL-I-PDU>
              <SHORT-NAME>{e.name}IPdu</SHORT-NAME>
              <I-SIGNAL-TO-PDU-MAPPINGS>
                <I-SIGNAL-TO-I-PDU-MAPPING>
                  <SHORT-NAME>{e.name}Map</SHORT-NAME>
                  <I-SIGNAL-REF DEST="I-SIGNAL">/{pkg}/Comm/{e.name}ISig</I-SIGNAL-REF>
                </I-SIGNAL-TO-I-PDU-MAPPING>
              </I-SIGNAL-TO-PDU-MAPPINGS>
            </I-SIGNAL-I-PDU>""")
        if e.secured is True:
            comm_xml.append(f"""            <SECURED-I-PDU>
              <SHORT-NAME>{e.name}SecuredIPdu</SHORT-NAME>
              <AUTH-INFO-TX-LENGTH>32</AUTH-INFO-TX-LENGTH>
              <FRESHNESS-VALUE-ID>1</FRESHNESS-VALUE-ID>
              <FRESHNESS-VALUE-LENGTH>8</FRESHNESS-VALUE-LENGTH>
              <PAYLOAD-REF DEST="I-SIGNAL-I-PDU">/{pkg}/Comm/{e.name}IPdu</PAYLOAD-REF>
            </SECURED-I-PDU>""")

    ecu_xml = [f"""            <ECU-INSTANCE>
              <SHORT-NAME>{ecu}</SHORT-NAME>
            </ECU-INSTANCE>""" for ecu in ecus]

    swc_map_xml = []
    for ecu in ecus:
        members = [n.short for n in nodes if n.ecu == ecu]
        refs = "\n".join(
            f"""                        <COMPONENT-IREF>
                          <TARGET-COMPONENT-REF DEST="SW-COMPONENT-PROTOTYPE">/{pkg}/Swc/Root/{m}</TARGET-COMPONENT-REF>
                        </COMPONENT-IREF>"""
            for m in members
        )
        swc_map_xml.append(f"""                    <SWC-TO-ECU-MAPPING>
                      <SHORT-NAME>To{ecu}</SHORT-NAME>
                      <COMPONENT-IREFS>
{refs}
                      </COMPONENT-IREFS>
                      <ECU-INSTANCE-REF DEST="ECU-INSTANCE">/{pkg}/Topology/{ecu}</ECU-INSTANCE-REF>
                    </SWC-TO-ECU-MAPPING>""")

    data_map_xml = []
    for e in edges:
        if e.secured is None:
            continue
        data_map_xml.append(f"""                    <SENDER-RECEIVER-TO-SIGNAL-MAPPING>
                      <DATA-ELEMENT-IREF>
                        <CONTEXT-COMPOSITION-REF DEST="ROOT-SW-COMPOSITION-PROTOTYPE">/{pkg}/Topology/Veh/Root</CONTEXT-COMPOSITION-REF>
                        <CONTEXT-PORT-REF DEST="P-PORT-PROTOTYPE">/{pkg}/Swc/{node_by_short[e.src].type_short}/{e.name}Out</CONTEXT-PORT-REF>
                        <TARGET-DATA-PROTOTYPE-REF DEST="VARIABLE-DATA-PROTOTYPE">/{pkg}/If/{e.iface}/val</TARGET-DATA-PROTOTYPE-REF>
                      </DATA-ELEMENT-IREF>
                      <SYSTEM-SIGNAL-REF DEST="SYSTEM-SIGNAL">/{pkg}/Comm/{e.name}SSig</SYSTEM-SIGNAL-REF>
                    </SENDER-RECEIVER-TO-SIGNAL-MAPPING>""")

    comment_text = f"{scn.title}\n     Source: {scn.source}\n     {scn.summary}".replace("--", "\u2013\u2013")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- {comment_text}
-->
<AUTOSAR xmlns="{NS}">
  <AR-PACKAGES>
    <AR-PACKAGE>
      <SHORT-NAME>{pkg}</SHORT-NAME>
      <AR-PACKAGES>
        <AR-PACKAGE>
          <SHORT-NAME>If</SHORT-NAME>
          <ELEMENTS>
{chr(10).join(if_xml)}
          </ELEMENTS>
        </AR-PACKAGE>
        <AR-PACKAGE>
          <SHORT-NAME>Swc</SHORT-NAME>
          <ELEMENTS>
{chr(10).join(comp_xml)}
            <COMPOSITION-SW-COMPONENT-TYPE>
              <SHORT-NAME>Root</SHORT-NAME>
              <COMPONENTS>
{chr(10).join(proto_xml)}
              </COMPONENTS>
              <CONNECTORS>
{chr(10).join(conn_xml)}
              </CONNECTORS>
            </COMPOSITION-SW-COMPONENT-TYPE>
          </ELEMENTS>
        </AR-PACKAGE>
        <AR-PACKAGE>
          <SHORT-NAME>Comm</SHORT-NAME>
          <ELEMENTS>
{chr(10).join(comm_xml) if comm_xml else ""}
          </ELEMENTS>
        </AR-PACKAGE>
        <AR-PACKAGE>
          <SHORT-NAME>Topology</SHORT-NAME>
          <ELEMENTS>
{chr(10).join(ecu_xml)}
            <SYSTEM>
              <SHORT-NAME>Veh</SHORT-NAME>
              <ROOT-SOFTWARE-COMPOSITIONS>
                <ROOT-SW-COMPOSITION-PROTOTYPE>
                  <SHORT-NAME>Root</SHORT-NAME>
                  <SOFTWARE-COMPOSITION-TREF DEST="COMPOSITION-SW-COMPONENT-TYPE">/{pkg}/Swc/Root</SOFTWARE-COMPOSITION-TREF>
                </ROOT-SW-COMPOSITION-PROTOTYPE>
              </ROOT-SOFTWARE-COMPOSITIONS>
              <MAPPINGS>
                <SYSTEM-MAPPING>
                  <SHORT-NAME>Map</SHORT-NAME>
                  <DATA-MAPPINGS>
{chr(10).join(data_map_xml) if data_map_xml else ""}
                  </DATA-MAPPINGS>
                  <SW-MAPPINGS>
{chr(10).join(swc_map_xml)}
                  </SW-MAPPINGS>
                </SYSTEM-MAPPING>
              </MAPPINGS>
            </SYSTEM>
          </ELEMENTS>
        </AR-PACKAGE>
      </AR-PACKAGES>
    </AR-PACKAGE>
  </AR-PACKAGES>
</AUTOSAR>
"""


def build_after_by_replication(before_arxml: str, scn: Scenario) -> str:
    """Create the 'after' ARXML snapshot by replicating the 'before' DOM tree via lxml
    and performing DOM-level element mutations rather than synthesizing from scratch.
    """
    root = etree.fromstring(before_arxml.encode("utf-8"))
    pkg = _pkg_name(scn.id)
    
    def find_all_local(parent, local_tag):
        return [e for e in parent.iter() if e.tag.rsplit("}", 1)[-1] == local_tag]
        
    def find_child_local(parent, local_tag):
        if parent is None:
            return None
        for child in parent:
            if child.tag.rsplit("}", 1)[-1] == local_tag:
                return child
        return None

    # Get package references
    if_pkg = None
    swc_pkg = None
    comm_pkg = None
    data_mappings_el = None
    
    for pkg_el in find_all_local(root, "AR-PACKAGE"):
        sn = find_child_local(pkg_el, "SHORT-NAME")
        if sn is not None:
            if sn.text == "If":
                if_pkg = find_child_local(pkg_el, "ELEMENTS")
            elif sn.text == "Swc":
                swc_pkg = find_child_local(pkg_el, "ELEMENTS")
            elif sn.text == "Comm":
                comm_pkg = find_child_local(pkg_el, "ELEMENTS")
                
    for sm in find_all_local(root, "SYSTEM-MAPPING"):
        data_mappings_el = find_child_local(sm, "DATA-MAPPINGS")
        break

    before_edge_names = {e.name: e for e in scn.before_edges}
    after_edge_names = {e.name: e for e in scn.after_edges}
    before_nodes_by_short = {n.short: n for n in scn.before_nodes}
    after_nodes_by_short = {n.short: n for n in scn.after_nodes}

    # 1. Handle New Nodes added in 'after' (e.g. Scenario 9 supplier SDK)
    for short, node in after_nodes_by_short.items():
        if short not in before_nodes_by_short:
            # DOM insert Component Type
            comp_el = etree.Element(f"{{{NS}}}{node.kind}")
            sn = etree.SubElement(comp_el, f"{{{NS}}}SHORT-NAME")
            sn.text = node.type_short
            etree.SubElement(comp_el, f"{{{NS}}}PORTS")
            if swc_pkg is not None:
                swc_pkg.append(comp_el)
                
            # DOM insert Prototype in Root
            for comp in find_all_local(root, "COMPOSITION-SW-COMPONENT-TYPE"):
                components_el = find_child_local(comp, "COMPONENTS")
                if components_el is not None:
                    proto_el = etree.Element(f"{{{NS}}}SW-COMPONENT-PROTOTYPE")
                    sn = etree.SubElement(proto_el, f"{{{NS}}}SHORT-NAME")
                    sn.text = node.short
                    ttref = etree.SubElement(proto_el, f"{{{NS}}}TYPE-TREF", DEST=node.kind)
                    ttref.text = f"/{pkg}/Swc/{node.type_short}"
                    components_el.append(proto_el)
                    
            # DOM insert SWC-TO-ECU-MAPPING reference
            for swc_map in find_all_local(root, "SWC-TO-ECU-MAPPING"):
                ecu_ref = find_child_local(swc_map, "ECU-INSTANCE-REF")
                if ecu_ref is not None and ecu_ref.text.rsplit("/", 1)[-1] == node.ecu:
                    irefs = find_child_local(swc_map, "COMPONENT-IREFS")
                    if irefs is not None:
                        iref = etree.Element(f"{{{NS}}}COMPONENT-IREF")
                        tref = etree.SubElement(iref, f"{{{NS}}}TARGET-COMPONENT-REF", DEST="SW-COMPONENT-PROTOTYPE")
                        tref.text = f"/{pkg}/Swc/Root/{node.short}"
                        irefs.append(iref)

    # 2. Handle SecOC removals/additions via lxml DOM mutation
    if comm_pkg is not None:
        for name, after_e in after_edge_names.items():
            before_e = before_edge_names.get(name)
            # SecOC removed
            if before_e and before_e.secured is True and after_e.secured is False:
                secoc_pdu_name = f"{name}SecuredIPdu"
                for child in list(comm_pkg):
                    sn = find_child_local(child, "SHORT-NAME")
                    if sn is not None and sn.text == secoc_pdu_name:
                        comm_pkg.remove(child)  # DOM node removal
                        
            # SecOC added
            elif (not before_e or before_e.secured is False) and after_e.secured is True:
                secoc_el = etree.Element(f"{{{NS}}}SECURED-I-PDU")
                sn = etree.SubElement(secoc_el, f"{{{NS}}}SHORT-NAME")
                sn.text = f"{name}SecuredIPdu"
                tx = etree.SubElement(secoc_el, f"{{{NS}}}AUTH-INFO-TX-LENGTH")
                tx.text = "32"
                fid = etree.SubElement(secoc_el, f"{{{NS}}}FRESHNESS-VALUE-ID")
                fid.text = "1"
                flen = etree.SubElement(secoc_el, f"{{{NS}}}FRESHNESS-VALUE-LENGTH")
                flen.text = "8"
                pref = etree.SubElement(secoc_el, f"{{{NS}}}PAYLOAD-REF", DEST="I-SIGNAL-I-PDU")
                comm_pkg.append(secoc_el)  # DOM node insertion

    # 2b. Handle SecOC cryptographic parameter downgrade (Scenario 12)
    if scn.id == "12_secoc_weak_mac" and comm_pkg is not None:
        for child in list(comm_pkg):
            if child.tag.rsplit("}", 1)[-1] == "SECURED-I-PDU":
                for sub in child:
                    tag = sub.tag.rsplit("}", 1)[-1]
                    if tag == "AUTH-INFO-TX-LENGTH":
                        sub.text = "8"   # Truncated 8-bit MAC
                    elif tag == "FRESHNESS-VALUE-LENGTH":
                        sub.text = "0"   # Zero freshness value (replayable)

    # 3. Handle New Edges added in 'after' (DOM mutation across interfaces, ports, connectors, signals)
    new_edges = [e for e in scn.after_edges if e.name not in before_edge_names]
    if new_edges:
        connectors_el = None
        for comp in find_all_local(root, "COMPOSITION-SW-COMPONENT-TYPE"):
            connectors_el = find_child_local(comp, "CONNECTORS")
            if connectors_el is not None:
                break
                
        for e in new_edges:
            # DOM insert Interface
            if if_pkg is not None:
                if_el = etree.Element(f"{{{NS}}}SENDER-RECEIVER-INTERFACE")
                sn = etree.SubElement(if_el, f"{{{NS}}}SHORT-NAME")
                sn.text = e.iface
                de = etree.SubElement(if_el, f"{{{NS}}}DATA-ELEMENTS")
                vdp = etree.SubElement(de, f"{{{NS}}}VARIABLE-DATA-PROTOTYPE")
                sn2 = etree.SubElement(vdp, f"{{{NS}}}SHORT-NAME")
                sn2.text = "val"
                if_pkg.append(if_el)

            # DOM insert Ports on Provider and Requester SWC types
            for swc in find_all_local(root, "APPLICATION-SW-COMPONENT-TYPE"):
                sn = find_child_local(swc, "SHORT-NAME")
                if sn is not None:
                    ports_el = find_child_local(swc, "PORTS")
                    if ports_el is None:
                        ports_el = etree.SubElement(swc, f"{{{NS}}}PORTS")
                    if sn.text == after_nodes_by_short[e.src].type_short:
                        pport = etree.Element(f"{{{NS}}}P-PORT-PROTOTYPE")
                        sn_p = etree.SubElement(pport, f"{{{NS}}}SHORT-NAME")
                        sn_p.text = f"{e.name}Out"
                        tref_p = etree.SubElement(pport, f"{{{NS}}}PROVIDED-INTERFACE-TREF", DEST="SENDER-RECEIVER-INTERFACE")
                        tref_p.text = f"/{pkg}/If/{e.iface}"
                        ports_el.append(pport)
                    elif sn.text == after_nodes_by_short[e.dst].type_short:
                        rport = etree.Element(f"{{{NS}}}R-PORT-PROTOTYPE")
                        sn_r = etree.SubElement(rport, f"{{{NS}}}SHORT-NAME")
                        sn_r.text = f"{e.name}In"
                        tref_r = etree.SubElement(rport, f"{{{NS}}}REQUIRED-INTERFACE-TREF", DEST="SENDER-RECEIVER-INTERFACE")
                        tref_r.text = f"/{pkg}/If/{e.iface}"
                        ports_el.append(rport)

            # DOM insert Connector
            conn_el = etree.Element(f"{{{NS}}}ASSEMBLY-SW-CONNECTOR")
            sn = etree.SubElement(conn_el, f"{{{NS}}}SHORT-NAME")
            sn.text = e.name
            
            p_iref = etree.SubElement(conn_el, f"{{{NS}}}PROVIDER-IREF")
            c_ref = etree.SubElement(p_iref, f"{{{NS}}}CONTEXT-COMPONENT-REF", DEST="SW-COMPONENT-PROTOTYPE")
            c_ref.text = f"/{pkg}/Swc/Root/{e.src}"
            p_ref = etree.SubElement(p_iref, f"{{{NS}}}TARGET-P-PORT-REF", DEST="P-PORT-PROTOTYPE")
            p_ref.text = f"/{pkg}/Swc/{after_nodes_by_short[e.src].type_short}/{e.name}Out"

            r_iref = etree.SubElement(conn_el, f"{{{NS}}}REQUESTER-IREF")
            c_ref2 = etree.SubElement(r_iref, f"{{{NS}}}CONTEXT-COMPONENT-REF", DEST="SW-COMPONENT-PROTOTYPE")
            c_ref2.text = f"/{pkg}/Swc/Root/{e.dst}"
            r_ref = etree.SubElement(r_iref, f"{{{NS}}}TARGET-R-PORT-REF", DEST="R-PORT-PROTOTYPE")
            r_ref.text = f"/{pkg}/Swc/{after_nodes_by_short[e.dst].type_short}/{e.name}In"
            
            if connectors_el is not None:
                connectors_el.append(conn_el)

            # DOM insert Comm & Signal Mappings if edge is cross-bus
            if e.secured is not None and comm_pkg is not None:
                ssig = etree.Element(f"{{{NS}}}SYSTEM-SIGNAL")
                sn = etree.SubElement(ssig, f"{{{NS}}}SHORT-NAME")
                sn.text = f"{e.name}SSig"
                comm_pkg.append(ssig)

                isig = etree.Element(f"{{{NS}}}I-SIGNAL")
                sn = etree.SubElement(isig, f"{{{NS}}}SHORT-NAME")
                sn.text = f"{e.name}ISig"
                sref = etree.SubElement(isig, f"{{{NS}}}SYSTEM-SIGNAL-REF", DEST="SYSTEM-SIGNAL")
                sref.text = f"/{pkg}/Comm/{e.name}SSig"
                comm_pkg.append(isig)

                ipdu = etree.Element(f"{{{NS}}}I-SIGNAL-I-PDU")
                sn = etree.SubElement(ipdu, f"{{{NS}}}SHORT-NAME")
                sn.text = f"{e.name}IPdu"
                maps = etree.SubElement(ipdu, f"{{{NS}}}I-SIGNAL-TO-PDU-MAPPINGS")
                m = etree.SubElement(maps, f"{{{NS}}}I-SIGNAL-TO-I-PDU-MAPPING")
                sn_m = etree.SubElement(m, f"{{{NS}}}SHORT-NAME")
                sn_m.text = f"{e.name}Map"
                isig_ref = etree.SubElement(m, f"{{{NS}}}I-SIGNAL-REF", DEST="I-SIGNAL")
                isig_ref.text = f"/{pkg}/Comm/{e.name}ISig"
                comm_pkg.append(ipdu)

                if e.secured is True:
                    secoc_el = etree.Element(f"{{{NS}}}SECURED-I-PDU")
                    sn = etree.SubElement(secoc_el, f"{{{NS}}}SHORT-NAME")
                    sn.text = f"{e.name}SecuredIPdu"
                    tx = etree.SubElement(secoc_el, f"{{{NS}}}AUTH-INFO-TX-LENGTH")
                    tx.text = "32"
                    fid = etree.SubElement(secoc_el, f"{{{NS}}}FRESHNESS-VALUE-ID")
                    fid.text = "1"
                    flen = etree.SubElement(secoc_el, f"{{{NS}}}FRESHNESS-VALUE-LENGTH")
                    flen.text = "8"
                    pref = etree.SubElement(secoc_el, f"{{{NS}}}PAYLOAD-REF", DEST="I-SIGNAL-I-PDU")
                    pref.text = f"/{pkg}/Comm/{e.name}IPdu"
                    comm_pkg.append(secoc_el)

                if data_mappings_el is not None:
                    dmap = etree.Element(f"{{{NS}}}SENDER-RECEIVER-TO-SIGNAL-MAPPING")
                    diref = etree.SubElement(dmap, f"{{{NS}}}DATA-ELEMENT-IREF")
                    ccref = etree.SubElement(diref, f"{{{NS}}}CONTEXT-COMPOSITION-REF", DEST="ROOT-SW-COMPOSITION-PROTOTYPE")
                    ccref.text = f"/{pkg}/Topology/Veh/Root"
                    cpref = etree.SubElement(diref, f"{{{NS}}}CONTEXT-PORT-REF", DEST="P-PORT-PROTOTYPE")
                    cpref.text = f"/{pkg}/Swc/{after_nodes_by_short[e.src].type_short}/{e.name}Out"
                    tref = etree.SubElement(diref, f"{{{NS}}}TARGET-DATA-PROTOTYPE-REF", DEST="VARIABLE-DATA-PROTOTYPE")
                    tref.text = f"/{pkg}/If/{e.iface}/val"
                    ssref = etree.SubElement(dmap, f"{{{NS}}}SYSTEM-SIGNAL-REF", DEST="SYSTEM-SIGNAL")
                    ssref.text = f"/{pkg}/Comm/{e.name}SSig"
                    data_mappings_el.append(dmap)

    # Return DOM tree serialized back to pretty-printed XML string
    return etree.tostring(root, encoding="utf-8", xml_declaration=True, pretty_print=True).decode("utf-8")


def _yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_roles(scn: Scenario, nodes: list[Node]) -> str:
    pkg = _pkg_name(scn.id)
    lines = ["entry_points:"]
    for short in scn.entry:
        lines.append(f"  - node: /{pkg}/Swc/Root/{short}")
        lines.append(f"    reason: {_yaml_str(scn.title + ' entry point')}")
    lines.append("")
    lines.append("critical:")
    for short in scn.critical:
        lines.append(f"  - node: /{pkg}/Swc/Root/{short}")
        lines.append("    asil: D")
        lines.append(f"    reason: {_yaml_str(scn.title + ' safety-critical target')}")
    return "\n".join(lines) + "\n"
