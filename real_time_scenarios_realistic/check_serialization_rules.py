#!/usr/bin/env python3
"""Independent checker for AUTOSAR_TPS_ARXMLSerializationRules (FO R20-11).

Does not use the generator or the autosar-data library, so it can audit any .arxml file.
Usage: python check_serialization_rules.py <file-or-dir> [...]
Exit code 0 = no violations.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

from lxml import etree

XSI = "http://www.w3.org/2001/XMLSchema-instance"
NS_RE = re.compile(r"^http://autosar\.org/schema/r\d+\.\d+$")
HINT_RE = re.compile(r"^AUTOSAR_[0-9A-Za-z-]+\.xsd$")
SORTED_CONTAINERS = {"AR-PACKAGES", "ELEMENTS", "PORTS", "COMPONENTS", "CONNECTORS"}
OPEN_RE = re.compile(r"^<([A-Za-z0-9:-]+)((?:\s+[^<>]*)?)>$")
ONELINE_RE = re.compile(r"^<([A-Za-z0-9:-]+)((?:\s+[^<>]*)?)>([^<]*)</\1>$")
ATTR_RE = re.compile(r'([A-Za-z0-9:_.-]+)="')


def short(el):
    s = el.find("{*}SHORT-NAME")
    return s.text if s is not None else None


def check(path: Path) -> list[tuple[str, str]]:
    v: list[tuple[str, str]] = []
    raw = path.read_bytes()
    # 00002 / 00003
    if path.suffix != ".arxml":
        v.append(("TPS_ASR_00002", "extension must be .arxml"))
    if len(path.name) > 255:
        v.append(("TPS_ASR_00003", "file name longer than 255 characters"))
    # 00004 / 00006
    if raw.startswith(b"\xef\xbb\xbf"):
        v.append(("TPS_ASR_00006", "file starts with a UTF-8 BOM"))
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return v + [("TPS_ASR_00004", "not valid UTF-8")]
    lines = text.split("\n")
    # 00005 / 00007 / 00008
    if lines[0] != '<?xml version="1.0" encoding="UTF-8"?>':
        v.append(("TPS_ASR_00005/00007/00008", f"XML declaration must be exactly version=1.0 + encoding=UTF-8, got: {lines[0][:60]}"))
    if "\r" in text:
        v.append(("TPS_ASR_00019", "carriage returns present (use LF line endings)"))
    try:
        root = etree.fromstring(raw)
    except etree.XMLSyntaxError as exc:
        return v + [("XML", f"not well-formed: {exc}")]
    # 00011 / 00017 / 00018
    ns = etree.QName(root).namespace
    if etree.QName(root).localname != "AUTOSAR" or not ns or not NS_RE.match(ns):
        v.append(("TPS_ASR_00011", f"root must be AUTOSAR in http://autosar.org/schema/r<major>.<minor>, got {root.tag}"))
    if root.nsmap != {None: ns, "xsi": XSI}:
        v.append(("TPS_ASR_00017/00018", f"namespaces must be exactly default AUTOSAR ns + xsi, got {root.nsmap}"))
    for el in root.iter():
        if isinstance(el.tag, str):
            if el.prefix is not None:
                v.append(("TPS_ASR_00017", f"prefixed element <{el.prefix}:{etree.QName(el).localname}>"))
                break
            if etree.QName(el).namespace != ns:
                v.append(("TPS_ASR_00018", f"element in foreign namespace: {el.tag}"))
                break
    # 00012 / 00013
    loc = root.get("{%s}schemaLocation" % XSI)
    if not loc:
        v.append(("TPS_ASR_00012", "xsi:schemaLocation missing (mandatory)"))
    else:
        parts = loc.split()
        if len(parts) != 2 or parts[0] != ns:
            v.append(("TPS_ASR_00012", f"schemaLocation must map the AUTOSAR namespace to one hint, got '{loc}'"))
        elif not HINT_RE.match(parts[1]):
            v.append(("TPS_ASR_00013", f"schema hint must be AUTOSAR_{{number}}.xsd without a path, got '{parts[1]}'"))
    # 00015
    for i, ln in enumerate(lines, 1):
        if re.search(r"<[A-Za-z][^<>]*/>", ln):
            v.append(("TPS_ASR_00015", f"line {i}: self-closing empty element"))
            break
    # 00016 + references absolute
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        if len(el) == 0 and not (el.text or "").strip() and el.tag != "{%s}AUTOSAR" % ns:
            v.append(("TPS_ASR_00016", f"empty element/wrapper <{etree.QName(el).localname}> (line {el.sourceline})"))
            break
    for el in root.iter():
        if isinstance(el.tag, str) and el.get("DEST") is not None and not (el.text or "").startswith("/"):
            v.append(("TPS_GST_00169", f"reference not an absolute short-name path: {el.text!r} (line {el.sourceline})"))
            break
    # 00014 sorted containers (short-name key, ascending)
    for el in root.iter():
        if isinstance(el.tag, str) and etree.QName(el).localname in SORTED_CONTAINERS:
            keys = [short(c) for c in el if isinstance(c.tag, str)]
            if all(k is not None for k in keys) and keys != sorted(keys):
                v.append(("TPS_ASR_00014", f"<{etree.QName(el).localname}> children not sorted by SHORT-NAME (line {el.sourceline})"))
                break
    # 00019 layout
    depth, in_root_tag, bad = 0, False, None
    for i, ln in enumerate(lines[1:], 2):
        if ln == "":
            continue
        s = ln.strip()
        indent = len(ln) - len(ln.lstrip(" "))
        if "\t" in ln[:indent + 1]:
            bad = bad or (i, "tab indentation")
        if in_root_tag:
            if indent != 2:
                bad = bad or (i, "root attribute lines must be indented 2 spaces")
            if s.endswith(">"):
                in_root_tag = False
                depth = 1
            continue
        if s == "<AUTOSAR":
            in_root_tag = True
            continue
        if s.startswith("</"):
            depth -= 1
            if indent != 2 * depth:
                bad = bad or (i, f"closing tag indent {indent}, expected {2 * depth}")
            continue
        m1 = ONELINE_RE.match(s)
        if m1:
            if indent != 2 * depth:
                bad = bad or (i, f"indent {indent}, expected {2 * depth}")
            if m1.group(3) != m1.group(3).strip():
                bad = bad or (i, "primitive content not whitespace-normalized")
            names = ATTR_RE.findall(m1.group(2))
            if names != sorted(names):
                bad = bad or (i, "attributes not sorted alphabetically")
            if len(names) > 1:
                bad = bad or (i, "more than one attribute must each be on its own line")
            continue
        m2 = OPEN_RE.match(s)
        if m2:
            if indent != 2 * depth:
                bad = bad or (i, f"indent {indent}, expected {2 * depth}")
            names = ATTR_RE.findall(m2.group(2))
            if names != sorted(names):
                bad = bad or (i, "attributes not sorted alphabetically")
            if len(names) > 1:
                bad = bad or (i, "more than one attribute must each be on its own line")
            depth += 1
            continue
        bad = bad or (i, f"unrecognised layout: {s[:50]}")
    if bad:
        v.append(("TPS_ASR_00019", f"line {bad[0]}: {bad[1]}"))
    if not text.endswith("\n"):
        v.append(("TPS_ASR_00019", "file does not end with a newline"))
    return v


def main(argv):
    files = []
    quiet = "-q" in argv
    targets = [a for a in argv if not a.startswith("-")] or ["."]
    for a in targets:
        p = Path(a)
        files += sorted(p.rglob("*.arxml")) if p.is_dir() else [p]
    tally, bad_files = Counter(), 0
    for f in files:
        viol = check(f)
        if viol:
            bad_files += 1
            for rule, msg in viol:
                tally[rule] += 1
                if not quiet:
                    print(f"{f}: [{rule}] {msg}")
    print(f"\nchecked {len(files)} files: {len(files) - bad_files} clean, {bad_files} with violations")
    for rule, n in sorted(tally.items()):
        print(f"  {rule}: {n} file(s)")
    return 1 if bad_files else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
