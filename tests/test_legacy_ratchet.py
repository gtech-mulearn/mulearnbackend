from pathlib import Path

import pytest

from scripts.legacy_ratchet import main

BASELINE = Path(__file__).resolve().parent / "legacy_baseline.txt"

OUTCOMES = {
    "passed": "",
    "failed": '<failure message="assert 0">trace</failure>',
    "error": '<error message="failed on setup">trace</error>',
    "skipped": '<skipped type="pytest.skip" message="skip">skip</skipped>',
}


def case(name, outcome="passed", file="api/a/tests.py", classname="api.a.tests"):
    return (
        f'<testcase classname="{classname}" name="{name}" file="{file}" line="1" time="0.01">'
        f"{OUTCOMES[outcome]}</testcase>"
    )


def write_report(tmp_path, *cases):
    path = tmp_path / "legacy.xml"
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest">'
        + "".join(cases)
        + "</testsuite></testsuites>",
        encoding="utf-8",
    )
    return path


def write_baseline(tmp_path, *ids):
    path = tmp_path / "baseline.txt"
    path.write_text("# header\n" + "".join(f"{i}\n" for i in ids), encoding="utf-8")
    return path


def run(report, baseline):
    return main([str(report), "--baseline", str(baseline)])


def test_a_failure_not_in_the_baseline_fails(tmp_path, capsys):
    report = write_report(tmp_path, case("test_old", "failed"), case("test_new", "failed"))
    baseline = write_baseline(tmp_path, "api/a/tests.py::test_old")

    assert run(report, baseline) == 1
    err = capsys.readouterr().err
    assert "api/a/tests.py::test_new" in err
    assert "api/a/tests.py::test_old" not in err


def test_an_error_not_in_the_baseline_fails(tmp_path, capsys):
    report = write_report(tmp_path, case("test_new", "error"))

    assert run(report, write_baseline(tmp_path)) == 1
    assert "api/a/tests.py::test_new" in capsys.readouterr().err


def test_failures_and_errors_in_the_baseline_pass(tmp_path):
    report = write_report(tmp_path, case("test_f", "failed"), case("test_e", "error"), case("test_ok"))
    baseline = write_baseline(tmp_path, "api/a/tests.py::test_e", "api/a/tests.py::test_f")

    assert run(report, baseline) == 0


def test_a_baseline_test_that_now_passes_is_reported_without_failing(tmp_path, capsys):
    report = write_report(tmp_path, case("test_fixed"), case("test_still", "failed"))
    baseline = write_baseline(tmp_path, "api/a/tests.py::test_fixed", "api/a/tests.py::test_still")

    assert run(report, baseline) == 0
    out = capsys.readouterr().out
    assert "no longer fail" in out
    assert "api/a/tests.py::test_fixed" in out
    assert "api/a/tests.py::test_still" not in out


def test_a_baseline_test_missing_from_the_run_is_reported_without_failing(tmp_path, capsys):
    report = write_report(tmp_path, case("test_ok"))
    baseline = write_baseline(tmp_path, "api/a/tests.py::test_deleted")

    assert run(report, baseline) == 0
    out = capsys.readouterr().out
    assert "didn't run" in out
    assert "api/a/tests.py::test_deleted" in out


@pytest.mark.parametrize(
    ("file", "classname", "name", "node_id"),
    [
        ("api/a/tests.py", "api.a.tests", "test_x", "api/a/tests.py::test_x"),
        ("api/a/tests.py", "api.a.tests.TestThing", "test_y", "api/a/tests.py::TestThing::test_y"),
        (
            "api/a/tests.py",
            "api.a.tests.TestOuter.TestInner",
            "test_z[a::b]",
            "api/a/tests.py::TestOuter::TestInner::test_z[a::b]",
        ),
        ("api\\a\\tests.py", "api.a.tests", "test_x", "api/a/tests.py::test_x"),
        # A module that fails to import: pytest records it with an empty classname.
        ("api/a/tests.py", "", "api.a.tests", "api/a/tests.py"),
    ],
)
def test_node_ids_are_rebuilt_from_the_junit_attributes(tmp_path, capsys, file, classname, name, node_id):
    report = write_report(tmp_path, case(name, "failed", file=file, classname=classname))

    assert run(report, write_baseline(tmp_path)) == 1
    assert f"  {node_id}\n" in capsys.readouterr().err
    assert run(report, write_baseline(tmp_path, node_id)) == 0


def test_skipped_tests_dont_fail(tmp_path):
    assert run(write_report(tmp_path, case("test_s", "skipped")), write_baseline(tmp_path)) == 0


def test_comments_and_blank_lines_in_the_baseline_are_ignored(tmp_path):
    report = write_report(tmp_path, case("test_f", "failed"))
    baseline = tmp_path / "baseline.txt"
    baseline.write_text("# a comment\n\n  api/a/tests.py::test_f  \n\n# another\n", encoding="utf-8")

    assert run(report, baseline) == 0


def test_a_missing_report_fails(tmp_path, capsys):
    assert run(tmp_path / "absent.xml", write_baseline(tmp_path)) == 2
    assert "absent.xml" in capsys.readouterr().err


def test_an_unparsable_report_fails(tmp_path, capsys):
    report = tmp_path / "legacy.xml"
    report.write_text("<testsuites><testsuite>", encoding="utf-8")

    assert run(report, write_baseline(tmp_path)) == 2
    assert "Can't parse" in capsys.readouterr().err


def test_a_report_with_no_tests_fails(tmp_path, capsys):
    assert run(write_report(tmp_path), write_baseline(tmp_path)) == 2
    assert "no tests" in capsys.readouterr().err


def test_a_report_without_file_attributes_fails(tmp_path, capsys):
    report = write_report(tmp_path, '<testcase classname="api.a.tests" name="test_x" time="0.01"/>')

    assert run(report, write_baseline(tmp_path)) == 2
    assert "junit_family = xunit1" in capsys.readouterr().err


def test_the_baseline_is_sorted_unique_test_ids_under_a_shrink_only_header():
    lines = BASELINE.read_text(encoding="utf-8").splitlines()
    header = [line for line in lines if line.startswith("#")]
    ids = [line for line in lines if line and not line.startswith("#")]

    assert lines[: len(header)] == header, "comments belong in the header only"
    assert "only shrinks" in " ".join(header)
    assert ids, "the baseline lists today's failures"
    assert ids == sorted(set(ids))
    for node_id in ids:
        assert node_id == node_id.strip()
        assert node_id.split("::")[0].endswith(".py"), node_id
