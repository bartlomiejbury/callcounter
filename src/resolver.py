#!/usr/bin/env python3
import subprocess
from collections import defaultdict
import argparse

parser = argparse.ArgumentParser(description="Function call report")
parser.add_argument("--binary", required=True, help="Path to binary with -g")
parser.add_argument("--input", required=True, help="Count file (callcounter.raw)")
parser.add_argument("--output", required=True, help="Report output file")
parser.add_argument("--sum", action="store_true", help="Sum all threads")
parser.add_argument("--threaded", action="store_true", help="Report for each thread separately")
args = parser.parse_args()

if args.sum == args.threaded:
    raise ValueError("Choose exactly one mode: --sum or --threaded")


if args.sum:
    func_counts = defaultdict(int)
    with open(args.input, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 3:
                continue
            addr, count, _ = parts
            try:
                count = int(count)
            except ValueError:
                continue
            func_counts[addr] += count
    thread_maps = {"ALL_THREADS": func_counts}

elif args.threaded:
    thread_maps = defaultdict(lambda: defaultdict(int))
    with open(args.input, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 3:
                continue
            addr, count, thread_hash = parts
            try:
                count = int(count)
            except ValueError:
                continue
            thread_maps[thread_hash][addr] += count


unique_addrs = set()
for addr_counts in thread_maps.values():
    unique_addrs.update(addr_counts.keys())

addr2line_map = {}
if unique_addrs:
    proc = subprocess.run(
        ["addr2line", "-f", "-C", "-e", args.binary] + list(unique_addrs),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    lines = proc.stdout.strip().splitlines()
    unique_addrs_list = list(unique_addrs)
    for i, addr in enumerate(unique_addrs_list):
        func_name = lines[2*i].strip() if 2*i < len(lines) else "<unknown>"
        file_line = lines[2*i+1].strip() if 2*i+1 < len(lines) else "<unknown>"
        addr2line_map[addr] = (func_name, file_line)


def colorize(count, max_count):
    ratio = count / max_count if max_count > 0 else 0
    if ratio > 0.66:
        return f"\033[91m{count}\033[0m"  # red
    elif ratio > 0.33:
        return f"\033[93m{count}\033[0m"  # yellow
    else:
        return f"\033[92m{count}\033[0m"  # green


with open(args.output, "w") as f:
    for thread, addr_counts in thread_maps.items():
        print(f"=== Thread {thread} ===")
        f.write(f"=== Thread {thread} ===\n")

        if not addr_counts:
            continue

        # Prepare data for display
        rows = []
        max_count = max(addr_counts.values())
        for addr, count in sorted(addr_counts.items(), key=lambda x: -x[1]):
            func_name, file_line = addr2line_map.get(addr, ("<unknown>", "<unknown>"))
            rows.append((func_name, file_line, count))

        # Calculate column widths
        max_func_len = max(len(row[0]) for row in rows)
        max_file_len = max(len(row[1]) for row in rows)
        max_func_len = max(max_func_len, len("Function"))
        max_file_len = max(max_file_len, len("File:Line"))

        # Header
        header = f"{'Function':<{max_func_len}}  {'File:Line':<{max_file_len}}  Call Count"
        print(header)
        f.write(header + "\n")

        # Rows
        for func_name, file_line, count in rows:
            colored_count = colorize(count, max_count)
            print(f"{func_name:<{max_func_len}}  {file_line:<{max_file_len}}  {colored_count}")
            f.write(f"{func_name:<{max_func_len}}  {file_line:<{max_file_len}}  {count}\n")

        print()
        f.write("\n")

print(f"Report saved to {args.output}")
