#!/usr/bin/env python3
"""
Comprehensive Automated Scenario Test Runner
============================================
Runs the ARXML SecDiff security validation pipeline across all real-world
automotive benchmark scenarios, measures execution time, validates gate verdicts
against ground truth, and outputs a formatted terminal report.

Usage:
  python test_all_scenarios.py                  # Runs realistic dataset (default)
  python test_all_scenarios.py --dataset all    # Runs both realistic and original
  python test_all_scenarios.py --json out.json  # Saves benchmark results to JSON
"""

import sys
import time
import argparse
import json
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from arxml_secdiff import pipeline

# Ground truth expected verdicts for the 13 real-world CVE automotive scenarios
EXPECTED_VERDICTS = {
    "01_jeep_uconnect": "BLOCK",
    "02_bmw_connecteddrive": "BLOCK",
    "03_tesla_2016_fix": "PASS",
    "04_mitsubishi_outlander": "FLAG",
    "05_fca_network_fix": "PASS",
    "06_curry_nissan_api": "BLOCK",
    "07_spireon_fleet_admin": "BLOCK",
    "08_someip_deassociation": "BLOCK",
    "09_supply_chain_sdk": "BLOCK",
    "10_kia_telematics_api": "BLOCK",
    "11_toyota_can_injection": "BLOCK",
    "12_secoc_weak_mac": "PASS",
    "13_unannotated_naming_boundary": "BLOCK",
}

# ANSI color codes for terminal formatting
COLOR_GREEN = "\033[92m"
COLOR_RED = "\033[91m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_BOLD = "\033[1m"
COLOR_RESET = "\033[0m"


def format_verdict(verdict: str) -> str:
    if verdict == "BLOCK":
        return f"{COLOR_RED}{COLOR_BOLD}BLOCK{COLOR_RESET}"
    elif verdict == "FLAG":
        return f"{COLOR_YELLOW}{COLOR_BOLD}FLAG{COLOR_RESET}"
    elif verdict == "PASS":
        return f"{COLOR_GREEN}{COLOR_BOLD}PASS{COLOR_RESET}"
    return verdict


def run_scenario_suite(scenarios_dir: Path, suite_label: str):
    print(f"\n{COLOR_BOLD}{COLOR_BLUE}>>> Running Scenario Suite: {suite_label}{COLOR_RESET}")
    print(f"Path: {scenarios_dir}\n")

    results = []
    total_time_start = time.perf_counter()
    all_passed = True

    subdirs = sorted([d for d in scenarios_dir.iterdir() if d.is_dir() and (d / "before.arxml").exists()])

    for sdir in subdirs:
        bef = sdir / "before.arxml"
        aft = sdir / "after.arxml"
        roles = sdir / "roles.yaml"

        start_t = time.perf_counter()
        res = pipeline.run(
            before_sources=[str(bef)],
            updated_sources=[str(aft)],
            roles_config=str(roles) if roles.exists() else None,
        )
        elapsed_ms = (time.perf_counter() - start_t) * 1000

        expected = EXPECTED_VERDICTS.get(sdir.name, "N/A")
        verdict_ok = res.verdict == expected

        if not verdict_ok and expected != "N/A":
            all_passed = False

        status_str = f"{COLOR_GREEN}✓ MATCH{COLOR_RESET}" if verdict_ok else f"{COLOR_RED}✗ MISMATCH (Exp: {expected}){COLOR_RESET}"

        # Risk breakdown
        risk_5 = sum(1 for f in res.findings if getattr(f, "risk", 0) >= 5)

        entry = {
            "scenario": sdir.name,
            "nodes": res.updated.graph.number_of_nodes(),
            "edges": res.updated.graph.number_of_edges(),
            "findings": len(res.findings),
            "risk_5": risk_5,
            "verdict": res.verdict,
            "expected": expected,
            "match": verdict_ok,
            "time_ms": round(elapsed_ms, 1),
        }
        results.append(entry)

        print(
            f"  [{sdir.name}] {format_verdict(res.verdict):<15} | "
            f"Findings: {len(res.findings):>2} | "
            f"Nodes: {res.updated.graph.number_of_nodes():>2} | "
            f"Time: {elapsed_ms:>6.1f} ms | {status_str}"
        )

    total_time_ms = (time.perf_counter() - total_time_start) * 1000

    # Summary Table
    print("\n" + "=" * 80)
    print(f"{'Scenario Name':<32} {'Nodes':>6} {'Edges':>6} {'Findings':>9} {'Verdict':>9} {'Time':>9}")
    print("=" * 80)
    for r in results:
        print(
            f"{r['scenario']:<32} "
            f"{r['nodes']:>6} "
            f"{r['edges']:>6} "
            f"{r['findings']:>9} "
            f"{r['verdict']:>9} "
            f"{r['time_ms']:>7.1f}ms"
        )
    print("=" * 80)

    pass_count = sum(1 for r in results if r["match"])
    print(
        f"Suite Summary: {pass_count}/{len(results)} scenarios matched ground truth. "
        f"Total execution time: {total_time_ms/1000:.2f}s\n"
    )

    return results, all_passed


def main():
    parser = argparse.ArgumentParser(description="Test all ARXML SecDiff scenarios at once.")
    parser.add_argument(
        "--dataset",
        choices=["realistic", "original", "all"],
        default="realistic",
        help="Which scenario dataset to test (default: realistic)",
    )
    parser.add_argument(
        "--json",
        type=str,
        default=None,
        help="Optional path to export benchmark results as JSON",
    )
    args = parser.parse_args()

    realistic_dir = ROOT / "real_time_scenarios_realistic"
    original_dir = ROOT / "real_time_scenarios"

    all_results = {}
    overall_success = True

    if args.dataset in ["realistic", "all"]:
        if realistic_dir.exists():
            res, ok = run_scenario_suite(realistic_dir, "Realistic Dataset (Enterprise AUTOSAR R20-11)")
            all_results["realistic"] = res
            if not ok:
                overall_success = False
        else:
            print(f"Error: {realistic_dir} not found.")
            sys.exit(1)

    if args.dataset in ["original", "all"]:
        if original_dir.exists():
            res, ok = run_scenario_suite(original_dir, "Original Benchmark Dataset")
            all_results["original"] = res
            if not ok:
                overall_success = False
        else:
            print(f"Error: {original_dir} not found.")
            sys.exit(1)

    if args.json:
        out_path = Path(args.json)
        out_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
        print(f"Benchmark results exported to: {out_path.resolve()}")

    if not overall_success:
        print(f"{COLOR_RED}Some scenarios did not match ground-truth verdicts!{COLOR_RESET}")
        sys.exit(1)
    else:
        print(f"{COLOR_GREEN}{COLOR_BOLD}All scenarios verified and matched ground-truth successfully!{COLOR_RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
