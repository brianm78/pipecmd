
### TODO

Considering overriding __bool__ to evaluate and use the return code.

Ie:

    def __bool__(self):
        """Evaluate command and return True for returncode of 0"""
        proc = self.run(wait=True)
        return proc.returncode == 0

This would allow using things like pipeline chaining etc.
Eg.

    if sh.test["-e", filename]:
        # File exists

    (sh.false and sh.echo("This never runs")).run()

Though the behaviour is maybe not entirely what you'd expect, because the evaluation of the check happens eagerly, so
something like:

    # Touch file if doesn't exist.
    cmd = sh.test["!", "-e", filename] and sh.touch[filename]

    cmd()   # touch file
    cmd()   # Also touches file, even though already exists, because the check was done at definition time.

Instead, it may be less surprising to implement as a seperate chain that checks the returncode.  Eg:

   sh.test["!", "-e", filename] & sh.touch[filename]

Note: don't really have an operator we can overload for the "or" case: "|" already taken for piping.
Could use ^, //, @, 