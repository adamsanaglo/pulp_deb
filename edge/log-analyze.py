import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

#  log_format noip 'redacted - $remote_user [$time_local] '  '"$request" $status $body_bytes_sent $request_time '  '"$http_referer" "$http_user_agent"';
log_regex = re.compile(
    r"""^(?P<remote_addr>\S+) - (?P<remote_user>\S+) \[(?P<time_local>.+)\] "(?P<method>\S+) (?P<uri>\S+) (?P<protocol>\S+)" (?P<status>\d+) (?P<body_bytes_sent>\d+) (?P<request_time>\d+\.\d+) "(?P<http_referer>.*)" "(?P<http_user_agent>.*)".*$"""
)

per_status_counts = defaultdict(Counter)

status_counts = Counter()
start_time = None
unparseable = set()

with open("access.log") as f:
    for line in f:
        m = log_regex.match(line)
        if m:
            if m.group("remote_addr") != "redacted":
                continue
            local_time = m.group("time_local")
            # convert time string to a time_t
            timet = time.mktime(time.strptime(local_time, "%d/%b/%Y:%H:%M:%S %z"))
            if not start_time:
                start_time = timet
            end_time = timet
            status = m.group("status")
            uri = m.group("uri")
            status_counts[status] += 1
            if status != "200":
                per_status_counts[status][uri] += 1
        else:
            unparseable.add(line)

elapsed_time = end_time - start_time
lines = []
for status, count in status_counts.items():
    lines.append(f"{status}: {count} ({count / elapsed_time:.2f}/s)")
print("\n".join(lines))

missing_files = set()
for uri in per_status_counts["404"].keys():
    # See if the uri exists under /var/www/html
    maybe = Path("/var/www/html") / uri
    if maybe.exists():
        missing_files.add(uri)

if len(missing_files):
    nl = "\n"
    print(f"Missing files:{nl}{nl.join(missing_files)}")
else:
    print("No 404s have existing files under /var/www/html")

real_404 = {}
ignore = re.compile(
    r"^(/clamav/.*\.cld|/sles/1[25]/.+/media\.1/media|.*/repodata/.*\.sqlite\.bz2)$"
)
for uri, count in per_status_counts["404"].items():
    if not ignore.match(uri):
        real_404[uri] = count

print(json.dumps(real_404, indent=4, sort_keys=True))
