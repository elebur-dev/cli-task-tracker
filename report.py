#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "prettytable",
#     "reportlab",
# ]
# ///
import argparse
import datetime
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from prettytable import PrettyTable
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


DATE_FORMAT = "%d-%m-%Y"
TIME_FORMAT = "%H:%M"
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
    date_help_msg = (
        "A date to show report for.\n"
        "Format: \n"
        "    1) DD-MM-YYYY - exact date to show report for.\n"
        "    2) a single digit - number of days in the past to show report for\n"
        "       (e.g. '0' - today, '1' - show report for yesterday, "
        "        '2' - two days ago and so on)."
    )
    parser.add_argument("-d", "--date", help=date_help_msg)

    subparsers = parser.add_subparsers(dest="command")
    export_parser = subparsers.add_parser(
        "export",
        help="Export all report files to one PDF.",
    )
    export_parser.add_argument(
        "output",
        nargs="?",
        default=str(BASE_DIR / "reports_export.pdf"),
        help="Output PDF path. Default: reports_export.pdf in project root.",
    )

    return parser


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    filepath = report_filepath()

    parser = configure_argparse()
    args = parser.parse_args()

    if len(sys.argv) == 1:
        print_summary(REPORTS_DIR, "0")
        return 0

    if args.command == "export":
        export_reports_to_pdf(REPORTS_DIR, Path(args.output))
    elif args.start is not None:
        add_entry(filepath, args.start)
    elif args.finish:
        finish_last_entry(filepath)
    elif args.date:
        print_summary(REPORTS_DIR, args.date)

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
    return current.strftime(DATE_FORMAT)


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


def print_summary(report_folder: Path, date_str: str) -> None:
    date = parse_date(date_str)
    formatted_date = date.strftime(DATE_FORMAT)
    filepath = report_folder / f"{formatted_date}.json"
    log = read_json(filepath)
    if not log:
        print(f"No tasks recorded for {formatted_date}.")
        return

    table = PrettyTable(["Start", "End", "Duration", "Task"])
    table.title = f"Task for {formatted_date}"
    table.align["Task"] = "l"
    table.max_width["Task"] = 40

    for record in log:
        start_dt_obj = parse_time(record.get("start", ""))
        end_dt_obj = parse_time(record.get("finish", ""))

        # If the task cross the midnight. E.e. start at 23:33, and end at 00:20.
        if start_dt_obj and end_dt_obj and start_dt_obj > end_dt_obj:
            end_dt_obj += datetime.timedelta(days=1)

        if start_dt_obj and end_dt_obj:
            duration = end_dt_obj - start_dt_obj
            # Remove redundant seconds.
            duration = str(duration).removesuffix(":00")
        else:
            duration = "-"

        table.add_row([
            start_dt_obj.strftime(TIME_FORMAT) if start_dt_obj else "",
            end_dt_obj.strftime(TIME_FORMAT) if end_dt_obj else "-",
            duration,
            str(record.get("text", "")),
        ])

    print(table)


def parse_date(date_str: str) -> datetime.datetime | None:
    date = None
    if date_str.isdigit():
        timedelta = datetime.timedelta(days=int(date_str))
        today = datetime.datetime.now()
        return today - timedelta

    try:
        date = datetime.datetime.strptime(date_str, DATE_FORMAT)
    except ValueError:
        print(
            "ERROR: wrong date format has been sent. "
            f"Expected format is DD-MM-YYYY. Received - '{date_str}'"
        )

    return date


def parse_time(time_str: str) -> datetime.datetime | None:
    if not time_str:
        return

    return datetime.datetime.strptime(time_str, TIME_FORMAT)


def export_reports_to_pdf(report_folder: Path, output_path: Path) -> None:
    report_files = sorted_report_files(report_folder)
    if not report_files:
        print("No report files found to export.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
    )
    styles = getSampleStyleSheet()
    task_cell_style = styles["BodyText"].clone("TaskCell")
    task_cell_style.wordWrap = "CJK"
    task_cell_style.splitLongWords = True
    task_cell_style.spaceBefore = 0
    task_cell_style.spaceAfter = 0
    elements: list[object] = []

    for date_obj, filepath in report_files:
        table_data: list[list[object]] = [["Start", "End", "Task"]]
        log = read_json(filepath)

        for record in sorted(log, key=record_start_sort_key):
            task_text = str(record.get("text", "")).strip() or "-"
            table_data.append([
                str(record.get("start", "")).strip() or "-",
                str(record.get("finish", "")).strip() or "-",
                Paragraph(escape(task_text), task_cell_style),
            ])

        if len(table_data) == 1:
            table_data.append([
                "-",
                "-",
                Paragraph("No tasks recorded.", task_cell_style),
            ])

        table = Table(
            table_data,
            colWidths=[80, 80, doc.width - 160],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF1F7")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#22303C")),
                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#CBD7E4")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.HexColor("#FFFFFF"), colors.HexColor("#F7FAFC")],
                ),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#2E3A44")),
                ("ALIGN", (0, 0), (1, -1), "CENTER"),
                ("ALIGN", (2, 0), (2, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5DEE8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])
        )

        elements.extend([
            Paragraph(date_obj.strftime(DATE_FORMAT), styles["Heading2"]),
            Spacer(1, 6),
            table,
            Spacer(1, 12),
        ])

    doc.build(elements)
    print(f"Successfully exported {len(report_files)} report(s) to {output_path}.")


def sorted_report_files(report_folder: Path) -> list[tuple[datetime.datetime, Path]]:
    sortable_files: list[tuple[datetime.datetime, Path]] = []
    for filepath in report_folder.glob("*.json"):
        try:
            date_obj = datetime.datetime.strptime(filepath.stem, DATE_FORMAT)
        except ValueError:
            continue
        sortable_files.append((date_obj, filepath))

    return sorted(sortable_files, key=lambda item: item[0])


def record_start_sort_key(record: dict) -> datetime.datetime:
    start_time = str(record.get("start", "")).strip()
    try:
        parsed_time = parse_time(start_time)
    except ValueError:
        parsed_time = None
    return parsed_time or datetime.datetime.min


if __name__ == "__main__":
    sys.exit(main())
