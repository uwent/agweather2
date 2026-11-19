"""Set `updated:` in the front matter of the topic and model pages given to today's date, or with --from-git to the
date of each page's last commit (Ben, 2026-11-18: the "last updated" date pages show). The commit hook runs it on
every page staged (`lint-staged` in package.json), so a page's date is the day it last changed.

Run: `uv run python scripts/stamp_updated.py PAGE...` or `uv run python scripts/stamp_updated.py --from-git PAGE...`
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TODAY = datetime.now(tz=ZoneInfo("America/Chicago")).date().isoformat()  # Madison's date
UPDATED = re.compile(r"^updated: .*$", re.MULTILINE)


def stamp(path: Path, day: str) -> bool:
    """Write `updated: day` into the page's front matter (after `status:`, or replacing the line); whether it changed."""
    text = path.read_text()
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        print(f"{path}: no front matter, left alone", file=sys.stderr)
        return False
    end = text.index("\n---\n", 4)
    front, rest = text[4:end], text[end:]
    if UPDATED.search(front):
        new_front = UPDATED.sub(f"updated: {day}", front)
    elif re.search(r"^status: .*$", front, re.MULTILINE):
        new_front = re.sub(r"^(status: .*)$", rf"\1\nupdated: {day}", front, count=1, flags=re.MULTILINE)
    else:
        new_front = f"{front}\nupdated: {day}"
    if new_front == front:
        return False
    path.write_text(f"---\n{new_front}{rest}")
    return True


def last_commit_day(path: Path) -> str:
    out = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", str(path)], capture_output=True, text=True, check=True
    )
    return out.stdout.strip() or TODAY


def main() -> None:
    parser = argparse.ArgumentParser(description="Set updated: in pages' front matter.")
    parser.add_argument("pages", nargs="+", type=Path)
    parser.add_argument("--from-git", action="store_true", help="each page's last commit date rather than today's")
    args = parser.parse_args()
    changed = sum(stamp(p, last_commit_day(p) if args.from_git else TODAY) for p in args.pages)
    if args.from_git:
        print(f"{changed} of {len(args.pages)} pages stamped")


if __name__ == "__main__":
    main()
