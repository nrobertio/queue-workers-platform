# Worker: pop a job, process it, and handle failure correctly.
# - exponential backoff between retries
# - bounded attempts, then dead-letter
# - idempotent processing (skip if already done)
import os
import sys
import time

sys.path.append("/app")
from common.job import (
    Job, QUEUE_KEY, DLQ_KEY, STATUS_PREFIX, MAX_ATTEMPTS,
)

import redis

r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, decode_responses=True)

# Fail injection for testing retry/DLQ behaviour.
FAIL_KEYS = set(filter(None, os.getenv("FAIL_KEYS", "").split(",")))


def process(job: Job) -> None:
    # Idempotency guard: if this key is already marked done, skip reprocessing.
    if r.get(STATUS_PREFIX + job.idempotency_key) == "done":
        return
    # Simulated work. A key listed in FAIL_KEYS always fails, to exercise retries/DLQ.
    if job.idempotency_key in FAIL_KEYS:
        raise RuntimeError("injected failure for " + job.idempotency_key)
    time.sleep(0.2)
    r.set(STATUS_PREFIX + job.idempotency_key, "done")


def run() -> None:
    print("worker started", flush=True)
    while True:
        item = r.brpop(QUEUE_KEY, timeout=5)
        if not item:
            continue
        _, raw = item
        job = Job.from_json(raw)
        try:
            process(job)
            print("processed", job.idempotency_key, flush=True)
        except Exception as exc:  # noqa: BLE001
            job.attempts += 1
            if job.attempts >= MAX_ATTEMPTS:
                r.set(STATUS_PREFIX + job.idempotency_key, "dead_letter")
                r.lpush(DLQ_KEY, job.to_json())
                print("dead-lettered", job.idempotency_key, str(exc), flush=True)
            else:
                backoff = min(2 ** job.attempts, 30)
                r.set(STATUS_PREFIX + job.idempotency_key, "retrying")
                print("retry", job.idempotency_key, "attempt", job.attempts, "in", backoff, "s", flush=True)
                time.sleep(backoff)
                r.lpush(QUEUE_KEY, job.to_json())


if __name__ == "__main__":
    run()
