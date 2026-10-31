"""Fail if any job under lakehouse/ prints rows: run output persists in Databricks run history."""

import ast
import sys
from pathlib import Path

FORBIDDEN_CALLS = {"display", "print"}
FORBIDDEN_METHODS = {"show"}


def violations(source: str) -> list[int]:
    lines = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if (isinstance(f, ast.Name) and f.id in FORBIDDEN_CALLS) or (
            isinstance(f, ast.Attribute) and f.attr in FORBIDDEN_METHODS
        ):
            lines.append(node.lineno)
    return lines


def main(root: str = "lakehouse") -> int:
    found = 0
    for path in sorted(Path(root).rglob("*.py")):
        for line in violations(path.read_text(encoding="utf-8")):
            print(f"{path}:{line}: row output is forbidden in lakehouse jobs")
            found += 1
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
