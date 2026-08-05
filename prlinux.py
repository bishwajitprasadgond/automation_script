#!/usr/bin/env python3
"""
Restore project from project_dump.txt

Usage:
    python project_restore.py
    python project_restore.py project_dump.txt
"""

from pathlib import Path
import re
import sys

DEFAULT_DUMP_FILE = "project_dump.txt"

OVERWRITE_EXISTING = True

FILE_MARKER = re.compile(r"^FILE:\s*(.+)$")


def save_file(base_dir: Path, relative_path: str, lines):

    # Normalize Windows/Linux separators
    relative_path = relative_path.replace("\\", "/").strip()

    target = base_dir / Path(relative_path)

    print(f"\nCreating file : {target}")

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"Directory OK  : {target.parent}")
    except Exception as e:
        print(f"Failed creating directory:\n{e}")
        return False

    if target.exists() and not OVERWRITE_EXISTING:
        print("Skipped (already exists)")
        return False

    while lines and lines[-1] == "":
        lines.pop()

    try:
        with target.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as f:
            f.write("\n".join(lines))

        print("Created successfully")
        return True

    except Exception as e:
        print(f"Failed writing file:\n{e}")
        return False


def restore_project(dump_file: Path, output_dir: Path):

    if not dump_file.exists():
        print(f"Dump file not found:\n{dump_file}")
        return

    print("=" * 80)
    print("PROJECT RESTORE")
    print("=" * 80)
    print("Dump File :", dump_file.resolve())
    print("Output Dir:", output_dir.resolve())
    print()

    restored = 0
    skipped = 0

    current_file = None
    current_lines = []
    collecting = False

    with dump_file.open(
        "r",
        encoding="utf-8",
        errors="ignore",
        newline=None,
    ) as f:

        for raw_line in f:

            line = raw_line.rstrip("\r\n")

            match = FILE_MARKER.match(line)

            if match:

                if current_file is not None:

                    if save_file(
                        output_dir,
                        current_file,
                        current_lines,
                    ):
                        restored += 1
                    else:
                        skipped += 1

                current_file = match.group(1).strip()

                current_lines = []

                collecting = False

                continue

            if (
                line.startswith("#")
                and len(line) > 20
            ):
                collecting = True
                continue

            if current_file is None:
                continue

            if collecting:
                current_lines.append(line)

    if current_file is not None:

        if save_file(
            output_dir,
            current_file,
            current_lines,
        ):
            restored += 1
        else:
            skipped += 1

    print()
    print("=" * 80)
    print(f"Files Restored : {restored}")
    print(f"Files Skipped  : {skipped}")
    print("=" * 80)


def main():

    if len(sys.argv) > 1:
        dump_file = Path(sys.argv[1])
    else:
        dump_file = Path(DEFAULT_DUMP_FILE)

    output_dir = Path.cwd()

    restore_project(
        dump_file=dump_file.resolve(),
        output_dir=output_dir.resolve(),
    )


if __name__ == "__main__":
    main()