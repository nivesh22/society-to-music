"""Run code quality checks and report results in plain English.

Run this before every git commit:
    make check

Checks performed:
  1. Code formatting (ruff format)
  2. Code style / lint (ruff check)
  3. Unit tests (pytest)
"""

import subprocess
import sys

# Maps ruff error codes to plain-English fix instructions.
_RUFF_GUIDE = {
    "E501": "Line is too long — shorten it to under 88 characters",
    "F401": "Unused import — remove the import at the top of the file",
    "F811": "Duplicate import — you imported the same thing twice, remove one",
    "F821": "Name used before it was defined — check your variable names",
    "T201": "print() found — use logger.info() instead (see logging section in TEAMMATES.md)",
    "E711": "Use 'is None' instead of '== None'",
    "E712": "Use 'if condition:' instead of 'if condition == True:'",
    "W291": "Trailing whitespace — remove spaces at the end of the line",
    "W293": "Blank line has whitespace — remove spaces from blank lines",
    "PLC0415": "Import not at top of file — move imports to the top (or add # noqa: PLC0415 if you need a lazy import)",
    "B007": "Loop variable not used in loop body — rename it to '_' if intentional",
    "B006": "Mutable default argument — use None as default and assign inside the function",
    "E722": "Bare 'except:' — catch a specific exception like 'except ValueError:'",
    "SIM108": "Use a ternary expression instead of an if/else block for simple assignments",
}


def _header(title: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


def run_format_check() -> bool:
    _header("Step 1 of 3 — Checking code formatting")
    result = subprocess.run(
        ["ruff", "format", "--check", "."],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("  PASS — all files are correctly formatted")
        return True

    print("  FAIL — these files need to be reformatted:")
    for line in result.stdout.strip().splitlines():
        if line.strip():
            print(f"    • {line.strip()}")
    print()
    print("  HOW TO FIX: run this command, then re-stage your file:")
    print("    ruff format .")
    return False


def run_lint_check() -> bool:
    _header("Step 2 of 3 — Checking code style (lint)")
    result = subprocess.run(
        ["ruff", "check", "."],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("  PASS — no style issues found")
        return True

    print("  FAIL — style issues found:\n")
    seen_codes: set[str] = set()
    for line in result.stdout.strip().splitlines():
        if not line.strip() or line.startswith("Found"):
            continue
        # ruff format: path:line:col: CODE message
        parts = line.split(":")
        if len(parts) >= 4:
            file_loc = f"{parts[0].strip()}:{parts[1].strip()}"
            rest = ":".join(parts[3:]).strip()
            code = rest.split()[0] if rest else ""
            plain = _RUFF_GUIDE.get(code, "")
            if plain:
                print(f"    • {file_loc} [{code}] — {plain}")
            else:
                print(f"    • {line.strip()}")
            seen_codes.add(code)
        else:
            print(f"    • {line.strip()}")

    print()
    if seen_codes:
        print("  HOW TO FIX:")
        print("    1. Run 'ruff check . --fix' — this auto-fixes many issues")
        print("    2. Re-read the errors above and fix any that remain manually")
        print("    3. Run 'make check' again to confirm everything is clean")
    return False


def run_tests() -> bool:
    _header("Step 3 of 3 — Running unit tests")
    result = subprocess.run(
        ["pytest", "tests/", "-q", "--tb=short", "--no-header"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        lines = result.stdout.strip().splitlines()
        summary = next(
            (line for line in reversed(lines) if "passed" in line), "all passed"
        )
        print(f"  PASS — {summary}")
        return True

    print("  FAIL — one or more tests failed:\n")
    # Print compact failure output
    for line in result.stdout.strip().splitlines():
        if line.strip():
            print(f"    {line}")
    if result.stderr.strip():
        for line in result.stderr.strip().splitlines()[:10]:
            print(f"    {line}")

    print()
    print("  HOW TO FIX:")
    print("    1. Run 'make test' for the full detailed error output")
    print("    2. Find the test function that failed (shown above as FAILED ...)")
    print("    3. Read the AssertionError — it tells you exactly what went wrong")
    print("    4. Fix your node function, then run 'make check' again")
    return False


def main() -> None:
    print()
    print("=" * 50)
    print("  Pre-commit check")
    print("  Run this before every git commit.")
    print("=" * 50)

    fmt_ok = run_format_check()
    lint_ok = run_lint_check()
    tests_ok = run_tests()

    print()
    print("=" * 50)
    if fmt_ok and lint_ok and tests_ok:
        print("  ALL CHECKS PASSED — safe to commit!")
        print()
        print("  Next steps:")
        print("    git add <your-file>")
        print('    git commit -m "describe what you did"')
    else:
        print("  ISSUES FOUND — fix the problems above before committing.")
        print()
        print("  Quick fix sequence:")
        if not fmt_ok:
            print("    1. ruff format .          ← fixes formatting automatically")
        if not lint_ok:
            print(
                "    2. ruff check . --fix     ← fixes many style issues automatically"
            )
        if not tests_ok:
            print("    3. make test              ← shows full test failure details")
        print(
            "    4. make check             ← run this again to confirm everything passes"
        )
        sys.exit(1)
    print("=" * 50)


if __name__ == "__main__":
    main()
