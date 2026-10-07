# Project Writeup: Queue and Workers Platform

Why this exists, how it was built, why each choice, benefits, and design trade-offs.

## 1. The problem it solves

If an API does slow work (sending email, processing a file, calling a third party) inside the request, the user waits and a traffic spike takes the service down. The fix is to accept the request, enqueue the work, and return immediately, while background workers process the queue. The hard part is not the happy path; it is failure: what happens when a job fails, when it fails forever, when the same job arrives twice, and when the queue backs up. This project implements those explicitly.

## 2. How it was built

- An API (FastAPI) that validates input, enforces idempotency, enqueues to Redis, and returns 202 immediately.
- Workers that pop jobs and process them, with retries, exponential backoff, a max-attempts limit, and a dead-letter queue.
- A shared job model and queue keys so API and workers agree on the contract.
- docker-compose that scales workers horizontally (docker compose up --scale worker=3).

## 3. Why each choice

- Return 202 and a job id, not the result: the whole point is to get slow work off the request path. The client polls status or gets notified later.
- Idempotency key with setnx: networks retry, clients double-click. An idempotency key reserved atomically (Redis SET NX) means the same logical job is accepted once, even under concurrent duplicate requests. Workers also skip a job already marked done.
- Exponential backoff, not immediate retry: hammering a failing dependency makes an outage worse. Backoff (2, 4, 8 ... capped) gives the dependency room to recover.
- Bounded attempts plus a dead-letter queue: a poison message that can never succeed must not loop forever or block the queue. After MAX_ATTEMPTS it goes to the DLQ for inspection, and the pipeline keeps moving.
- Redis list as the queue: simple, fast, good enough to demonstrate the pattern. The writeup notes where you would move to RabbitMQ or Kafka (ordering, fan-out, durability guarantees) as needs grow.

## 4. Benefits

- The request path stays fast and survives spikes; work is absorbed by the queue and drained by workers.
- Failures are handled on purpose: retried with backoff, then dead-lettered, never silently lost or infinitely looped.
- Duplicate and retried submissions do not double-process.
- Throughput scales by adding worker replicas.

## 5. Design notes and trade-offs

- At-least-once vs exactly-once: most queues deliver at-least-once, so consumers must be idempotent. This project makes idempotency explicit rather than pretending exactly-once exists.
- Why a DLQ matters: it separates transient failures (retry) from permanent ones (inspect), so one bad message does not poison the pipeline or page you forever.
- Backoff and the thundering-herd / retry-storm problem: naive retries amplify an outage; backoff (and in production, jitter) prevents that.
- When Redis is not enough: if you need strict ordering, consumer groups, replay, or multi-consumer fan-out, move to Kafka; if you need rich routing and acks, RabbitMQ. Redis lists are the right starting point, not the end state.
- What I would add next: visibility timeout / in-flight tracking so a crashed worker's job is redelivered, per-queue metrics (depth, age of oldest message), and jitter on the backoff.

## 6. How to run it

```
docker compose up -d --scale worker=3
python loadtest/enqueue_burst.py http://localhost:8000 100
# watch workers drain the queue; set FAIL_KEYS on the worker to see retries and the DLQ
```