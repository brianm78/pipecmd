"""
Note: Assumes the following shell commands are available:
    - echo
    - python
    - cat
    - false
    - true

"""

from pipecmd import sh, Command, BaseCommand, CommandDefinition
import pytest
import subprocess

# Command to quickly test content manipulation (reverses input)
PY_REVERSE_CMD = "import sys;print(sys.stdin.read()[::-1], end='')"


def test_create() -> None:
    """Check construction rules from string/list etc"""
    cmds : list[CommandDefinition] = [
        sh.echo["test"],
        "echo test",
        ["echo", "test"],
        Command("echo", ("test",)),
    ]
    for cmd in cmds:
        cmd = Command.make(cmd)
        assert isinstance(cmd, Command)
        assert cmd.cmd == "echo"
        assert list(cmd.args) == ["test"]


@pytest.mark.parametrize("command", [sh.echo["test"], sh.echo["test"] | sh.cat])
def test_pipe_create(command: Command) -> None:
    """Check construction from directly piping"""
    cmd = command | sh.python["-c", PY_REVERSE_CMD]
    assert str(cmd) == "\ntset"

    # String (with quotes and spaces)
    cmd = command | f'python -c "{PY_REVERSE_CMD}"'
    assert str(cmd) == "\ntset"

    # list
    cmd = command | ["python", "-c", PY_REVERSE_CMD]
    assert str(cmd) == "\ntset"


@pytest.mark.parametrize("command", [sh.echo["test"], sh.echo["test"] | sh.cat])
def test_run(command: BaseCommand) -> None:
    p = command.run(stdout=subprocess.PIPE, encoding="utf8")
    assert p.stdout is not None
    assert p.stdout.read() == "test\n"
    assert p.returncode == 0

    p = command.run(stdout=subprocess.PIPE)
    assert p.stdout is not None
    assert p.stdout.read() == b"test\n"
    assert p.returncode == 0


@pytest.mark.parametrize("command", [sh.echo["test"], sh.echo["test"] | sh.cat])
def test_call(command: Command) -> None:
    p = command(stdout=subprocess.PIPE, encoding="utf8")
    assert p.stdout is not None
    assert p.stdout.read() == "test\n"
    assert p.returncode == 0

    p = command(stdout=subprocess.PIPE)
    assert p.stdout is not None
    assert p.stdout.read() == b"test\n"
    assert p.returncode == 0


@pytest.mark.parametrize("command", [sh.echo["test"], sh.echo["test"] | sh.cat])
def test_bg(command: Command) -> None:
    p = command.bg(stdout=subprocess.PIPE, encoding="utf8")
    assert p.stdout is not None
    assert p.stdout.read() == "test\n"


@pytest.mark.parametrize("command", [sh.echo["test"], sh.echo["test"] | sh.cat])
def test_str_bytes(command: Command) -> None:
    assert str(command) == "test\n"
    assert bytes(command) == b"test\n"


@pytest.mark.parametrize("command", [sh.echo["a\nb\nc"], sh.echo["a\nb\nc"] | sh.cat])
def test_iter(command: BaseCommand) -> None:
    assert list(command) == ["a\n", "b\n", "c\n"]



def test_chain_and() -> None:
    """Test short-circuit && chaining."""
    cmd = sh.false & sh.echo["test"]
    assert str(cmd) == ""

    # Test chain of multiple
    cmd = sh.true & sh.false & sh.echo["test"]
    assert str(cmd) == ""

    # Check success case
    cmd = sh.true & sh.echo["test"]
    assert str(cmd) == "test\n"

    cmd = sh.true & sh.true & sh.echo["test"]
    assert str(cmd) == "test\n"


# Check both single and multiple chains.
def test_chain_or() -> None:
    """Test short-circuit || chaining."""
    cmd = sh.true ^ sh.echo["test"]
    assert str(cmd) == ""

    # Check multiple chain
    cmd = sh.false ^ sh.true ^ sh.echo["test"]
    assert str(cmd) == ""

    cmd = sh.false ^ sh.echo["test"]
    assert str(cmd) == "test\n"

    cmd = sh.false ^ sh.false ^ sh.echo["test"]
    assert str(cmd) == "test\n"

@pytest.mark.parametrize(
    "expected",
    [
        (sh.ls, "Command('ls')"),
        (sh.ls["-l"], "Command('ls', ['-l'])"),
        (sh.ls["-l", "--color"], "Command('ls', ['-l', '--color'])"),
        (sh.ls | sh.cat, "Command('ls') | Command('cat')"),
        (sh.ls & sh.cat, "Command('ls') && Command('cat')"),
        (sh.ls ^ sh.cat, "Command('ls') || Command('cat')"),
    ],
)
def test_repr(expected: tuple[BaseCommand, str]) -> None:
    cmd, res = expected
    assert repr(cmd) == res
