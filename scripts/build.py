"""Build the Upworthy project from the raw OSF files: every step in order, then its tests.

Run from the project root:   python3 scripts/build.py
Steps: 00 profile -> 01 load -> 02 clean -> tests -> independent checks. Writes docs/data_profile.md,
docs/cleaning_log.md and docs/validation_report.md. Stops on the first failing test (rule 9).
"""
import datetime as dt
import importlib.util
import inspect
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEPS = ["pipeline/00_profile/profile.py", "pipeline/01_load/load.py", "pipeline/02_clean/clean.py"]
CHECKS = ["scripts/checks/verify_profile.py", "scripts/checks/verify_clean.py"]


def run(script):
    print(f"\n== {script}")
    if subprocess.run([sys.executable, os.path.join(ROOT, script)], cwd=ROOT).returncode != 0:
        sys.exit(f"Build stopped: {script} failed")


def run_tests():
    results = []
    for fn in sorted(os.listdir(os.path.join(ROOT, "tests"))):
        if not (fn.startswith("test_") and fn.endswith(".py")):
            continue
        spec = importlib.util.spec_from_file_location(fn[:-3], os.path.join(ROOT, "tests", fn))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name, f in inspect.getmembers(mod, inspect.isfunction):
            if name.startswith("test_") and f.__module__ == mod.__name__:
                failing = f()
                results.append((fn, name, (f.__doc__ or "").strip(), len(failing), failing.head(10)))
                print(f"  [{'pass' if len(failing) == 0 else 'FAIL'}] {name}" + (f"  ({len(failing)} failing rows)" if len(failing) else ""))
    return results


def write_reports(results):
    sys.path.insert(0, os.path.join(ROOT, "pipeline"))
    from common import load_table
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = ["# Validation Report", "", f"Generated {now} by `scripts/build.py`. Each test returns zero failing rows when it passes.", "",
             "| File | Test | Result | Failing rows |", "|---|---|---|---|"]
    lines += [f"| {fn} | `{name}` | {'✅ pass' if n == 0 else '❌ FAIL'} | {n} |" for fn, name, _, n, _ in results]
    lines += [""] + [f"**`{name}`**: {doc}" + ("" if n == 0 else f"\n\n```\n{sample.to_string()}\n```") + "\n" for _, name, doc, n, sample in results]
    open(os.path.join(ROOT, "docs", "validation_report.md"), "w", encoding="utf-8").write("\n".join(lines))

    a = load_table("02_clean/cleaning_audit", content_blind=True)
    log = ["# Cleaning Log", "", f"Generated {now} by `scripts/build.py` from `build/02_clean/cleaning_audit` "
           "(computed in `pipeline/02_clean/clean.py`). Every number is measured from the data on each build.", "",
           "**Principle: flag, don't delete.** Every package row is kept; problems become flag columns, raw text stays "
           "beside cleaned text, and each analysis states which flags it excludes. Rules approved by Sanjay 2026-11-04 (NOTES §4.2).", ""]
    for s in a.split.unique():
        q = a[a.split == s]
        log += [f"## {s.capitalize()}", "", "| Rule | What | Table | Action | Affected | Of | Why |", "|---|---|---|---|---|---|---|"]
        log += [f"| {r.rule} | {r.what} | {r.table} | {r.action} | {r.affected:,} | {r.total:,} | {r.why} |" for r in q.itertuples()]
        log += [""]
    open(os.path.join(ROOT, "docs", "cleaning_log.md"), "w", encoding="utf-8").write("\n".join(log))


if __name__ == "__main__":
    for s in STEPS:
        run(s)
    print("\n== tests")
    results = run_tests()
    write_reports(results)
    n_fail = sum(1 for r in results if r[3])
    if n_fail:
        sys.exit(f"Build stopped: {n_fail} test(s) failed. See docs/validation_report.md")
    for c in CHECKS:
        run(c)
    print(f"\nBuild OK: {len(results)}/{len(results)} tests passed")
