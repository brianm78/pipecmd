"""
Test invoking via runner
"""

from pipecmd import sh, run, bg
import pytest
import subprocess


def test_run_nocap(capfd: pytest.CaptureFixture[str]) -> None:
    p = sh.echo["test"] | run
    assert p.stdout is None
    out, err = capfd.readouterr()
    assert out == "test\n"


def test_run_cap(capfd: pytest.CaptureFixture[str]) -> None:
    p = sh.echo["test"] | run(capture=True)
    assert p.stdout is not None
    assert p.stdout.read() == b"test\n"
    out, err = capfd.readouterr()
    assert out == ""


def test_get_output(capfd: pytest.CaptureFixture[str]) -> None:
    strVal = sh.echo["test"] | run(from_str=str)
    assert strVal == "test\n"

    bytesVal = sh.echo["test"] | run(from_bytes=bytes)
    assert bytesVal == b"test\n"

    intVal = sh.echo["-n", "123"] | run(from_str=int)
    assert intVal == 123
    intVal = sh.echo["-n", "123"] | run(from_bytes=lambda x: int(x.decode("utf8")))
    assert intVal == 123

    out, err = capfd.readouterr()
    assert out == ""  # Did not echo to screen.


def test_bg(capfd: pytest.CaptureFixture[str]) -> None:
    p = sh.sleep["1"] | bg
    assert p.returncode is None
    assert p.stdout is None


def test_check() -> None:
    # Default unchecked
    _ = sh.false | run

    with pytest.raises(subprocess.CalledProcessError):
        _ = sh.false | run(check=True)
