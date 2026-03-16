#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "prettytable",
# ]
# ///
import json
import sys
import argparse
import datetime
from pathlib import Path

from prettytable import PrettyTable


BASE_DIR = Path(__file__).resolve().parent


def configure_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
                        prog="Tasks logger.",
                        description="A simple CLI for recording daily tasks.",
    )

    group = parser.add_mutually_exclusive_group()

    group.add_argument('-s', '--start', help="Short description of the task.")
    group.add_argument('-f', '--finish', action='store_true')

    parser.add_argument("--summary", action="store_true", help="Show all today's tasks")

    return parser


def main():
    parser = configure_argparse()

    if not sys.argv == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    filepath = reports_dir / f"{today()}.json"

    if args.start is not None:
        add_entry(filepath, args.start)
    elif args.finish:
        finish_last_entry(filepath)

    if args.summary:
        print_summary(filepath)


def add_entry(filepath, text: str) -> None:
    if not filepath.exists():
        write_json(filepath, [])

    log = read_json(filepath)

    if log:
        last_record = log[-1]
        if not last_record.get("finish"):
            print(f"ERROR: You haven't finished the previous task yet: '{last_record["text"]}'")
            return

    log.append({
        "text": text,
        "start": time_now(),
        "finish": None,
    })

    write_json(filepath, log)
    print(f"Successfully added a new record: '{text}'")


def today():
    return datetime.datetime.now().strftime("%d-%m-%Y")


def time_now():
    return datetime.datetime.now().strftime("%H:%M")


def read_json(filepath: Path) -> list[dict]:
    with open(filepath, "r") as fin:
        obj = json.load(fin)

    return obj


def write_json(filepath: Path, obj: object) -> None:
    with open(filepath, "w") as fout:
        json.dump(obj, fout, ensure_ascii=False, indent=2)


def finish_last_entry(filepath: Path):
    if not filepath.exists():
        raise FileNotFoundError(filepath)

    log = read_json(filepath)
    if not log:
        print(f"ERROR: there are no records in the file {filepath} yet.")
        return

    last_entry = log[-1]
    if last_entry["finish"]:
        print(
            f"ERROR: last entry ('{last_entry['text']}') has been already finished "
            f"at {last_entry['finish']}"
        )
        return

    last_entry["finish"] = time_now()

    write_json(filepath, log)
    print(
        f"The record '{last_entry['text']}' has been finished at {last_entry['finish']}"
    )


def print_summary(filepath: Path) -> None:
    if not filepath.exists():
        raise FileNotFoundError(filepath)

    log = read_json(filepath)
    if not log:
        print(f"The log file {filepath!s} is empty")
        return

    table = PrettyTable(["Start", "End", "Task"])
    table.align["Task"] = "l"

    for record in log:
        table.add_row([
            record["start"], record["finish"], record["text"]
        ])

    print(table)


if __name__ == "__main__":
    main()
