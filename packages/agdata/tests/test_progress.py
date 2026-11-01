import io

from agdata.progress import Reporter


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def reporter(quiet=False):
    out, err, clock = io.StringIO(), io.StringIO(), Clock()
    return Reporter(out=out, err=err, quiet=quiet, every_s=10, clock=clock), out, err, clock


def lines(stream):
    return [line[9:] if line[:2].isdigit() else line for line in stream.getvalue().splitlines()]  # no time stamps


def test_progress_is_throttled_and_says_how_long_is_left():
    report, out, _, clock = reporter()
    report.progress("months", 0, 4)
    clock.now = 5
    report.progress("months", 1, 4)  # within 10 s of the last line: skipped
    clock.now = 60
    report.progress("months", 2, 4)
    clock.now = 61
    report.progress("months", 4, 4)  # the last always shows
    assert lines(out) == ["months: 0/4 (0%), 0 s", "months: 2/4 (50%), 60 s, ~60 s left", "months: 4/4 (100%), 61 s"]


def test_quiet_keeps_steps_off_the_terminal_but_not_failures():
    report, out, err, clock = reporter(quiet=True)
    report.step("reading")
    report.warn("slow")
    report.fail("2025-01", RuntimeError("queue full"))
    clock.now = 200
    assert report.finish("1 of 2 written") is False
    assert out.getvalue() == ""
    assert lines(err) == [
        "warning: slow",
        "failed: 2025-01: RuntimeError('queue full')",
        "Done in 3 min: 1 of 2 written; 1 warning; 1 failed:",
        "  2025-01: RuntimeError('queue full')",
    ]


def test_a_clean_run_finishes_on_stdout():
    report, out, err, _ = reporter()
    assert report.finish() is True
    assert lines(out) == ["Done in 0 s"] and err.getvalue() == ""
