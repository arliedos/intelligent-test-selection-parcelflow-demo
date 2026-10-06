#!/usr/bin/env python3
"""Single documented test command for the ParcelFlow demo.

Usage:
    python scripts/run_tests.py

Runs the full Python stdlib `unittest` suite under `tests/`, plus the Node
built-in test runner for `ui/assets/*.test.js` if `node` is available on
PATH. Writes a JUnit-style XML report and a plain-text summary to
`reports/` (gitignored). Exit code is non-zero if anything failed.

No fabricated execution records: this script only reports what it actually
ran, with real pass/fail counts and real durations from this invocation.
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import time
import unittest
import xml.etree.ElementTree as ET

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(REPO_ROOT, "reports")


def run_python_suite():
    sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
    sys.path.insert(0, REPO_ROOT)

    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(REPO_ROOT, "tests"), pattern="test_*.py")

    cases = []

    def _collect(s):
        for item in s:
            if isinstance(item, unittest.TestSuite):
                _collect(item)
            else:
                cases.append(item)

    _collect(suite)

    results = []
    for case in cases:
        result = unittest.TestResult()
        start = time.time()
        case.run(result)
        duration = time.time() - start
        results.append((case, result, duration))
    return results


def run_node_suite():
    node = shutil.which("node")
    if not node:
        return None
    js_tests = glob.glob(os.path.join(REPO_ROOT, "ui", "assets", "*.test.js"))
    if not js_tests:
        return None
    proc = subprocess.run(
        [node, "--test", *js_tests],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return proc


def _test_id(case) -> str:
    return case.id()


def build_junit_xml(results, node_proc) -> ET.Element:
    root = ET.Element("testsuite", name="parcelflow-demo")
    total = passed = failed = errors = 0

    for case, result, duration in results:
        total += 1
        testcase = ET.SubElement(
            root, "testcase", classname=_test_id(case).rsplit(".", 1)[0], name=_test_id(case).rsplit(".", 1)[-1],
            time=f"{duration:.4f}",
        )
        if result.errors:
            errors += 1
            failure = ET.SubElement(testcase, "error")
            failure.text = result.errors[0][1]
        elif result.failures:
            failed += 1
            failure = ET.SubElement(testcase, "failure")
            failure.text = result.failures[0][1]
        else:
            passed += 1

    if node_proc is not None:
        node_testcase = ET.SubElement(root, "testcase", classname="ui.assets", name="node_test_runner", time="0")
        if node_proc.returncode != 0:
            failure = ET.SubElement(node_testcase, "failure")
            failure.text = node_proc.stdout + "\n" + node_proc.stderr

    root.set("tests", str(total + (1 if node_proc is not None else 0)))
    root.set("failures", str(failed))
    root.set("errors", str(errors + (1 if node_proc is not None and node_proc.returncode != 0 else 0)))
    return root, total, passed, failed, errors


def main() -> int:
    os.makedirs(REPORTS_DIR, exist_ok=True)

    results = run_python_suite()
    node_proc = run_node_suite()

    root, total, passed, failed, errors = build_junit_xml(results, node_proc)

    junit_path = os.path.join(REPORTS_DIR, "junit.xml")
    ET.ElementTree(root).write(junit_path, encoding="utf-8", xml_declaration=True)

    summary_lines = [
        "ParcelFlow demo test run summary",
        f"python tests: {total} total, {passed} passed, {failed} failed, {errors} errors",
    ]
    if node_proc is not None:
        summary_lines.append(f"node ui tests: exit_code={node_proc.returncode}")
        summary_lines.append(node_proc.stdout)
    else:
        summary_lines.append("node ui tests: skipped (node not found or no *.test.js files)")

    summary_path = os.path.join(REPORTS_DIR, "summary.txt")
    with open(summary_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(summary_lines) + "\n")

    print("\n".join(summary_lines))
    print(f"JUnit report: {junit_path}")
    print(f"Summary: {summary_path}")

    exit_code = 0
    if failed or errors:
        exit_code = 1
    if node_proc is not None and node_proc.returncode != 0:
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
