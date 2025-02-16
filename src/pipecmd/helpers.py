from .command import Command
from pathlib import Path


class CommandHelper:
    def __init__(self, checked: bool | int = False):
        self.checked = checked

    def __getattr__(self, name: str | Path) -> Command:
        return Command(name, check=self.checked)

    def __getitem__(self, name: str | Path) -> Command:
        return Command(name, check=self.checked)

    def __repr__(self) -> str:
        return f"CommandHelper(checked={self.checked})"


sh = CommandHelper()
checked = CommandHelper(checked=True)
