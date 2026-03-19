#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "prettytable",
# ]
# ///
import argparse
import datetime
import json
import sys
from pathlib import Path

from prettytable import PrettyTable


BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"


def configure_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="report.py",
        description="A simple CLI for recording daily tasks.",
    )

    group = parser.add_mutually_exclusive_group()

    group.add_argument("-s", "--start", help="Short description of the task.")
    group.add_argument(
        "-f", "--finish", action="store_true", help="Finish the active task.")

    return parser


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    filepath = report_filepath()

    parser = configure_argparse()
    args = parser.parse_args()

    if len(sys.argv) == 1:
        print_summary(filepath)
        return 0

    if args.start is not None:
        add_entry(filepath, args.start)
    elif args.finish:
        finish_last_entry(filepath)

    return 0


def report_filepath(now: datetime.datetime | None = None) -> Path:
    return REPORTS_DIR / f"{today(now)}.json"


def add_entry(filepath: Path, text: str) -> None:
    log = read_json(filepath)

    if log:
        last_record = log[-1]
        if not last_record.get("finish"):
            print(
                f"ERROR: You haven't finished the previous task yet: "
                f"'{last_record['text']}'"
            )
            return

    log.append({
        "text": text,
        "start": time_now(),
        "finish": None,
    })

    write_json(filepath, log)
    print(f"Successfully added a new record: '{text}'")


def today(now: datetime.datetime | None = None) -> str:
    current = now or datetime.datetime.now()
    return current.strftime("%d-%m-%Y")


def time_now(now: datetime.datetime | None = None) -> str:
    current = now or datetime.datetime.now()
    return current.strftime("%H:%M")


def read_json(filepath: Path) -> list[dict]:
    if not filepath.exists():
        return []

    with filepath.open("r", encoding="utf-8") as fin:
        obj = json.load(fin)

    if not isinstance(obj, list):
        raise ValueError(f"Expected a list of task records in {filepath!s}")

    return obj


def write_json(filepath: Path, obj: object) -> None:
    with filepath.open("w", encoding="utf-8") as fout:
        json.dump(obj, fout, ensure_ascii=False, indent=2)


def finish_last_entry(filepath: Path) -> None:
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
    log = read_json(filepath)
    if not log:
        print("No tasks recorded for today yet.")
        return

    table = PrettyTable(["Start", "End", "Task"])
    table.align["Task"] = "l"

    for record in log:
        table.add_row([
            str(record.get("start", "")),
            str(record.get("finish") or "-"),
            str(record.get("text", "")),
        ])

    print(table)


if __name__ == "__main__":
    sys.exit(main())
