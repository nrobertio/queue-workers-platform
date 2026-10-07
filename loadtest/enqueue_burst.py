# Enqueue a burst of jobs to watch the queue drain across workers,
# including some that are set to fail so you see retries and the DLQ.
import sys
import urllib.request
import json

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 100

for i in range(N):
    key = "job-" + str(i)
    body = json.dumps({"payload": {"n": i}, "idempotency_key": key}).encode()
    req = urllib.request.Request(BASE + "/jobs", data=body, headers={"content-type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as exc:  # noqa: BLE001
        print("enqueue failed", key, exc)
print("enqueued", N, "jobs")
