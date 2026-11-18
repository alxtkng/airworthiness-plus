"""Fail if requirements.md and traceability.csv disagree.

Every requirement must have exactly one row in the matrix, and the
matrix must not name a requirement that does not exist. A requirement
with no test stays visible as "No Test"; it is never dropped.
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / "requirements" / "requirements.md"
MATRIX = ROOT / "requirements" / "traceability.csv"


def main() -> int:
    defined = re.findall(r"^\| (REQ-\d{3}) \|", REQUIREMENTS.read_text(encoding="utf-8"), re.M)
    with MATRIX.open(encoding="utf-8", newline="") as handle:
        traced = [row["Requirement"] for row in csv.DictReader(handle)]

    problems: list[str] = []
    for name, items in (("requirements.md", defined), ("traceability.csv", traced)):
        duplicates = sorted({item for item in items if items.count(item) > 1})
        if duplicates:
            problems.append(f"Duplicated in {name}: {', '.join(duplicates)}")
    missing = sorted(set(defined) - set(traced))
    unknown = sorted(set(traced) - set(defined))
    if missing:
        problems.append(f"In requirements.md but not traced: {', '.join(missing)}")
    if unknown:
        problems.append(f"Traced but not in requirements.md: {', '.join(unknown)}")

    for problem in problems:
        print(problem)
    print(f"{len(defined)} requirements, {len(traced)} traced")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
