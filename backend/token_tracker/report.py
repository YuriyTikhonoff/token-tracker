#!/usr/bin/env python3
"""Print token-usage reports from the token-tracker SQLite database.

Run ingest.py first (or use it as a cron job) to populate the database.
"""
import argparse
from datetime import datetime
from pathlib import Path

from . import queries

DEFAULT_DB_PATH = queries.DEFAULT_DB_PATH


def format_tokens(count):
    if count > 1_000_000:
        millions = count / 1_000_000
        decimals = 2 if millions < 10 else 1
        return f"{millions:,.{decimals}f} mln"
    if count >= 1_000:
        return f"{count / 1_000:,.1f}k"
    return f"{count:,}"


def format_cost(amount):
    return f"${amount:,.2f}"


def format_local(iso_timestamp):
    if not iso_timestamp:
        return iso_timestamp
    try:
        parsed = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    except ValueError:
        return iso_timestamp
    return parsed.astimezone(queries.LOCAL_TZ).strftime("%Y-%m-%d %H:%M")


def print_totals(totals):
    print("=== Totals (all time) ===")
    print(f"  input tokens:          {format_tokens(totals['input_tokens'])}")
    print(f"  output tokens:         {format_tokens(totals['output_tokens'])}")
    print(f"  cache creation tokens: {format_tokens(totals['cache_creation_tokens'])}")
    print(f"  cache read tokens:     {format_tokens(totals['cache_read_tokens'])}")
    print(f"  estimated cost:        {format_cost(totals['cost'])}")
    print()


def print_by_project(entries):
    print("=== By project ===")
    for entry in entries:
        print(f"  {entry['project']:<70} {format_tokens(entry['tokens']):>15} tokens  {format_cost(entry['cost']):>12}")
    print()


def print_by_session(entries, limit):
    print(f"=== Top {limit} sessions by cost ===")
    for entry in entries:
        print(
            f"  {entry['session_id']}  {entry['project']:<50} "
            f"{format_tokens(entry['tokens']):>12} tokens  {format_cost(entry['cost']):>12}  "
            f"last: {format_local(entry['last_seen'])}"
        )
    print()


def print_by_prompt(entries, limit):
    print(f"=== Top {limit} prompts by cost ===")
    for entry in entries:
        preview = (entry["preview"] or "").replace("\n", " ")[:80]
        print(
            f"  {format_cost(entry['cost']):>12}  {format_tokens(entry['tokens']):>10} tokens  "
            f"{format_local(entry['timestamp'])}  {preview}"
        )
    print()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--pricing", type=Path, default=None, help="Use only this pricing file")
    parser.add_argument("--top", type=int, default=15, help="Row limit for session/prompt breakdowns")
    parser.add_argument("--account", help="Only this account_uuid (default: all accounts combined)")
    args = parser.parse_args(argv)

    if not args.db.exists():
        raise SystemExit(f"No database at {args.db} — run ingest.py first.")

    pricing = queries.load_pricing(args.pricing)
    connection = queries.connect(args.db)

    print_totals(queries.get_totals(connection, pricing, account=args.account))
    print_by_project(queries.get_by_project(connection, pricing, account=args.account))
    print_by_session(queries.get_by_session(connection, pricing, args.top, account=args.account), args.top)
    print_by_prompt(queries.get_by_prompt(connection, pricing, args.top, account=args.account), args.top)

    connection.close()


if __name__ == "__main__":
    main()
