"""
Test file redirection behaviour
Note: Assumes the following commands are available:
    cat
    echo
    true
    false
"""

from pipecmd import sh, Command, BaseCommand
import pytest
from pathlib import Path

# Test redirection on Command / CommandChain / AndChain / OrChain
REDIRECT_COMMANDS_ECHO = [
    sh.echo["test"],
    sh.echo["test"] | sh.cat,
    sh.true & sh.echo["test"],
    sh.false ^ sh.echo["test"],
]
# For passthrough stream tests (test single command and pipeline)
REDIRECT_COMMANDS_CAT = [sh.cat, sh.cat | sh.cat]


@pytest.mark.parametrize("command", REDIRECT_COMMANDS_ECHO)
# cmd > file vs file < cmd
@pytest.mark.parametrize("reverse", [True, False])
# Test redirecting outer chain vs redirecting  final command in chain.
@pytest.mark.parametrize("redirect_outer", [True, False])
def test_redirect_output(command: Command, tmp_path: Path, reverse: bool, redirect_outer: bool) -> None:
    """Test redirect to file path

    Test both dirs (file < cmd,  cmd > file)
    """
    path = tmp_path / "out.txt"

    # Test string and path equivalent.
    for conv in [str, Path]:
        outfile = conv(path)

        # Ensure redirecting on final command is equivalent to redirecting on
        # chain.
        # Ie (echo["test"] | cat > file) is eqivalent to (echo["test"] | cat) > file
        if redirect_outer:
            cmd = (outfile < command) if reverse else (command > outfile)
        else:
            final_cmd = (outfile < sh.cat) if command else (sh.cat > outfile)
            cmd = command | final_cmd

        cmd.run()
        assert path.read_text() == "test\n"
        # Ensure overwrites.
        cmd.run()
        assert path.read_text() == "test\n"
        path.unlink()


@pytest.mark.parametrize("command", REDIRECT_COMMANDS_ECHO)
@pytest.mark.parametrize("reverse", [True, False])
@pytest.mark.parametrize("use_path", [True, False])
def test_redirect_output_append(command: Command, tmp_path: Path, reverse: bool, use_path: bool) -> None:
    """Rest redirect to path, str path, file, stringIO and /dev/null.

    Test both dirs (file < cmd,  cmd > file)
    """
    path = tmp_path / "out.txt"
    # Test both string and Path object
    outfile = path if use_path else str(path)

    cmd = (outfile << command) if reverse else (command >> outfile)
    cmd.run()
    assert path.read_text() == "test\n"
    cmd.run()
    assert path.read_text() == "test\ntest\n"
    path.unlink()


@pytest.mark.parametrize("command", REDIRECT_COMMANDS_ECHO)
@pytest.mark.parametrize("reverse", [True, False])
@pytest.mark.parametrize("shift", [True, False])
def test_redirect_output_file(command: BaseCommand, tmp_path: Path, reverse: bool, shift: bool) -> None:
    """Test redirect to file object or dev/null
    >> vs > works the same for file objects (since already opened), but supported for consistency
    (should behave identically)
    """
    path = tmp_path / "out.txt"
    for mode in ["wb", "w"]:
        with open(path, mode) as f:
            if shift:
                cmd = (f << command) if reverse else (command >> f)
            else:
                cmd = (f < command) if reverse else (command > f)
            cmd.run()
        assert path.read_text() == "test\n"

    # Check >/dev/null
    # TODO: Check output suppressed?
    if shift:
        cmd = (None << command) if reverse else (command >> None)
    else:
        cmd = (None < command) if reverse else (command > None)
    assert cmd.run().stdout is None


@pytest.mark.parametrize("command", REDIRECT_COMMANDS_ECHO)
def test_no_redirect(command: BaseCommand, capfd: pytest.CaptureFixture[str]) -> None:
    """Check with no file redirection, output sent to stdout normally"""
    assert command.run().stdout is None
    out = capfd.readouterr()
    assert out.out == "test\n"


@pytest.mark.parametrize("command", REDIRECT_COMMANDS_ECHO)
@pytest.mark.parametrize("reverse", [True, False])
@pytest.mark.parametrize("shift", [True, False])
def test_redirect_output_none(
    command: BaseCommand, reverse: bool, shift: bool, capfd: pytest.CaptureFixture[str]
) -> None:
    """Redirect to None shortcut for DEVNULL"""
    if shift:
        cmd = (None << command) if reverse else (command >> None)
    else:
        cmd = (None < command) if reverse else (command > None)
    assert cmd.run().stdout is None
    out = capfd.readouterr()
    assert out.out == ""


@pytest.mark.parametrize("command", REDIRECT_COMMANDS_CAT)
@pytest.mark.parametrize("reverse", [True, False])
@pytest.mark.parametrize("shift", [True, False])
@pytest.mark.parametrize("use_path", [True, False])
def test_redirect_input(tmp_path: Path, command: BaseCommand, reverse: bool, shift: bool, use_path: bool) -> None:
    """Rest redirect to path, str path, file, stringIO and /dev/null.

    Test both dirs (cmd < file,  file > cmd)

    >> Is also supported, but acts identically to > for inputs.
    """
    path = tmp_path / "input.txt"
    path.write_text("1234")

    infile = path if use_path else str(path)

    if shift:
        cmd = (infile >> command) if reverse else (command << infile)
    else:
        cmd = (infile > command) if reverse else (command < infile)
    assert str(cmd) == "1234"


@pytest.mark.parametrize("command", REDIRECT_COMMANDS_CAT)
@pytest.mark.parametrize("reverse", [True, False])
@pytest.mark.parametrize("shift", [True, False])
@pytest.mark.parametrize("mode", ["r", "rb"])
def test_redirect_input_file(command: BaseCommand, tmp_path: Path, reverse: bool, shift: bool, mode: str) -> None:
    """Test redirect to file object or dev/null
    >> vs > works the same for file objects (since already opened), but supported for consistency
    (should behave identically)
    """
    path = tmp_path / "input.txt"
    path.write_text("1234")

    with open(path, mode) as f:
        if shift:
            cmd = (f >> command) if reverse else (command << f)
        else:
            cmd = (f > command) if reverse else (command < f)
        cmd.run()
    assert path.read_text() == "1234"


@pytest.mark.parametrize("command", REDIRECT_COMMANDS_CAT)
@pytest.mark.parametrize("reverse", [True, False])
@pytest.mark.parametrize("shift", [True, False])
def test_redirect_input_none(command: BaseCommand, reverse: bool, shift: bool) -> None:
    if shift:
        cmd = (None >> command) if reverse else (command << None)
    else:
        cmd = (None > command) if reverse else (command < None)
    assert str(cmd) == ""


def test_chain_redirection_and(tmp_path: Path) -> None:
    # Test complex chain with multiple redirections of seperate commands.
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file3 = tmp_path / "file3.txt"

    cmd = sh.true & (sh.echo["a"] > file1) & (sh.echo["b"] > file2) & sh.false & (sh.echo["c"] > file3)
    cmd()
    assert file1.read_text() == "a\n"
    assert file2.read_text() == "b\n"
    assert not file3.exists()


def test_chain_redirection_or(tmp_path: Path) -> None:
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"

    cmd = sh.false ^ (sh.echo["a"] > file1) ^ (sh.echo["b"] > file2)
    cmd()
    assert file1.read_text() == "a\n"
    assert not file2.exists()
