import nox

sourcecode_paths = ["src", "tests", "main.py"]
nox.options.reuse_existing_virtualenvs = True


@nox.session(name="format")
def formatting(session: nox.Session) -> None:
    """Format the code and sort imports. Not needed in workflows."""
    session.install("-r", "requirements-dev.txt")
    session.run("isort", *sourcecode_paths)
    session.run(
        "autoflake",
        "--recursive",
        "--in-place",
        "--remove-unused-variables",
        *sourcecode_paths,
    )
    session.run("black", *sourcecode_paths)


@nox.session(name="quality")
def quality(session: nox.Session) -> None:
    """Analyse static code for typing and code smells."""
    session.install("-r", "requirements-dev.txt")
    session.run("pylint", *sourcecode_paths)
    session.run("mypy", *sourcecode_paths)


@nox.session(name="complexity")
def complexity(session: nox.Session) -> None:
    """Assess the complexity of the code."""
    session.install("-r", "requirements-dev.txt")
    session.run(
        "xenon", "--max-absolute B", "--max-modules A", "--max-average A", "src"
    )


@nox.session(name="tests")
def test(session: nox.Session) -> None:
    """Run all tests with code coverage."""
    session.install("-r", "requirements-dev.txt")
    session.run(
        "coverage",
        "run",
        "-m",
        "pytest",
        "tests/unit",
        "--junitxml=junit/test-results.xml",
    )
    session.run("coverage", "report", "--fail-under=30", "-m")
    session.run("coverage", "xml", "--fail-under=30", "-o", "coverage.xml")
    session.run("coverage", "html", "--fail-under=30")
