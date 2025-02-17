from __future__ import annotations
import subprocess
import typing
import dataclasses
from .types import Undefined

if typing.TYPE_CHECKING:
    from .command import BaseCommand


class _CommandRunnerArgs[T](typing.TypedDict, total=False):
    get_result: typing.Callable[[subprocess.Popen[bytes]], T]
    wait: bool
    check: bool | int | Undefined
    capture: bool


@dataclasses.dataclass(frozen=True)
class CommandRunner[T]:
    get_result: typing.Callable[[subprocess.Popen[bytes]], T]
    wait: bool = True
    check: bool | int | Undefined = Undefined.val
    capture: bool = False

    def run(self, command: BaseCommand) -> T:
        stdout = subprocess.PIPE if self.capture else Undefined.val
        proc = command.run(stdout=stdout, wait=self.wait, check=self.check)
        return self.get_result(proc)

    # Allow overriding settings by calling.
    # Some convenience methods are provided for quickly converting from string / bytes
    # (and will automatically enable redirection of output to a pipe).
    # Note: Only one of from_str / from_bytes / from_proc / to_file should be provided,
    # and it will override any prior setting.

    @typing.overload
    def __call__[U](
        self,
        *,
        from_str: typing.Callable[[str], U],
        wait: bool | Undefined = Undefined.val,
        check: bool | int | Undefined = Undefined.val,
    ) -> CommandRunner[U]: ...

    @typing.overload
    def __call__[U](
        self,
        *,
        from_bytes: typing.Callable[[bytes], U],
        wait: bool | Undefined = Undefined.val,
        check: bool | int | Undefined = Undefined.val,
    ) -> CommandRunner[U]: ...

    @typing.overload
    def __call__[U](
        self,
        *,
        from_proc: typing.Callable[[subprocess.Popen[bytes]], U],
        capture: bool | Undefined = Undefined.val,
        wait: bool | Undefined = Undefined.val,
        check: bool | int | Undefined = Undefined.val,
    ) -> CommandRunner[U]: ...

    @typing.overload
    def __call__(
        self,
        *,
        capture: bool | Undefined = Undefined.val,
        wait: bool | Undefined = Undefined.val,
        check: bool | int | Undefined = Undefined.val,
    ) -> CommandRunner[T]: ...

    def __call__[U](
        self,
        *,
        from_str: typing.Callable[[str], U] | Undefined = Undefined.val,
        from_bytes: typing.Callable[[bytes], U] | Undefined = Undefined.val,
        from_proc: typing.Callable[[subprocess.Popen[bytes]], U] | Undefined = Undefined.val,
        capture: bool | Undefined = Undefined.val,
        wait: bool | Undefined = Undefined.val,
        check: bool | int | Undefined = Undefined.val,
    ) -> CommandRunner[T] | CommandRunner[U] | CommandRunner[subprocess.Popen[bytes]]:
        """Alter runner parameters.

        Args:
            May specify at most one of from_str / from_bytes / from_proc

            capture:
                If true, capture output from final command.  This will override any
                output redirection performed on it.

            from_proc:
                Provide a function taking the process object.
                stdout will not be available unless set capture=True

            from_str:
                Take a function converting the output of the process as a string.
                Implies capture=True.
                Eg. run(from_str=int) converts the output to an integer.
                This is a convenience function for the equivalent of:
                    (from_proc = lambda proc: func(proc.stdout.read().decode('utf8')), capture=True)

            from_bytes:
                As from_str, but provides the raw byte content of the process.
                Implies capture=True.

            wait:
                Wait for the process to complete before returning.

            check:
                If True, check the result after execution and raise an Exception if it is 0
                May provide an integer instead, in which case will check the returncode matches that value.
                Only checked if wait=True.
        """
        converts = sum(1 for x in [from_str, from_bytes, from_proc] if not isinstance(x, Undefined))
        if converts > 1:
            raise ValueError("At most one of from_str, from_bytes or from_proc should be provided")

        args: _CommandRunnerArgs[typing.Any] = {}

        if not isinstance(from_str, Undefined):
            # Note: only one of from_str, from_bytes / from_proc should be defined.
            def convert(proc: subprocess.Popen[bytes]) -> U:
                assert proc.stdout
                return from_str(proc.stdout.read().decode("utf8"))

            from_proc = convert
            capture = True

        if not isinstance(from_bytes, Undefined):
            # Note: only one of from_str, from_bytes / from_proc should be defined.
            def convert(proc: subprocess.Popen[bytes]) -> U:
                assert proc.stdout
                return from_bytes(proc.stdout.read())

            from_proc = convert
            capture = True

        val: CommandRunner[typing.Any] = self
        if not isinstance(from_proc, Undefined):
            args["get_result"] = from_proc
            val = dataclasses.replace(val, get_result=from_proc)

        if not isinstance(capture, Undefined):
            args["capture"] = capture

        if not isinstance(check, Undefined):
            args["check"] = check

        if not isinstance(wait, Undefined):
            args["wait"] = wait

        return dataclasses.replace(self, **args)


# Provide instances for some common cases


def identity[T](val: T) -> T:
    return val


run = CommandRunner(identity)
bg = CommandRunner(identity, wait=False)
capture = run(from_str=str)
