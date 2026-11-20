#!/usr/bin/env python3
"""Build the serialization-rule-compliant, enriched version of real_time_scenarios/.

Input : the original real_time_scenarios/<id>/{before,after}.arxml (minimal files)
Output: real_time_scenarios_realistic/<id>/{before,after}.arxml (+ roles/notes/cli_output)

Every enrichment is applied identically to the before and after file, so the only
difference between them is still the scenario's own change.  Output is validated with
the `autosar-data` library (pip install autosar-data), sorted per the AUTOSAR meta-model
(TPS_ASR_00014) and serialized per AUTOSAR_TPS_ARXMLSerializationRules (R20-11).

Usage (from the project root):  python real_time_scenarios_realistic/build_realistic.py
"""
from __future__ import annotations

import copy
import json
import re
import shutil
import sys
import uuid
from pathlib import Path

import autosar_data as ad
from lxml import etree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "real_time_scenarios"
sys.path.insert(0, str(ROOT))

from arxml_secdiff import parser as tool_parser  # noqa: E402
from arxml_secdiff import pipeline  # noqa: E402

NS = "http://autosar.org/schema/r4.0"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_HINT = "AUTOSAR_00051.xsd"          # TPS_ASR_00013: AUTOSAR_{number}.xsd, no path
SCHEMA_VERSION = ad.AutosarVersion.AUTOSAR_00051
UUID_NS = uuid.UUID("6f1c7a52-0b0e-4c1d-9a55-3d1f0a9a2c10")
CAN_BAUD, CANFD_BAUD = 500000, 2000000
SECURED_PDU_BYTES, PLAIN_PDU_BYTES = 16, 8   # CAN-FD frame sizes (13-byte secured PDU -> DLC 16)


# --------------------------------------------------------------------------- helpers
def E(tag, text=None, *children, **attrs):
    el = etree.Element(tag)
    for k, v in attrs.items():
        el.set(k, str(v))
    if text is not None:
        el.text = str(text)
    for c in children:
        if c is not None:
            el.append(c)
    return el


def named(tag, name, *children, **attrs):
    return E(tag, None, E("SHORT-NAME", name), *children, **attrs)


def ref(tag, dest, path):
    return E(tag, path, DEST=dest)


def pkg(name, subpackages=(), elements=()):
    p = named("AR-PACKAGE", name)
    if subpackages:
        p.append(E("AR-PACKAGES", None, *subpackages))
    if elements:
        p.append(E("ELEMENTS", None, *elements))
    return p


def load_stripped(path: Path) -> etree._Element:
    parser = etree.XMLParser(remove_comments=True, remove_blank_text=True)
    root = etree.parse(str(path), parser).getroot()
    for el in root.iter():
        if isinstance(el.tag, str) and el.tag.startswith("{"):
            el.tag = el.tag.split("}", 1)[1]
    return root


def sname(el):
    s = el.find("SHORT-NAME")
    return s.text if s is not None else None


def paths(root):
    """path -> element for every identifiable element (wrapper elements add no segment)."""
    out = {}

    def walk(el, prefix):
        for c in el:
            if not isinstance(c.tag, str):
                continue
            n = sname(c)
            if n is not None:
                p = f"{prefix}/{n}"
                out[p] = c
                walk(c, p)
            else:
                walk(c, prefix)

    walk(root, "")
    return out


def insert_after(parent, new, *after_tags):
    """Insert `new` after the last existing child among `after_tags` (else first)."""
    pos = 0
    for i, c in enumerate(parent):
        if isinstance(c.tag, str) and c.tag in after_tags:
            pos = i + 1
    parent.insert(pos, new)


def top_package(root, name):
    for p in root.find("AR-PACKAGES"):
        if sname(p) == name:
            return p
    return None


def sub_package(top, name):
    for p in top.find("AR-PACKAGES"):
        if sname(p) == name:
            return p
    return None


def elements_of(package):
    els = package.find("ELEMENTS")
    if els is None:
        els = E("ELEMENTS")
        package.append(els)
    return els


# --------------------------------------------------------------------------- platform types
def platform_package():
    def base(n, size, native):
        return named("SW-BASE-TYPE", n, E("CATEGORY", "FIXED_LENGTH"), E("BASE-TYPE-SIZE", size),
                     E("BASE-TYPE-ENCODING", "NONE"), E("NATIVE-DECLARATION", native))

    def props(base_ref=None, impl_ref=None):
        cond = E("SW-DATA-DEF-PROPS-CONDITIONAL")
        if base_ref:
            cond.append(ref("BASE-TYPE-REF", "SW-BASE-TYPE", base_ref))
        if impl_ref:
            cond.append(ref("IMPLEMENTATION-DATA-TYPE-REF", "IMPLEMENTATION-DATA-TYPE", impl_ref))
        return E("SW-DATA-DEF-PROPS", None, E("SW-DATA-DEF-PROPS-VARIANTS", None, cond))

    def value(n, b):
        return named("IMPLEMENTATION-DATA-TYPE", n, E("CATEGORY", "VALUE"),
                     props(base_ref=f"/Platform/BaseTypes/{b}"))

    def array(n, elem, size):
        return named("IMPLEMENTATION-DATA-TYPE", n, E("CATEGORY", "ARRAY"),
                     E("SUB-ELEMENTS", None,
                       named("IMPLEMENTATION-DATA-TYPE-ELEMENT", "Element", E("CATEGORY", "TYPE_REFERENCE"),
                             E("ARRAY-SIZE", size), E("ARRAY-SIZE-SEMANTICS", "FIXED-SIZE"),
                             props(impl_ref=f"/Platform/ImplementationDataTypes/{elem}"))))

    return pkg("Platform", subpackages=[
        pkg("BaseTypes", elements=[base("boolean", 8, "boolean"), base("uint8", 8, "uint8"),
                                   base("uint16", 16, "uint16"), base("uint32", 32, "uint32")]),
        pkg("ImplementationDataTypes", elements=[
            value("Boolean", "boolean"), value("UInt8", "uint8"), value("UInt16", "uint16"),
            value("UInt32", "uint32"), array("Byte8Array", "UInt8", 8)]),
    ])


BYTE8 = "/Platform/ImplementationDataTypes/Byte8Array"
INFERRED: list[str] = []


# --------------------------------------------------------------------------- enrichment
def desc(el, text):
    if el.find("DESC") is None and el.find("SHORT-NAME") is not None:
        insert_after(el, E("DESC", None, E("L-2", text, L="EN")), "SHORT-NAME", "SHORT-NAME-FRAGMENTS", "LONG-NAME")


def derive_topology(orig_file: Path):
    """From the ORIGINAL file, derive which ECU sends / receives each on-wire PDU."""
    m = tool_parser.parse([str(orig_file)])
    protos_by_type = {}
    for p in m.prototypes.values():
        protos_by_type.setdefault(p.type_ref, []).append(p.path)
    secured_of = {}
    for pdu in m.pdus.values():
        if pdu.kind == "SECURED-I-PDU" and pdu.payload_ref:
            tgt = m.index.get(pdu.payload_ref)
            if tgt is not None and tgt.tag == "PDU-TRIGGERING":
                tgt_ref = tgt.find("I-PDU-REF")
                auth = tgt_ref.text if tgt_ref is not None else None
            else:
                auth = pdu.payload_ref
            if auth:
                secured_of[auth] = pdu.path
    tx, rx = {}, {}   # pdu path -> set(ecu path)
    for r in m.routes:
        if not r.pdu or not r.port:
            continue
        port = m.port(r.port)
        if port is None:
            continue
        for proto in protos_by_type.get(port.owner, []):
            ecu = m.swc_to_ecu.get(proto)
            if ecu:
                tx.setdefault(r.pdu, set()).add(ecu)
            for c in m.assembly_connectors.values():
                if c.provider_component == proto and c.provider_port == r.port and c.requester_component:
                    rx_ecu = m.swc_to_ecu.get(c.requester_component)
                    if rx_ecu:
                        rx.setdefault(r.pdu, set()).add(rx_ecu)
    return m, secured_of, tx, rx


def enrich(root, orig_file: Path, snapshot: str):
    P = paths(root)
    model, secured_of, tx_map, rx_map = derive_topology(orig_file)

    # 1. platform data types + typed data elements
    root.find("AR-PACKAGES").append(platform_package())
    for v in root.iter("VARIABLE-DATA-PROTOTYPE"):
        if v.find("TYPE-TREF") is None:
            insert_after(v, ref("TYPE-TREF", "IMPLEMENTATION-DATA-TYPE", BYTE8), "SHORT-NAME", "DESC", "CATEGORY",
                         "SW-DATA-DEF-PROPS")

    # 2. descriptions
    for tag, fmt in (("SENDER-RECEIVER-INTERFACE", "Sender/receiver interface {n}"),
                     ("APPLICATION-SW-COMPONENT-TYPE", "Application software component type {n}"),
                     ("SENSOR-ACTUATOR-SW-COMPONENT-TYPE", "Sensor/actuator software component type {n}"),
                     ("COMPOSITION-SW-COMPONENT-TYPE", "Composition {n}"),
                     ("ECU-INSTANCE", "ECU instance {n}"), ("SYSTEM", "System extract {n}"),
                     ("I-SIGNAL-I-PDU", "Authentic/plain I-PDU {n}"), ("SECURED-I-PDU", "SecOC secured I-PDU {n}")):
        for el in root.iter(tag):
            desc(el, fmt.format(n=sname(el)))

    # 3. internal behavior + implementation for atomic component types
    for top in list(root.find("AR-PACKAGES")):
        sw = sub_package(top, "Swc") if top.find("AR-PACKAGES") is not None else None
        if sw is None:
            continue
        impls = []
        for comp in list(elements_of(sw)):
            if comp.tag not in ("APPLICATION-SW-COMPONENT-TYPE", "SENSOR-ACTUATOR-SW-COMPONENT-TYPE"):
                continue
            cpath = f"/{sname(top)}/Swc/{sname(comp)}"
            bpath = f"{cpath}/Behavior"
            events, runnables = [], []
            cyc_sends, cyc_name = [], "Run_Cyclic10ms"
            for port in comp.findall("PORTS/*"):
                pname = sname(port)
                iref = port.find("PROVIDED-INTERFACE-TREF")
                kind = "P"
                if iref is None:
                    iref = port.find("REQUIRED-INTERFACE-TREF")
                    kind = "R"
                if iref is None or iref.text not in P:
                    continue
                de = P[iref.text].find("DATA-ELEMENTS/VARIABLE-DATA-PROTOTYPE")
                if de is None:
                    continue
                dpath = f"{iref.text}/{sname(de)}"
                port_path = f"{cpath}/{pname}"
                if kind == "P":
                    cyc_sends.append(named("VARIABLE-ACCESS", f"Snd_{pname}", E("ACCESSED-VARIABLE", None, E(
                        "AUTOSAR-VARIABLE-IREF", None,
                        ref("PORT-PROTOTYPE-REF", "P-PORT-PROTOTYPE", port_path),
                        ref("TARGET-DATA-PROTOTYPE-REF", "VARIABLE-DATA-PROTOTYPE", dpath)))))
                else:
                    rn = f"Run_{pname}_Rx"
                    runnables.append(named(
                        "RUNNABLE-ENTITY", rn, E("CAN-BE-INVOKED-CONCURRENTLY", "false"),
                        E("DATA-RECEIVE-POINT-BY-ARGUMENTS", None, named(
                            "VARIABLE-ACCESS", f"Rcv_{pname}", E("ACCESSED-VARIABLE", None, E(
                                "AUTOSAR-VARIABLE-IREF", None,
                                ref("PORT-PROTOTYPE-REF", "R-PORT-PROTOTYPE", port_path),
                                ref("TARGET-DATA-PROTOTYPE-REF", "VARIABLE-DATA-PROTOTYPE", dpath))))),
                        E("SYMBOL", rn)))
                    events.append(named(
                        "DATA-RECEIVED-EVENT", f"Dre_{pname}", ref("START-ON-EVENT-REF", "RUNNABLE-ENTITY", f"{bpath}/{rn}"),
                        E("DATA-IREF", None, ref("CONTEXT-R-PORT-REF", "R-PORT-PROTOTYPE", port_path),
                          ref("TARGET-DATA-ELEMENT-REF", "VARIABLE-DATA-PROTOTYPE", dpath))))
            if cyc_sends:
                runnables.append(named("RUNNABLE-ENTITY", cyc_name, E("CAN-BE-INVOKED-CONCURRENTLY", "false"),
                                       E("DATA-SEND-POINTS", None, *cyc_sends), E("SYMBOL", cyc_name)))
                events.append(named("TIMING-EVENT", "Tev_Cyclic10ms",
                                    ref("START-ON-EVENT-REF", "RUNNABLE-ENTITY", f"{bpath}/{cyc_name}"),
                                    E("PERIOD", "0.01")))
            if not runnables:
                continue
            beh = named("SWC-INTERNAL-BEHAVIOR", "Behavior", E("EVENTS", None, *events), E("RUNNABLES", None, *runnables))
            comp.append(E("INTERNAL-BEHAVIORS", None, beh))
            impls.append(named("SWC-IMPLEMENTATION", f"{sname(comp)}_Impl", E("PROGRAMMING-LANGUAGE", "C"),
                               E("SW-VERSION", "1.0.0"), ref("BEHAVIOR-REF", "SWC-INTERNAL-BEHAVIOR", bpath)))
        for i in impls:
            elements_of(sw).append(i)

    # 4. communication layer: lengths, mappings, SecOC properties
    data_id = 0x100
    for top in root.find("AR-PACKAGES"):
        if top.find("AR-PACKAGES") is None:
            continue
        comm = sub_package(top, "Comm")
        topo = sub_package(top, "Topology")
        if comm is None or topo is None:
            continue
        tname = sname(top)
        for isig in comm.iter("I-SIGNAL"):
            if isig.find("LENGTH") is None:
                insert_after(isig, E("LENGTH", "64"), "SHORT-NAME", "DESC")
        for pdu in comm.iter("I-SIGNAL-I-PDU"):
            if pdu.find("LENGTH") is None:
                insert_after(pdu, E("LENGTH", str(PLAIN_PDU_BYTES)), "SHORT-NAME", "DESC")
            for mp in pdu.iter("I-SIGNAL-TO-I-PDU-MAPPING"):
                if mp.find("SHORT-NAME") is None:
                    ir = mp.find("I-SIGNAL-REF")
                    mp.insert(0, E("SHORT-NAME", f"{ir.text.rsplit('/', 1)[-1]}_Map" if ir is not None else "Map"))
                if mp.find("PACKING-BYTE-ORDER") is None:
                    mp.append(E("PACKING-BYTE-ORDER", "MOST-SIGNIFICANT-BYTE-LAST"))
                if mp.find("START-POSITION") is None:
                    mp.append(E("START-POSITION", "0"))

        # ---- network objects derived from the original topology
        net_pkg = pkg("Network")
        net_els = elements_of(net_pkg)
        cluster_path = f"/{tname}/Network/Backbone"
        ecus = {p: el for p, el in paths(topo).items() if el.tag == "ECU-INSTANCE"}
        ecus = {f"/{tname}/Topology/{sname(el)}": el for el in topo.iter("ECU-INSTANCE")}
        ecu_ports = {p: [] for p in ecus}       # ecu path -> list of port elements
        pdu_els = {sname(e): e for e in comm.iter() if e.tag in ("I-SIGNAL-I-PDU", "SECURED-I-PDU")}
        auth_to_secured = {k.rsplit("/", 1)[-1]: v.rsplit("/", 1)[-1] for k, v in secured_of.items()
                           if k.startswith(f"/{tname}/")}
        for sec in comm.iter("SECURED-I-PDU"):          # original files: empty PAYLOAD-REF in some 'fix' scenarios
            pr = sec.find("PAYLOAD-REF")
            if pr is None or not (pr.text or "").strip():
                guess = sname(sec).replace("SecuredIPdu", "IPdu")
                if guess in pdu_els and guess != sname(sec):
                    auth_to_secured[guess] = sname(sec)
                    INFERRED.append(f"{snapshot}:{tname}/{sname(sec)} -> {guess}")
                    if pr is None:
                        pr = E("PAYLOAD-REF", f"/{tname}/Comm/{guess}", DEST="I-SIGNAL-I-PDU")
                        sec.append(pr)
                    else:
                        pr.text = f"/{tname}/Comm/{guess}"
        frames, frame_trigs, pdu_trigs = [], [], []
        next_id = 0x100 if tname == "FV" else 0x400
        trig_path = lambda n: f"{cluster_path}/Ch0/Trg_{n}"
        ordered = sorted(pdu_els)
        for pn in ordered:
            pdu_el = pdu_els[pn]
            ppath = f"/{tname}/Comm/{pn}"
            secured = pdu_el.tag == "SECURED-I-PDU"
            authentic = pn in auth_to_secured
            on_wire_path = ppath if not authentic else f"/{tname}/Comm/{auth_to_secured[pn]}"
            tx_ecus = sorted(e for e in tx_map.get(ppath, set()) | tx_map.get(on_wire_path, set()) if e in ecus)
            rx_ecus = sorted(e for e in rx_map.get(ppath, set()) | rx_map.get(on_wire_path, set()) if e in ecus)
            port_refs = []
            for e, direction in [(x, "OUT") for x in tx_ecus] + [(x, "IN") for x in rx_ecus]:
                pname = f"PP_{pn}_{'Tx' if direction == 'OUT' else 'Rx'}"
                ecu_ports[e].append(named("I-PDU-PORT", pname, E("COMMUNICATION-DIRECTION", direction)))
                port_refs.append(ref("I-PDU-PORT-REF", "I-PDU-PORT", f"{e}/CanConn0/{pname}"))
            pdu_trigs.append(named("PDU-TRIGGERING", f"Trg_{pn}",
                                   E("I-PDU-PORT-REFS", None, *port_refs) if port_refs else None,
                                   ref("I-PDU-REF", "SECURED-I-PDU" if secured else "I-SIGNAL-I-PDU", ppath)))
            if authentic:
                continue          # authentic PDU is carried inside the secured PDU: no frame of its own
            flen = SECURED_PDU_BYTES if secured else PLAIN_PDU_BYTES
            fname = f"Frame_{pn}"
            frames.append(named("CAN-FRAME", fname, E("FRAME-LENGTH", str(flen)), E(
                "PDU-TO-FRAME-MAPPINGS", None, named(
                    "PDU-TO-FRAME-MAPPING", f"Map_{pn}", E("PACKING-BYTE-ORDER", "MOST-SIGNIFICANT-BYTE-LAST"),
                    ref("PDU-REF", "SECURED-I-PDU" if secured else "I-SIGNAL-I-PDU", ppath), E("START-POSITION", "0")))))
            fp_refs = []
            for e, direction in [(x, "OUT") for x in tx_ecus] + [(x, "IN") for x in rx_ecus]:
                fpn = f"FP_{fname}_{'Tx' if direction == 'OUT' else 'Rx'}"
                ecu_ports[e].append(named("FRAME-PORT", fpn, E("COMMUNICATION-DIRECTION", direction)))
                fp_refs.append(ref("FRAME-PORT-REF", "FRAME-PORT", f"{e}/CanConn0/{fpn}"))
            frame_trigs.append(named(
                "CAN-FRAME-TRIGGERING", f"FT_{fname}", E("FRAME-PORT-REFS", None, *fp_refs) if fp_refs else None,
                ref("FRAME-REF", "CAN-FRAME", f"/{tname}/Network/{fname}"),
                E("PDU-TRIGGERINGS", None, E("PDU-TRIGGERING-REF-CONDITIONAL", None,
                                             ref("PDU-TRIGGERING-REF", "PDU-TRIGGERING", trig_path(pn)))),
                E("CAN-ADDRESSING-MODE", "STANDARD"), E("CAN-FRAME-RX-BEHAVIOR", "CAN-FD"),
                E("CAN-FRAME-TX-BEHAVIOR", "CAN-FD"), E("IDENTIFIER", str(next_id))))
            next_id += 1

        # SECURED-I-PDU: schema-valid SecOC structure; payload -> PDU-TRIGGERING of the authentic PDU
        for sec in comm.iter("SECURED-I-PDU"):
            old = {k: sec.find(k) for k in ("AUTH-INFO-TX-LENGTH", "FRESHNESS-VALUE-ID", "FRESHNESS-VALUE-LENGTH")}
            props = E("SECURE-COMMUNICATION-PROPS")
            props.append(E("AUTH-ALGORITHM", "CMAC"))
            if old["AUTH-INFO-TX-LENGTH"] is not None:
                props.append(E("AUTH-INFO-TX-LENGTH", old["AUTH-INFO-TX-LENGTH"].text))
            props.append(E("DATA-ID", str(data_id)))
            data_id += 1
            if old["FRESHNESS-VALUE-ID"] is not None:
                props.append(E("FRESHNESS-VALUE-ID", old["FRESHNESS-VALUE-ID"].text))
            if old["FRESHNESS-VALUE-LENGTH"] is not None:
                props.append(E("FRESHNESS-VALUE-LENGTH", old["FRESHNESS-VALUE-LENGTH"].text))
                props.append(E("FRESHNESS-VALUE-TX-LENGTH", old["FRESHNESS-VALUE-LENGTH"].text))
            for o in old.values():
                if o is not None:
                    sec.remove(o)
            pr = sec.find("PAYLOAD-REF")
            if pr is not None and (pr.text or "").strip():
                pr.set("DEST", "PDU-TRIGGERING")
                pr.text = trig_path(pr.text.rsplit("/", 1)[-1])
            elif pr is not None:
                sec.remove(pr)
            insert_after(sec, E("LENGTH", "13"), "SHORT-NAME", "DESC")
            sec.append(props)
            sec.append(E("USE-AS-CRYPTOGRAPHIC-I-PDU", "false"))

        # ECU instances: controller + connector + ports
        for e, el in ecus.items():
            ctrl = named("CAN-COMMUNICATION-CONTROLLER", "CanCtrl0", E("CAN-COMMUNICATION-CONTROLLER-VARIANTS", None, E(
                "CAN-COMMUNICATION-CONTROLLER-CONDITIONAL", None, E("WAKE-UP-BY-CONTROLLER-SUPPORTED", "false"))))
            el.append(E("COMM-CONTROLLERS", None, ctrl))
            el.append(E("SLEEP-MODE-SUPPORTED", "false"))
            el.append(E("WAKE-UP-OVER-BUS-SUPPORTED", "false"))
            conn = named("CAN-COMMUNICATION-CONNECTOR", "CanConn0",
                         ref("COMM-CONTROLLER-REF", "CAN-COMMUNICATION-CONTROLLER", f"{e}/CanCtrl0"),
                         E("ECU-COMM-PORT-INSTANCES", None, *ecu_ports[e]) if ecu_ports[e] else None)
            el.append(E("CONNECTORS", None, conn))

        channel = named("CAN-PHYSICAL-CHANNEL", "Ch0",
                        E("COMM-CONNECTORS", None, *[E("COMMUNICATION-CONNECTOR-REF-CONDITIONAL", None, ref(
                            "COMMUNICATION-CONNECTOR-REF", "CAN-COMMUNICATION-CONNECTOR", f"{e}/CanConn0"))
                            for e in sorted(ecus)]),
                        E("FRAME-TRIGGERINGS", None, *frame_trigs) if frame_trigs else None,
                        E("PDU-TRIGGERINGS", None, *pdu_trigs) if pdu_trigs else None)
        cluster = named("CAN-CLUSTER", "Backbone", E("CAN-CLUSTER-VARIANTS", None, E(
            "CAN-CLUSTER-CONDITIONAL", None, E("BAUDRATE", str(CAN_BAUD)), E("PHYSICAL-CHANNELS", None, channel),
            E("CAN-FD-BAUDRATE", str(CANFD_BAUD)))))
        net_els.append(cluster)
        for f in frames:
            net_els.append(f)
        top.find("AR-PACKAGES").append(net_pkg)

        # SYSTEM -> fibex elements (cluster, frames, PDUs)
        fib = [("CAN-CLUSTER", cluster_path)]
        fib += [("CAN-FRAME", f"/{tname}/Network/{sname(f)}") for f in frames]
        fib += [(pdu_els[n].tag, f"/{tname}/Comm/{n}") for n in ordered]
        for system in topo.iter("SYSTEM"):
            if system.find("CATEGORY") is None:
                insert_after(system, E("CATEGORY", "SYSTEM_EXTRACT"), "SHORT-NAME", "DESC")
            system.append(E("FIBEX-ELEMENTS", None, *[E("FIBEX-ELEMENT-REF-CONDITIONAL", None, ref(
                "FIBEX-ELEMENT-REF", d, p)) for d, p in fib]))
    return root


# --------------------------------------------------------------------------- serialization
def make_root(packages):
    root = etree.Element("{%s}AUTOSAR" % NS, nsmap={None: NS, "xsi": XSI})
    root.set("{%s}schemaLocation" % XSI, f"{NS} {SCHEMA_HINT}")
    admin = E("ADMIN-DATA", None, E("LANGUAGE", "EN"), E("DOC-REVISIONS", None, E(
        "DOC-REVISION", None, E("REVISION-LABEL", "1.0.0"), E("ISSUED-BY", "arxml-secdiff scenario generator"),
        E("DATE", "2026-11-20T00:00:00Z"))))
    root.append(qualify(admin))
    ps = etree.SubElement(root, "{%s}AR-PACKAGES" % NS)
    for p in packages:
        ps.append(qualify(copy.deepcopy(p)))
    return root


def qualify(el):
    for e in el.iter():
        if isinstance(e.tag, str) and not e.tag.startswith("{"):
            e.tag = "{%s}%s" % (NS, e.tag)
    return el


def to_bytes(packages):
    return etree.tostring(make_root(packages), xml_declaration=True, encoding="UTF-8")


def serialize_files(named_buffers: dict[str, bytes]) -> dict[str, str]:
    """Load ALL files into one model (strict), add UUIDs, order per meta-model, check refs, serialize."""
    model = ad.AutosarModel()
    for fname, buf in named_buffers.items():
        try:
            model.load_buffer(buf.decode("utf-8"), fname, True)
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"[validation] {fname}: {exc}")
    for path, el in model.identifiable_elements:
        try:
            el.set_attribute("UUID", str(uuid.uuid5(UUID_NS, path)))
        except Exception:  # noqa: BLE001
            pass
    model.sort()                                    # schema element order inside every element
    broken = model.check_references()
    if broken:
        shown = [f"{b.element_name} -> {b.character_data}" for b in broken[:8]]
        raise SystemExit(f"[validation] {len(broken)} unresolved references, e.g. {shown}")
    # containers the meta-model declares as unordered bags: TPS_ASR_00014 sorts them by short name
    sortable = {e.element_name for _, e in model.elements_dfs
                if e.element_type.content_mode == ad.ContentMode.Bag and not e.element_type.is_ordered}
    out = {}
    for f in model.files:
        out[f.filename] = write_arxml(etree.fromstring(f.serialize().encode("utf-8"),
                                                       etree.XMLParser(remove_blank_text=True)), sortable)
    return out


def local(el):
    return etree.QName(el).localname


def drop_empty_wrappers(root):
    """TPS_ASR_00016: no empty wrappers."""
    changed = True
    while changed:
        changed = False
        for el in list(root.iter()):
            if el is not root and isinstance(el.tag, str) and len(el) == 0 and not (el.text or "").strip():
                el.getparent().remove(el)
                changed = True


def order_bags(root, sortable):
    """TPS_ASR_00014: sort unordered named children by SHORT-NAME (stable, ascending)."""
    for el in root.iter():
        if isinstance(el.tag, str) and local(el) in sortable and len(el):
            kids = [c for c in el if isinstance(c.tag, str)]
            names = [c.findtext("{%s}SHORT-NAME" % NS) for c in kids]
            if all(n is not None for n in names):
                for c in kids:
                    el.remove(c)
                for c in sorted(kids, key=lambda c: c.findtext("{%s}SHORT-NAME" % NS)):
                    el.append(c)


def esc(t, attr=False):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return t.replace('"', "&quot;") if attr else t


def write_arxml(root, sortable) -> str:
    """Serialize per TPS_ASR_00004-00019: UTF-8 decl, 2-space NewLine blocks, OneLine primitives,
    alphabetical attributes, root attributes on their own lines, start/end tag pairs."""
    drop_empty_wrappers(root)
    order_bags(root, sortable)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<AUTOSAR", f'  xmlns="{NS}"', f'  xmlns:xsi="{XSI}"',
             f'  xsi:schemaLocation="{NS} {SCHEMA_HINT}">']

    def emit(el, depth):
        ind = "  " * depth
        attrs = sorted((etree.QName(k).localname, v) for k, v in el.attrib.items())
        a = "".join(f' {k}="{esc(v, True)}"' for k, v in attrs)
        if len(el) == 0:
            lines.append(f"{ind}<{local(el)}{a}>{esc((el.text or '').strip())}</{local(el)}>")
            return
        lines.append(f"{ind}<{local(el)}{a}>")
        for c in el:
            if isinstance(c.tag, str):
                emit(c, depth + 1)
        lines.append(f"{ind}</{local(el)}>")

    for c in root:
        if isinstance(c.tag, str):
            emit(c, 1)
    lines.append("</AUTOSAR>")
    return "\n".join(lines) + "\n"


def split_packages(root):
    """Partition into (filename, [top-package skeleton]) by <top>/<sub> package."""
    parts = []
    for top in root.find("AR-PACKAGES"):
        tname = sname(top)
        subs = top.find("AR-PACKAGES")
        if subs is None:
            parts.append((f"{tname}.arxml", [top]))
            continue
        for sub in subs:
            skeleton = named("AR-PACKAGE", tname)
            skeleton.append(E("AR-PACKAGES", None, copy.deepcopy(sub)))
            parts.append((f"{tname}_{sname(sub)}.arxml", [skeleton]))
    return parts


def build_snapshot(src_file: Path, snapshot: str):
    root = load_stripped(src_file)
    enrich(root, src_file, snapshot)
    merged_name = src_file.name
    merged = serialize_files({merged_name: to_bytes(list(root.find("AR-PACKAGES")))})[merged_name]
    parts = split_packages(root)
    split = serialize_files({n: to_bytes(p) for n, p in parts})
    return merged, split


def main():
    split_all = "--split-all" in sys.argv
    from scenario_defs import SCENARIOS  # noqa: E402
    summary = []
    base_out = HERE / "full_vehicle_base.arxml"
    base_out.write_text(build_snapshot(SRC / "full_vehicle_base.arxml", "base")[0], encoding="utf-8", newline="\n")
    for sc in SCENARIOS:
        out = HERE / sc.id
        out.mkdir(exist_ok=True)
        for snap in ("before", "after"):
            merged, split = build_snapshot(SRC / sc.id / f"{snap}.arxml", snap)
            (out / f"{snap}.arxml").write_text(merged, encoding="utf-8", newline="\n")
            if split_all or sc.id == "01_jeep_uconnect":
                d = out / "split" / snap
                d.mkdir(parents=True, exist_ok=True)
                for n, t in split.items():
                    (d / n).write_text(t, encoding="utf-8", newline="\n")
        for extra in ("roles.yaml", "NOTES.md"):
            shutil.copy2(SRC / sc.id / extra, out / extra)
        res = pipeline.run(before_sources=[str(out / "before.arxml")], updated_sources=[str(out / "after.arxml")],
                           roles_config=str(out / "roles.yaml"))
        data = {"scenario": sc.id, "title": sc.title, "verdict": res.verdict, "exit_code": res.exit_code,
                "total_nodes": res.updated.graph.number_of_nodes(), "total_edges": res.updated.graph.number_of_edges(),
                "findings_count": len(res.findings),
                "findings": [{"category": f.category, "title": f.title, "detail": f.detail, "risk": s.risk,
                              "impact": s.score.impact, "feasibility": s.score.feasibility}
                             for f, s in zip(res.findings, res.scored)],
                "expected_verdict": sc.expected_after}
        (out / "cli_output.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        summary.append((sc.id, res.verdict, sc.expected_after, len(res.findings)))
        print(f"[{sc.id}] {res.verdict} (expected {sc.expected_after}) findings={len(res.findings)}")
    return summary


if __name__ == "__main__":
    main()
