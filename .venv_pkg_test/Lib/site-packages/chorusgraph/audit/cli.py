"""`chorusgraph audit` — cold log audit and live pilot ledger reporting."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from chorusgraph.audit.ingest import load_log
from chorusgraph.audit.ledger_report import (
    format_ledger_console_report,
    format_ledger_json_report,
    format_ledger_markdown_report,
    load_ledger_audit,
    summarize_runs,
)
from chorusgraph.audit.report import format_console_report, format_json_report, format_markdown_report
from chorusgraph.audit.simulate import run_cold_audit
from chorusgraph.ledger.sink import SqliteLedgerSink

DEFAULT_LEDGER_DB = Path(".chorusgraph") / "ledger.db"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chorusgraph-audit",
        description=(
            "ChorusGraph audit: cold log simulation (no API key) or live pilot ledger "
            "reporting (measured cache hits and latency)."
        ),
    )
    parser.add_argument("--log", type=Path, help="Cold audit: path to CSV or JSONL query log")
    parser.add_argument(
        "--format",
        choices=("csv", "jsonl"),
        default=None,
        help="Log format (auto-detect from extension/content if omitted)",
    )
    parser.add_argument("--query-column", default=None, help="Query text column name")
    parser.add_argument("--timestamp-column", default=None, help="Timestamp column name")
    parser.add_argument("--tokens-in-column", default=None, help="Input tokens column name")
    parser.add_argument("--tokens-out-column", default=None, help="Output tokens column name")
    parser.add_argument(
        "--category-slug",
        default="general",
        help="Cache category slug for gate thresholds (default: general)",
    )
    parser.add_argument(
        "--ledger",
        metavar="RUN_ID",
        default=None,
        help="Pilot audit: report measured cache hits from a Route Ledger run",
    )
    parser.add_argument(
        "--ledger-db",
        type=Path,
        default=None,
        help=f"SQLite ledger database (default: {DEFAULT_LEDGER_DB})",
    )
    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="List recent ledger runs in --ledger-db (use without --ledger)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument("--markdown", action="store_true", help="Emit Markdown report")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Write report to file instead of stdout",
    )
    return parser


def _emit(text: str, output: Path | None) -> None:
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text.rstrip() + "\n", encoding="utf-8")
    else:
        print(text)


def _run_cold(args: argparse.Namespace) -> int:
    log_path: Path = args.log
    if not log_path.exists():
        print(f"Error: log file not found: {log_path}", file=sys.stderr)
        return 1

    rows = load_log(
        log_path,
        fmt=args.format,
        query_column=args.query_column,
        timestamp_column=args.timestamp_column,
        tokens_in_column=args.tokens_in_column,
        tokens_out_column=args.tokens_out_column,
    )
    if not rows:
        print("Error: no queries found in log.", file=sys.stderr)
        return 1

    result = run_cold_audit(rows, category_slug=args.category_slug)
    if args.json:
        text = format_json_report(result)
    elif args.markdown:
        text = format_markdown_report(result, log_path=str(log_path))
    else:
        text = format_console_report(result, log_path=str(log_path))
    _emit(text, args.output)
    return 0


def _resolve_ledger_db(args: argparse.Namespace) -> Path:
    return args.ledger_db or DEFAULT_LEDGER_DB


def _run_ledger(args: argparse.Namespace) -> int:
    db_path = _resolve_ledger_db(args)
    if not db_path.exists():
        print(f"Error: ledger database not found: {db_path}", file=sys.stderr)
        return 1

    sink = SqliteLedgerSink(db_path)

    if args.list_runs and args.ledger is None:
        rows = summarize_runs(sink)
        if not rows:
            print("No ledger runs found.", file=sys.stderr)
            return 1
        if args.json:
            _emit(json.dumps({"runs": rows}, indent=2), args.output)
        else:
            lines = [f"Ledger runs in {db_path}", "-" * 72]
            lines.append(f"{'run_id':<38} {'graph_id':<18} {'gates':>6} {'rate':>8}")
            for row in rows:
                lines.append(
                    f"{row['run_id']:<38} {row['graph_id']:<18} "
                    f"{row['gate_steps']:>6} {row['cache_hit_rate'] * 100:>7.1f}%"
                )
            _emit("\n".join(lines), args.output)
        return 0

    if args.ledger is None:
        print("Error: pass --ledger <run_id> or --list-runs.", file=sys.stderr)
        return 2

    audit = load_ledger_audit(sink, args.ledger)
    if audit is None:
        print(f"Error: run not found: {args.ledger}", file=sys.stderr)
        return 1

    if args.json:
        text = format_ledger_json_report(audit)
    elif args.markdown:
        text = format_ledger_markdown_report(audit)
    else:
        text = format_ledger_console_report(audit)
    _emit(text, args.output)
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.log is not None and (args.ledger is not None or args.list_runs):
        print("Error: use either --log (cold audit) or --ledger/--list-runs, not both.", file=sys.stderr)
        raise SystemExit(2)

    if args.log is not None:
        raise SystemExit(_run_cold(args))

    if args.ledger is not None or args.list_runs:
        raise SystemExit(_run_ledger(args))

    parser.print_help()
    raise SystemExit(2)


if __name__ == "__main__":
    main()
