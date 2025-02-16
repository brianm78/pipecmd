from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    from pathlib import Path
    import subprocess

type CommandDefinition = typing.Iterable[str | Path] | str | Path

# Input may be either file/fd/subprocess id or a path
type FileOrPath = typing.IO[typing.Any] | Path | str | subprocess._FILE


# Sentinel class to denote undefined values.
class Undefined:
    val: typing.ClassVar[typing.Self]  # Singleton instance usable in params.

    @typing.overload
    @classmethod
    def get_default[T](cls, *vals: T | Undefined) -> T: ...

    @typing.overload
    @classmethod
    def get_default[T](cls, *vals: T | Undefined, require: typing.Literal[True]) -> T: ...

    @typing.overload
    @classmethod
    def get_default[T](cls, *vals: T | Undefined, require: typing.Literal[False]) -> T | Undefined: ...

    @classmethod
    def get_default[T](cls, *vals: T | Undefined, require: bool = True) -> T | Undefined:
        """Return first non-undefined value in sequence.
        If all values undefined, raises exception if require is True,
        otherwise returns Undefined
        """
        for val in vals:
            if not isinstance(val, Undefined):
                return val

        if require:
            raise Exception("No non-undefined value")
        return Undefined.val


Undefined.val = Undefined()
