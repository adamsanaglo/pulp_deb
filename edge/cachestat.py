#!/usr/bin/python3
from collections import defaultdict
import gzip
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import typer

# nginx config file /etc/nginx/conf.d/logging.conf
# log_format better '$time_iso8601 "$request" $status $body_bytes_sent $upstream_cache_status "$http_user_agent"';
log_format = r"^(?P<timestamp>[^ ]+) \"(?P<method>[A-Z]+) (?P<url>.+?) .*?\" (?P<status>\d{3}) (?P<size>\d+) (?P<hitmiss>[^ ]+) \"(?P<agent>.*)\"$"
better_line = re.compile(log_format)

byte_values: Set[str] = {"total_bytes", "total_miss_bytes", "total_churn"}

def grind_logfile(logfile: Path) -> Tuple[float, float, Dict[str, int]]:
    """
    Read a logfile and return a start and end time as well as a dict of stats:
    total_hits, total_misses, total_local, total_expired, total_updating (request counts)
    total_bytes, total_miss_bytes, total_churn (bytes)
    """
    if logfile.suffix == ".gz":
        with gzip.open(logfile, "rt") as f:
            lines = f.readlines()
    else:
        with logfile.open("r") as f:
            lines = f.readlines()
    start_time = 0.0
    end_time = 0.0
    stats: Dict[str, int] = defaultdict(int)
    churn: Dict[str, int] = defaultdict(int)
    bad_lines = 0
    for line_number, line in enumerate(lines):
        try:
            match = better_line.match(line)
            if match:
                if match.group("method") != "GET":
                    continue
                time = float(datetime.fromisoformat(match.group("timestamp")).timestamp())
                if start_time == 0:
                    start_time = time
                end_time = time
                size = int(match.group("size"))
                stats["total_bytes"] += size
                if match.group("hitmiss") == "HIT":
                    stats["total_hits"] += 1
                elif match.group("hitmiss") == "MISS":
                    stats["total_misses"] += 1
                    stats["total_miss_bytes"] += size
                    # Track the largest miss for each URL as the maximal contribution to churn
                    url = match.group("url")
                    churn[url] = max(churn[url], size)
                elif match.group("hitmiss") == "-":
                    stats["total_local"] += 1
                elif match.group("hitmiss") == "EXPIRED":
                    stats["total_expired"] += 1
                elif match.group("hitmiss") == "UPDATING":
                    stats["total_updating"] += 1
                else:
                    print(f"{str(logfile)}:{line_number+1} Unknown hit/miss status {match.group('hitmiss')}")
        except Exception as e:
            print(f"{str(logfile)}:{line_number+1} doesn't match log format")
            bad_lines += 1
            if bad_lines > 5:
                raise Exception("Not a log file")
    # total churn is the sum of the values in the churn dict
    stats["total_churn"] = sum(churn.values())
    return start_time, end_time, stats


# Display table of results
def print_row(logfile, total_hits, total_misses, total_local, total_bytes, total_miss_bytes, total_churn, start=0, end=0, hours=0, is_summary=False, **kwargs):
    prefix = f"{'Grand total':<61}" if is_summary else f"{logfile:<15} {start:>19} {end:>19} {hours:>5.1f}"
    suffix = "----------" if is_summary else f"{total_churn:>10}"
    print(f"{prefix} {total_hits:>10} {total_misses:>10} {total_local:>10} {total_bytes:>10} {total_miss_bytes:>10} {suffix}")


def humanize_bytes(bytes: int) -> str:
    """
    Convert a number of bytes into a human readable string
    """
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
    for unit in units:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} {units[-1]}"


def main(
        logfiles: List[Path] = typer.Argument(..., help="One or more logfiles or directories to process"),
    ):
    summary: Dict[str, int] = defaultdict(int)
    results: Dict[str, Any] = {}

    def handle_logfile(logfile: Path):
        try:
            start, end, stats = grind_logfile(logfile)
        except Exception as e:
            print(f"Skipping {str(logfile)}")
            return
        hours = (end - start) / 3600
        results[str(logfile)] = {
            "start": datetime.fromtimestamp(start).isoformat(sep="T", timespec="seconds"),
            "end": datetime.fromtimestamp(end).isoformat(sep="T", timespec="seconds"),
            "hours": hours
        }
        for k, v in stats.items():
            summary[k] += v
            if k in byte_values:
                v = humanize_bytes(v)
            results[str(logfile)][k] = v

    for logfile in logfiles:
        if logfile.is_dir():
            for child in logfile.glob("**/*"):
                if child.is_file():
                    handle_logfile(child)
        elif logfile.is_file():
            handle_logfile(logfile)
        else:
            print(f"{str(logfile)} is not a file or directory")

    for k, v in summary.items():
        if k in byte_values:
            summary[k] = humanize_bytes(v)

    print(f"{'File':<15} {'        Start':19} {'        End':19} {'Hours':5} {'Hits':>10} {'Misses':>10} {'Local':>10} {'Bytes':>10} {'Miss Bytes':>10} {'Churn':>10}")
    for logfile, result in results.items():
        print_row(logfile, **result)
    print_row("Summary", is_summary=True, **summary)

if __name__ == "__main__":
    typer.run(main)
