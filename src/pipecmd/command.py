from __future__ import annotations
import subprocess
import shlex
import typing
from pathlib import Path
import dataclasses
from .types import CommandDefinition, FileOrPath, Undefined
from .runner import CommandRunner


class RedirectArgs(typing.TypedDict, total=False):
    input: FileOrPath
    output: FileOrPath
    append: bool


@dataclasses.dataclass(frozen=True, kw_only=True)
class BaseCommand:
    """Create a command object for the given command.

    The command is not run until calling a method such as run / iterlines,
    or converting to string / bytes with str() / bytes() etc.
    """

    # Should the returnvalue of the command be checked by default
    # (Only when wait=True)
    check: bool | int = False

    @typing.overload
    def __or__(self, other: CommandDefinition | BaseCommand) -> CommandChain: ...

    @typing.overload
    def __or__[T](self, other: CommandRunner[T]) -> T: ...

    def __or__[T](self, other: CommandDefinition | BaseCommand | CommandRunner[T]) -> CommandChain | T:
        if isinstance(other, CommandRunner):
            return other.run(self)
        return self.pipe_to(Command.make(other))

    def pipe_to(self, other: BaseCommand) -> CommandChain:
        """Return command piping output of this command into other"""
        return CommandChain([self, other], check=self.check)

    def on_success(self, other: BaseCommand) -> CommandAndChain:
        """Return command running other if this command returns success (zero returncode)"""
        return CommandAndChain([self, Command.make(other)], check=self.check)

    def on_failure(self, other: BaseCommand) -> CommandOrChain:
        """Return command running other if this command returns failure (non-zero returncode)"""
        return CommandOrChain([self, Command.make(other)], check=self.check)

    def __and__(self, other: CommandDefinition | BaseCommand) -> CommandAndChain:
        return self.on_success(Command.make(other))

    def __xor__(self, other: CommandDefinition | BaseCommand) -> CommandOrChain:
        """We're using | for piping, and there isn't really a good operator to use
        for the equivalent of ||, so we're somewhat arbitrarily using "^"
        """
        return self.on_failure(Command.make(other))

    def iter_lines(self, encoding: str = "utf8") -> typing.Iterator[str]:
        """Run command and read output line-by-line"""
        proc = self.run(wait=False, stdout=subprocess.PIPE, encoding=encoding)
        if proc.stdout is None:
            return
        for line in proc.stdout:
            yield line

    def __iter__(self) -> typing.Iterator[str]:
        return self.iter_lines()

    def __bytes__(self) -> bytes:
        """Run and retrieve output as bytes object."""
        proc: subprocess.Popen[bytes] = self.run(stdout=subprocess.PIPE, encoding=None, wait=True)
        if proc.stdout is None:
            return b""
        return proc.stdout.read()

    def __str__(self) -> str:
        """Replace with string output of command.

        Note: Each invocation re-runs command.
        """
        proc: subprocess.Popen[str] = self.run(stdout=subprocess.PIPE, encoding="utf8", wait=True)
        if proc.stdout is None:
            return ""
        return proc.stdout.read()

    def __call__(
        self,
        *,
        stdin: FileOrPath | Undefined = Undefined.val,
        stdout: FileOrPath | Undefined = Undefined.val,
        append: bool | Undefined = Undefined.val,
        wait: bool = True,
        check: bool | int | Undefined = Undefined.val,
        **kwargs: typing.Any,
    ) -> subprocess.Popen[typing.Any]:
        """Run command, optionally providing further args."""
        return self.run(stdin=stdin, stdout=stdout, append=append, wait=wait, check=check, **kwargs)

    def bg(
        self,
        stdin: FileOrPath | Undefined = Undefined.val,
        stdout: FileOrPath | Undefined = Undefined.val,
        append: bool | Undefined = Undefined.val,
        **kwargs: typing.Any,  # Passed directly through to subprocess
    ) -> subprocess.Popen[typing.Any]:
        """Run in background.  Equivalent to .run(wait=False)"""
        return self.run(stdin=stdin, stdout=stdout, append=append, wait=False, check=False, **kwargs)

    def run(
        self,
        stdin: FileOrPath | Undefined = Undefined.val,
        stdout: FileOrPath | Undefined = Undefined.val,
        append: bool | Undefined = Undefined.val,
        wait: bool = True,
        check: bool | int | Undefined = Undefined.val,
        **kwargs: typing.Any,  # Passed directly through to subprocess
    ) -> subprocess.Popen[typing.Any]:
        # Implemnent in subclasses
        raise NotImplementedError()

    def redirect(self, **kwargs: typing.Unpack[RedirectArgs]) -> typing.Self:
        """Return new command with redirected stdin/stdout.
        A value of None will be treated as /dev/null
        """
        raise NotImplementedError()

    def __lt__(self, input: FileOrPath) -> typing.Self:
        """cmd < file: Run command with input sent to file."""
        # Shortcut for suppress outpuc: fild > None
        if input is None:
            input = subprocess.DEVNULL
        return self.redirect(input=input)

    def __gt__(self, output: FileOrPath) -> typing.Self:
        """cmd > output:  Run command with output sent to file."""
        return self.redirect(output=output)

    def __rrshift__(self, file: FileOrPath) -> typing.Self:
        """file >> cmd - set as input"""
        return self.redirect(input=file)

    def __lshift__(self, file: FileOrPath) -> typing.Self:
        """cmd << file"""
        return self.redirect(input=file)

    def __rshift__(self, file: FileOrPath) -> typing.Self:
        """cmd >> file.  As >, but where file is filename, opens in append mode."""
        return self.redirect(output=file, append=True)

    def __rlshift__(self, file: FileOrPath) -> typing.Self:
        """file << cmd : Write to file but, opening in append mode."""
        return self.redirect(output=file, append=True)


@dataclasses.dataclass(frozen=True)
class Command(BaseCommand):
    cmd: str | Path
    args: typing.Sequence[str | Path] = ()

    # Default Input / output files/paths used to invoke this command.
    # (If not set, uses None (no capturing/redirection)
    input: FileOrPath | Undefined = Undefined.val
    output: FileOrPath | Undefined = Undefined.val

    # Should Output be opened append (if a path)  default is False
    append: bool | Undefined = Undefined.val

    @classmethod
    def from_shell(cls, cmd: str, check: bool | int = False) -> typing.Self:
        cmd, *arglist = shlex.split(cmd)
        return cls(cmd, arglist, check=check)

    def redirect(self, **kwargs: typing.Unpack[RedirectArgs]) -> typing.Self:
        """Return new command with redirected stdin/stdout.
        A value of None will be treated as /dev/null
        """
        # Allow > None as a shortcut to devnull.
        if kwargs.get("input", Undefined.val) is None:
            kwargs["input"] = subprocess.DEVNULL
        if kwargs.get("output", Undefined.val) is None:
            kwargs["output"] = subprocess.DEVNULL

        return dataclasses.replace(self, **kwargs)

    @classmethod
    def make(cls, cmd: BaseCommand | CommandDefinition, check: bool | int = False) -> BaseCommand:
        """Construct from either a string (interpreted via shlex) or iterable of commandname + args.
        Eg. the below both produce Command("ls", "-l", "/tmp")

            "ls -l /tmp"   # uses shlex.split to split.
            ["ls", "-l", "/tmp"]

        Initial command must always be a path or string.
        """
        if isinstance(cmd, BaseCommand):
            return cmd  # no-op

        elif isinstance(cmd, str):
            return cls.from_shell(cmd, check=check)
        elif isinstance(cmd, Path):
            return cls(cmd, check=check)
        else:
            # Iterable of cmd/args
            name, *args = cmd
            return cls(name, args, check=check)

    def __getitem__(self, args: str | Path | tuple[str | Path, ...]) -> typing.Self:
        """Add args.  Eg. sh.ls["-l", "/tmp"]"""
        if isinstance(args, (str, Path)):
            # Single item
            args = (args,)

        return dataclasses.replace(self, args=(*self.args, *args))

    def __call__(
        self,
        *args: str | Path,
        stdin: FileOrPath | Undefined = Undefined.val,
        stdout: FileOrPath | Undefined = Undefined.val,
        append: bool | Undefined = Undefined.val,
        wait: bool = True,
        check: bool | int | Undefined = Undefined.val,
        **kwargs: typing.Any,
    ) -> subprocess.Popen[typing.Any]:
        """Run command, optionally providing further args."""
        cmd = self
        if args:
            cmd = self[args]
        return cmd.run(stdin=stdin, stdout=stdout, append=append, wait=wait, check=check, **kwargs)

    def __repr__(self) -> str:
        argstr = (", [" + ", ".join(repr(arg) for arg in self.args) + "]") if self.args else ""
        return f"Command({self.cmd!r}{argstr})"

    def _get_file(self, file: FileOrPath | Undefined, fallback: FileOrPath | Undefined, mode: str) -> subprocess._FILE:
        if isinstance(file, Undefined):
            if isinstance(fallback, Undefined):
                return None
            else:
                file = fallback

        if isinstance(file, (str, Path)):
            return open(file, mode)

        return file

    def run(
        self,
        stdin: FileOrPath | Undefined = Undefined.val,
        stdout: FileOrPath | Undefined = Undefined.val,
        append: bool | Undefined = Undefined.val,
        wait: bool = True,
        check: bool | int | Undefined = Undefined.val,
        **kwargs: typing.Any,  # Passed directly through to subprocess
    ) -> subprocess.Popen[typing.Any]:
        """Run the command and return subprocess.Popen object.

        Args:
            stdin / stdout:
                May be any of the standard subprocess._FILE values (file, fd, special value),
                or alternatively, may provide a file path, which will be opened and written to.
                Files are opened as binary by default (output will be opened as text if encoding is set).
                If not provided, will use default input/output files for this Command object
                (settable via the .redirect method or using > / < operators)

            append:
                If True, and output is a path, it will be opened in append mode ("a")

            wait:
                If True, waits for the child to complete before returning.

            check:
                Note: Only applied if wait is True.
                If True, raise an exception if return code is non-zero.
                If an integer, raise an exception if return code does not match this value.
                If not provided, uses default for this command.

        If stdin / stdout are paths, they will be opened (output in append mode if append is True)
        Opened as binary unless encoding is set.
        """

        # TODO: Ideally we should just open these for the lifetime of the process.
        # Though this is complicated if wait=False.
        stdin = self._get_file(stdin, self.input, "rb")
        append = Undefined.get_default(append, self.append, False)
        stdout = self._get_file(stdout, self.output, "ab" if append else "wb")
        check = Undefined.get_default(check, self.check)

        proc = subprocess.Popen([self.cmd, *self.args], stdin=stdin, stdout=stdout, **kwargs)

        if wait:
            returncode = proc.wait()
            if check is True:
                check = 0  # Check returncode == 0
            if check is not False and returncode != check:
                raise subprocess.CalledProcessError(proc.returncode, proc.args)
        return proc


@dataclasses.dataclass(frozen=True, repr=False)
class BaseCommandChain(BaseCommand):
    """Represent sequence of commands piped together"""

    cmds: typing.Sequence[BaseCommand] = ()

    _joinString: typing.ClassVar[str] = ""

    def __repr__(self) -> str:
        return f" {self._joinString} ".join(repr(c) for c in self.cmds)

    def _split_args(self, kwargs: RedirectArgs) -> tuple[RedirectArgs, RedirectArgs]:
        """Split into input args and output/append"""
        in_args = out_args = kwargs
        if "input" in kwargs:
            in_args = RedirectArgs({"input": kwargs["input"]})
            out_args = kwargs.copy()
            del out_args["input"]

        return in_args, out_args

    def redirect(self, **kwargs: typing.Unpack[RedirectArgs]) -> typing.Self:
        """Return new command with redirected stdin/stdout.

        Equivalent to redirecing first command in chain's stdin / last command's stdout/append
        """
        in_args, out_args = self._split_args(kwargs)
        cmds = list(self.cmds)
        if in_args:
            cmds[0] = cmds[0].redirect(**in_args)
        if out_args:
            cmds[-1] = cmds[-1].redirect(**out_args)

        return dataclasses.replace(self, cmds=cmds)

    def _concat_cmd(self, other: BaseCommand, flatten: bool = True) -> list[BaseCommand]:
        """Convert other to Command if not already, and concatenate with this chain's commands.

        If flatten is true, concatenates two chains of same type to a single chain.
        Ie.
            (a | b)  |  (c | d)   -> (a | b | c | d) rather than (a | b | (c | d))
        """
        cmds = list(self.cmds)
        if flatten and isinstance(other, self.__class__):
            cmds += other.cmds
        else:
            cmds.append(other)

        return cmds


@dataclasses.dataclass(frozen=True, repr=False)
class CommandAndChain(BaseCommandChain):
    """Chain of commands predicated on the prior command returning success.
    Equivalent to shell &&:
    Eg::

        sh.false & echo["Never printed"]
        sh.true & echo["But this is"]
    """

    _joinString: typing.ClassVar[str] = "&&"

    def on_success(self, other: BaseCommand) -> CommandAndChain:
        return dataclasses.replace(self, cmds=self._concat_cmd(other))

    def run(
        self,
        stdin: FileOrPath | Undefined = Undefined.val,
        stdout: FileOrPath | Undefined = Undefined.val,
        append: bool | Undefined = Undefined.val,
        wait: bool = True,
        check: bool | int | Undefined = Undefined.val,
        **kwargs: typing.Any,  # Passed directly through to subprocess
    ) -> subprocess.Popen[typing.Any]:
        """Run sequence of commands, stopping if any returns a non-zero exit code.
        The first command that produces a failing returncode will be returned,
        or if all are successful, the last command in the chain.

        If check is True, an exception is generated on the first failure instead.

        If wait is False, it will only apply to the final process in the chain:
        Prior processes will still wait to be able to obtain the returncode.

        stdin is sent to the first command in the chain.
        stdout will receive the outpout of the final command in the chain if and
        only if it is actually run (ie. no prior errors)
        """

        for cmd in self.cmds[:-1]:
            proc = cmd.run(stdin=stdin, wait=True, check=check, **kwargs)
            stdin = Undefined.val  # Don't pass same input past first one.
            if proc.returncode != 0:
                return proc

        proc = self.cmds[-1].run(stdout=stdout, append=append, wait=wait, check=check, **kwargs)
        return proc


@dataclasses.dataclass(frozen=True, repr=False)
class CommandOrChain(BaseCommandChain):
    """Chain of commands predicated on the prior command returning success.
    Equivalent to shell &&:
    Eg::

        sh.false & echo["Never printed"]
        sh.true & echo["But this is"]
    """

    _joinString: typing.ClassVar[str] = "||"

    def on_failure(self, other: BaseCommand) -> CommandOrChain:
        cmds = self._concat_cmd(other)
        # Override output
        return dataclasses.replace(self, cmds=cmds)

    def run(
        self,
        stdin: FileOrPath | Undefined = Undefined.val,
        stdout: FileOrPath | Undefined = Undefined.val,
        append: bool | Undefined = Undefined.val,
        wait: bool = True,
        check: bool | int | Undefined = Undefined.val,
        **kwargs: typing.Any,  # Passed directly through to subprocess
    ) -> subprocess.Popen[typing.Any]:
        """Run sequence of commands, only continuing to next if prior command
        returns a non-zero return code.  (Ie. equivalent to shell || syntax)

        The last command actually executed will be returned (Ie. either last command
        or first returning successful result)

        If check is True, will still generate an exception on the first failure.

        If wait is False, it will only apply to the final process in the chain:
        Prior processes will still wait to be able to obtain the returncode.

        stdin is sent to the first command in the chain.
        stdout will receive the outpout of the final command in the chain if and
        only if it is actually run (ie. all prior commands return nonzero)
        """

        for cmd in self.cmds[:-1]:
            proc = cmd.run(stdin=stdin, wait=True, check=check, **kwargs)
            stdin = Undefined.val  # Don't pass same input past first one.
            if proc.returncode == 0:
                return proc

        proc = self.cmds[-1].run(stdout=stdout, append=append, wait=wait, check=check, **kwargs)
        return proc


@dataclasses.dataclass(frozen=True, repr=False)
class CommandChain(BaseCommandChain):
    """Represent sequence of commands piped together"""

    _joinString: typing.ClassVar[str] = "|"

    def pipe_to(self, other: BaseCommand) -> typing.Self:
        cmds = self._concat_cmd(other)
        return dataclasses.replace(self, cmds=cmds)

    def run(
        self,
        stdin: FileOrPath | Undefined = Undefined.val,
        stdout: FileOrPath | Undefined = Undefined.val,
        append: bool | Undefined = Undefined.val,
        wait: bool = True,
        check: bool | int | Undefined = Undefined.val,
        **kwargs: typing.Any,  # Passed directly through to subprocess
    ) -> subprocess.Popen[typing.Any]:
        # TODO: Open input file for duration of call

        for cmd in self.cmds[:-1]:
            proc = cmd.run(stdin=stdin, stdout=subprocess.PIPE, wait=False, **kwargs)
            stdin = proc.stdout

        proc = self.cmds[-1].run(stdin=stdin, stdout=stdout, append=append, wait=wait, check=check, **kwargs)
        return proc
