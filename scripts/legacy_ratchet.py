"""Fail on legacy test failures that aren't in the recorded baseline (issue 0013).

    scripts/test.sh --junitxml=legacy.xml
    python scripts/legacy_ratchet.py legacy.xml [--baseline tests/legacy_baseline.txt]

Exit codes:
    0  every failing or erroring test is in the baseline
    1  a test that isn't in the baseline fails or errors
    2  the report is missing, unreadable, empty, or lacks the file attributes node ids need

Baseline tests that no longer fail, or didn't run, are printed so their lines can be
deleted. They never fail the check: the baseline only shrinks.
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_BASELINE = Path(__file__).resolve().parent.parent / "tests" / "legacy_baseline.txt"


class ReportError(Exception):
    pass


def node_id(testcase: ET.Element) -> str:
    """Rebuild the pytest node id from a testcase's file, classname and name."""
    file = testcase.get("file")
    if not file:
        raise ReportError(
            "The report has no file attributes, so node ids can't be rebuilt. "
            "pytest.ini must set junit_family = xunit1."
        )
    file = file.replace("\\", "/")
    classname = testcase.get("classname", "")
    name = testcase.get("name", "")
    if not classname:
        # A module that failed to import: its node id is the file itself.
        return file
    module = file.removesuffix(".py").replace("/", ".")
    classes = classname[len(module) + 1 :].split(".") if classname.startswith(module + ".") else []
    return "::".join([file, *classes, name])


def read_report(path: Path) -> tuple[set[str], set[str]]:
    """Return the node ids that ran and the ones that failed or errored."""
    try:
        root = ET.parse(path).getroot()
    except FileNotFoundError as exc:
        raise ReportError(f"No report at {path}: did the test run crash before writing it?") from exc
    except ET.ParseError as exc:
        raise ReportError(f"Can't parse {path}: {exc}") from exc
    ran, failing = set(), set()
    for testcase in root.iter("testcase"):
        test = node_id(testcase)
        ran.add(test)
        if testcase.find("failure") is not None or testcase.find("error") is not None:
            failing.add(test)
    if not ran:
        raise ReportError(f"{path} records no tests.")
    return ran, failing


def read_baseline(path: Path) -> set[str]:
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return {line for line in lines if line and not line.startswith("#")}


def print_list(title: str, ids: set[str], file=None) -> None:
    file = file or sys.stdout
    print(title, file=file)
    for test in sorted(ids):
        print(f"  {test}", file=file)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", type=Path, help="JUnit XML written by scripts/test.sh --junitxml")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args(argv)

    try:
        ran, failing = read_report(args.report)
    except ReportError as exc:
        print(exc, file=sys.stderr)
        return 2
    baseline = read_baseline(args.baseline)

    new = failing - baseline
    fixed = (baseline & ran) - failing
    missing = baseline - ran

    if fixed:
        print_list(f"{len(fixed)} baseline tests no longer fail. Delete their lines from {args.baseline}:", fixed)
    if missing:
        print_list(f"{len(missing)} baseline tests didn't run. Delete their lines if they were removed:", missing)
    if new:
        print_list(f"{len(new)} tests fail that aren't in {args.baseline}:", new, file=sys.stderr)
        print("Fix them. Never add a test to the baseline: it only shrinks.", file=sys.stderr)
        return 1
    print(f"{len(failing)} failing tests, all in the baseline. {len(ran) - len(failing)} pass or skip.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
