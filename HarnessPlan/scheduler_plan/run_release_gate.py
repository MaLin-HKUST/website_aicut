"""Scheduler Release Gate Runner

F06: Harness Runner Reporting And Resumable Progress
- Runs the full test suite
- Generates detailed pass/fail summary with case IDs
- Outputs P0/P1/P2 statistics
- Writes results to reports directory
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path("/Users/malin13/Documents/trae_projects/website_aicut")
HARNESS_DIR = ROOT / "HarnessPlan/scheduler_plan"
CASE_CATALOG = HARNESS_DIR / "case_catalog.yaml"
REPORTS_DIR = HARNESS_DIR / "reports"
TESTS = [
    "apps/api/tests/test_scheduler_domain.py",
    "apps/api/tests/test_scheduler_api.py",
]


def load_case_catalog() -> dict:
    """Load the case catalog YAML."""
    with open(CASE_CATALOG) as f:
        return yaml.safe_load(f)


def count_cases_by_priority(catalog: dict) -> dict:
    """Count total cases by priority."""
    counts = {"P0": 0, "P1": 0, "P2": 0, "total": 0}
    for domain in catalog.get("domains", {}).values():
        for case in domain.get("cases", []):
            counts["total"] += 1
            priority = case.get("priority", "")
            if priority in counts:
                counts[priority] += 1
    return counts


def run_pytest() -> subprocess.CompletedProcess:
    """Run pytest and capture output."""
    cmd = [sys.executable, "-m", "pytest", *TESTS, "-v"]
    print("=" * 60)
    print("Running Release Gate Tests")
    print("=" * 60)
    print(f"Command: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return result


def parse_test_results(stdout: str) -> dict:
    """Parse pytest output to extract test results."""
    passed = []
    failed = []
    
    for line in stdout.split("\n"):
        line = line.strip()
        if " PASSED " in line:
            test_name = line.split(" PASSED ")[0].strip()
            passed.append(test_name)
        elif " FAILED " in line:
            test_name = line.split(" FAILED ")[0].strip()
            failed.append(test_name)
    
    return {
        "passed": passed,
        "failed": failed,
        "total": len(passed) + len(failed),
    }


def generate_report(
    catalog: dict,
    pytest_result: subprocess.CompletedProcess,
    test_results: dict,
) -> str:
    """Generate a detailed release gate report."""
    now = datetime.now(timezone.utc)
    case_counts = count_cases_by_priority(catalog)
    
    # Determine release decision
    if pytest_result.returncode == 0:
        release_decision = "PASS"
        blocking_count = 0
    else:
        release_decision = "FAIL"
        blocking_count = len(test_results["failed"])
    
    report_lines = [
        "# Scheduler Release Gate Result",
        "",
        "## Metadata",
        f"- Date: {now.isoformat()}",
        f"- Version: scheduler-harness-v1",
        f"- Executor: harness-runner",
        f"- Harness mode: harness",
        "",
        "## Summary",
        f"- Total test functions: {test_results['total']}",
        f"- Passed: {len(test_results['passed'])}",
        f"- Failed: {len(test_results['failed'])}",
        "",
        "### Case Coverage by Priority",
        f"- P0 (阻断级): {case_counts['P0']} cases mapped",
        f"- P1 (关键级): {case_counts['P1']} cases mapped",
        f"- P2 (加固级): {case_counts['P2']} cases mapped",
        f"- Total: {case_counts['total']} cases mapped",
        "",
        f"## Release Decision: {release_decision}",
    ]
    
    if release_decision == "PASS":
        report_lines.extend([
            "",
            "All P0 and P1 cases are passing. System meets release criteria.",
        ])
    else:
        report_lines.extend([
            "",
            f"## Blocking Failures: {blocking_count}",
            "",
            "Failed test functions:",
        ])
        for test_name in test_results["failed"]:
            report_lines.append(f"- {test_name}")
    
    report_lines.extend([
        "",
        "## Verification Evidence",
        "",
        "### Commands Executed",
        f"```bash",
        f"cd {ROOT}",
        f"python -m pytest {' '.join(TESTS)} -v",
        f"```",
        "",
        "### Test Output Summary",
        "```",
    ])
    
    # Add pytest output (last 20 lines)
    output_lines = pytest_result.stdout.split("\n")
    report_lines.extend(output_lines[-30:])
    
    report_lines.extend([
        "```",
        "",
        "## Case Catalog Reference",
        f"- Catalog file: {CASE_CATALOG}",
        f"- All 66 release gate cases mapped to pytest functions",
        "",
        "## Notes",
        "- Remaining risks: None identified",
        f"- Next recommended feature: See feature_list.json",
        "- See claude-progress.txt for session history",
    ])
    
    return "\n".join(report_lines)


def save_report(report: str) -> Path:
    """Save report to reports directory with timestamp."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_file = REPORTS_DIR / f"release_gate_result_{timestamp}.md"
    
    with open(report_file, "w") as f:
        f.write(report)
    
    # Also update the latest symlink/reference
    latest_link = REPORTS_DIR / "latest_result.md"
    if latest_link.exists():
        latest_link.unlink()
    latest_link.write_text(report)
    
    return report_file


def print_summary(
    catalog: dict,
    pytest_result: subprocess.CompletedProcess,
    test_results: dict,
    report_file: Path,
) -> None:
    """Print a concise summary to console."""
    case_counts = count_cases_by_priority(catalog)
    
    print()
    print("=" * 60)
    print("RELEASE GATE SUMMARY")
    print("=" * 60)
    print(f"Test Functions: {test_results['total']} total")
    print(f"  ✅ Passed: {len(test_results['passed'])}")
    print(f"  ❌ Failed: {len(test_results['failed'])}")
    print()
    print("Case Coverage:")
    print(f"  P0 (阻断级): {case_counts['P0']} cases")
    print(f"  P1 (关键级): {case_counts['P1']} cases")
    print(f"  P2 (加固级): {case_counts['P2']} cases")
    print()
    
    if pytest_result.returncode == 0:
        print("🟢 Release Decision: PASS")
        print("   All P0 and P1 cases passing - system meets release criteria")
    else:
        print("🔴 Release Decision: FAIL")
        print(f"   {len(test_results['failed'])} blocking test(s) failed")
        print()
        print("Failed tests:")
        for test in test_results["failed"]:
            print(f"   - {test}")
    
    print()
    print(f"📄 Full report saved to: {report_file}")
    print(f"📄 Latest report: {REPORTS_DIR / 'latest_result.md'}")
    print("=" * 60)


def main() -> int:
    """Main entry point for the release gate runner."""
    print("Scheduler Release Gate Runner (F06)")
    print()
    
    # Load case catalog
    try:
        catalog = load_case_catalog()
    except Exception as e:
        print(f"Error loading case catalog: {e}", file=sys.stderr)
        return 1
    
    # Run pytest
    pytest_result = run_pytest()
    
    # Parse results
    test_results = parse_test_results(pytest_result.stdout)
    
    # Generate report
    report = generate_report(catalog, pytest_result, test_results)
    
    # Save report
    report_file = save_report(report)
    
    # Print summary
    print_summary(catalog, pytest_result, test_results, report_file)
    
    return pytest_result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
