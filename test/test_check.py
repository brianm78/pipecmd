"""
Test raising / not raising behaviour on success/failure returncodes
Assumes the following commands exist:
    echo
    cat
    false
    true

"""
from pipecmd import sh, BaseCommand, checked
import pytest
import subprocess

@pytest.mark.parametrize("command", [sh.false, sh.echo[""] | sh.false])
def test_returncode_fails(command: BaseCommand) -> None:
    with pytest.raises(subprocess.CalledProcessError):
        command.run(check=True)
    with pytest.raises(subprocess.CalledProcessError):
        command(check=True)

    with pytest.raises(subprocess.CalledProcessError):
        command.run(check=0)
    with pytest.raises(subprocess.CalledProcessError):
        command(check=0)

@pytest.mark.parametrize("command", [sh.echo, sh.echo[""] | sh.cat, sh.false | sh.echo])
def test_returncode_succeeds(command: BaseCommand) -> None:
    command.run(check=True)
    command(check=True)
    command.run(check=0)
    command(check=0)


# TODO: Check propagation.  Check default is non-raise.
@pytest.mark.parametrize("command", [sh.false, sh.echo[""] | sh.false])
def test_unchecked(command: BaseCommand) -> None:
    """If check is false, no error raised"""
    command.run()
    command()


@pytest.mark.parametrize("command", [checked.echo, checked.echo[""] | checked.cat, checked.false | checked.echo])
def test_checked_succeeds(command: BaseCommand) -> None:
    command.run()
    command()
    command.run()
    command()


# TODO: Check propagation.  Check default is non-raise.
@pytest.mark.parametrize("command", [checked.false, checked.echo[""] | checked.false])
def test_checked_fail(command: BaseCommand) -> None:
    with pytest.raises(subprocess.CalledProcessError):
        command.run()
    with pytest.raises(subprocess.CalledProcessError):
        command()

