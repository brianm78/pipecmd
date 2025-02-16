# Pipecmd

A simple utility library for quickly chaining commandline commands together with a shell-like syntax.
Attempts to mimic shell syntax within python for common operations like running commands,
creating pipelines and redirecting output.

## Overview

To define commands, use `Command(name, [args])` or use the helper `sh` object.
Additional arguments may be provided by indexing with a string or tuple of strings (or paths).
Such commands can be combined with other commands by pipelines ("|"), or conditionally chained together.

The command will be run and the output returned when calling str(), bytes() or iterating over the lines,
or by calling it (which will return the `subprocess.Popen` object)
Also supports shell-style && or || chaining by overloading the & and ^ operators (^ since | already taken by pipes)

Some examples:

    cmd = sh.du["/tmp"] | sh.sort["-n"]
    str(cmd)  # Equivalent to bash's `du /tmp | sort -n`
    bytes(cmd)  # Same, but returns raw byte output.
    for line in cmd:
        # Iterate line by line over results.

Note: Each retrieval of results (str() / bytes() call) will re-run the command.


File redirection (to a path/string, a file object or subprocess value)

    cmd = sh.ls["/tmp"] > "out.txt"
    cmd()  # Runs "ls /tmp" and writes results in a file named "out.txt"

    cmd = Path("in.txt") | sh.sort > "out.txt"
    cmd()  # Reads in.txt, sends to sort and writes result to "out.txt"

    with open("out.txt") as f:
        cmd = sh.ls["in.txt] > f
        cmd() # To file object.

Shell style && / || chaining supported via "&" and "^" overloads ("^" used since "|" already taken).

    sh.false & sh.echo["This never runs"]
    sh.true ^ sh.echo["Nor does this"]

Automatically attempts to coerce strings / iterables of strings to Command objects when combined (Path objects
also accepted):

    sh.du["/tmp"] | "sort -n"
    sh.du["/tmp"] | ["sort", "-n"]
    sh.echo["Hello"] | Path("/bin/cat")

Can be configured to automatically raise an exception when the returncode is non-zero by passing check=True
to command constructor or invocation, or by using the helper "checked" object.

    sh.false(check=True)  # Raises exception when /bin/false returns non-zero returncode.
    checked.false()       # Defaults to check=True

Commands constructed by coercion from string / sequences inherit the checked status of the command they are being combined with.  Eg.

    sh.echo["foo"] | "false"       # No exception
    checked.echo["foo"] | "false"  # Raises


Note that for pipelines, the check is only performed for the final command in the pipeline, as this is the only
one wait()ed on.  Commands run in the background (wait=False) are also not checked.

## Objects

### Commands

A Command represents a shell command, with an optional default input / output.

Note: Command objects are immutable - all operations amending them, such as adding additional arguments / file outputs will create a new command object with those values without modifying the original.

#### Contruction

Commands may be created via `Command(name, args)`, or via the helper `sh` object which converts attribute access to command name.
Ie the following are equivalent:

    Command("ls", ["/tmp"])
    sh.ls["/tmp"]
    sh["ls"]["/tmp"]

For commands that use non-identifier symbols, use `sh[commandname]` rather than the attribute syntax.

A helper "checked" object also exists which constructs commands defaulting to `check=True`.

Arguments to Command are:

    - stdin: 
        If provided, default to this file / path for reading input to command
    - stdin: 
        If provided, default to this file / path for reading input to command
    - append: 
        If True, will open in append mode rather than overwriting when output is a path.
    - check: 
        The default behaviour in regard to handling a non-zero return code.  Only checked when invoked with wait=True
        If False, the returncode is not checked
        If True, raises an exception on a non-zero return code
        If an integer, raises an exception if the return code does not match this value.

#### Additional Arguments

Additional arguments may be provided by indexing with the `[]` operator, and providing a string or tuple of strings.  Eg:

    sh.ls["/tmp"]
    sh.ls["-l", "/tmp"]

This may be repeated to add further additional arguments.  Eg

    ls = sh.ls["-l"]
    ls_tmp = ls["/tmp"]
    ls_tmp()  # Calls "ls -l /tmp"

Further arguments may also be provided via the `.run()` or `__call__` methods when invoking the command.

#### Invoking

Commands may be invoked with the `.run()` method, or by calling the command (optionally with additional arguments).

Both `.run` and `__call__` accept the same keyword arguments as `subprocess.Popen` to customise behaviour, and will return the
subprocess.Popen object.  They also allow stdin/stdout to be a file path rather than a file or fd, which will be automatically opened.

In addition, they accept a few additional arguments:

    wait:  
        If True (the default), waits for the completion of the command, otherwise will return without blocking.
        The .bg() method is a convenience alias to .

    check:
        If provided, overrides the defauth returncode checking behaviour for the command.
        If True, checks the returncode of the command is zero, and raises an exception otherwise (similar to subprocess.run).
        May also be set to an integer to check the returncode is that value.

        Only used if wait is true (since otherwise the returncode is not available).

    append:
        When stdout is a path, will open it in "a" (append) mode, rather than overwriting.

Commands are also invoked and their output retrieved when calling
`str()` or `bytes()` on the command, or when iterating over it (which will perform line-by-line iteration)

#### Redirecting Input / Output

Commands may have an associated .input / .output value which may be a file, path or subprocess special value (eg. `subprocess.PIPE` / `subprocess.DEVNULL`).  The ">", "<", ">>", "<<" operators are overloaded to associate a command with such a value.  Eg.

    sh.ls["/tmp"] > Path("out.txt")
    sh.ls["/tmp"] > "out.txt"
    with open("out.txt", "wb") as f:
        cmd = sh.ls["/tmp"] > "out.txt"
        cmd()

    with open("out.txt", "wb") as f:
        cmd = sh.ls["/tmp"] > "out.txt"
        cmd()


Note that when using a file, it must remain open when the command is invoked, rather than just when created.
As a convenience, `None` may be used as a shorthand for suppressing output (ie. sending to /dev/null) so the following 
are equivalent:

    sh.echo("This is suppressed") > None
    sh.echo("This is suppressed") > subprocess.DEVNULL

Piping a command, re-using ">" on an already redirected command, or specifying stdout/stdin on the invocation will override
these values.

The direction of the arrow relative to the command indicates whether it's input or output, so the below are equivalent:

    "input.txt" > sh.cat > "output.txt"
    sh.cat < "input.txt" > "output.txt"

">>" or "<<" On an output will open it in "a" (append) mode, concatenating the output to an existing file.
It may also be used for inputs, but behaves identically to "<".  Eg.

    >>> (sh.echo["foo"] >> "out.txt").run()
    >>> (sh.echo["bar"] >> "out.txt").run()
    >>> str(sh.cat["out.txt"])
    'foo\nbar\n'

### CommandChain

Unevaluated Command objects may be combined with the "|" operator to pipe the output of one into the input of another.
Eg.

    cmd = sh.du["/tmp"] | sh.sort["-n"] > "out.txt"

Or manually constructed with:

    CommandChain(sh.du["/tmp"], sh.sort["-n"], output="out.txt")

These may be executed and combined similarly to command objects, with the exception that they cannot be given additional
arguments.  Eg.

    str(cmd)  # Returns contents
    proc = cmd(check=True)  # Run and check returnvalue of final command.
    (cmd > "out.txt").run() # Run and send final output to file.

#### Automatic coercion to commands.

Piping a Command or CommandChain to a string or iterable will coerce the value to a Command.
Eg. the below are all equivalent:

    sh.du["/tmp"] | "sort -n"
    sh.du["/tmp"] | ["sort", "-n"]
    sh.du["/tmp"] | sh.sort["-n"]

Where a string is used, it will be split using `shlex.split`

### And / Or CommandChain

Commands combined with "&" or "^" (for ||) will construct CommandAndChain / CommandOrChain objects which will act like commands
that run all their consituents until the first failing / first succeeding command.  Eg.

    sh.some_command & sh.echo["some_command succeeded"]
    sh.some_command ^ sh.echo["some_command failed"]

The same coercion rules apply as for CommandChain.

### Helper Objects

The `sh` helper can be used to construct command objects via attribute access or `[]` indexing.  Eg

    sh.ls
    sh["ls"]

The Indexing method may be needed for commands containing non-identifier characters like spaces or "-".

The `checked` helper operates similarly, but commands construced from it (or constructed via coercion from such commands) 
default to raising an exception when returning a non zero return code.
Eg.

    checked.false()  # Will raise exception.
    checked.echo | ["false"]  # As will this.

## TODO

 - Considering overloading __bool__ to run and check returncode which would allow things like:
    if sh.test["-e", file]:
        ...

    And even *kind-of* allows chaining directly with python's short-cirtuiting logic operators like:

        (sh.test["!", "-e", file] and sh.touch(file)).run()

    But this really eagerly evaluates the first command at definition time, which has inuintuitive semantics
    compared to how everything else works, so I think this is probably a bad idea.

 - Maybe a more natural syntax for signallying a command should be run.  Doing

    (sh.echo["x"] | sh.cat > "file.txt")()

   Is a bit clunky.  Maybe define some helper objects such that:

    command | run  # Immediately run and return proc
    command | bg   # As run, but wait=False

   Immediately runs and returns the Popen object?