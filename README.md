# Queue and Workers Platform

A production-shaped async job platform: an API accepts work, pushes it onto a queue, and background workers process it with retries, exponential backoff, and a dead-letter queue for poison messages. The point is to move slow work out of the request path and handle failure correctly, not just show a happy path.

Maintained by nrobertio. A reference for the pattern behind most real backends: decouple the request from the work, and make retries, idempotency and failure explicit.

## What this demonstrates

- Async decoupling: the API returns immediately after enqueueing; workers do the slow work.
- Reliable processing: retries with exponential backoff, a max-attempts limit, and a dead-letter queue (DLQ) so one poison message does not block the pipeline.
- Idempotency: each job carries an idempotency key so a retried or duplicated job is not processed twice.
- Observability: queue depth, processed/failed/retried counters exposed for Prometheus.
- Horizontal scale: run more worker replicas to drain the queue faster.

## Architecture

```
client -> API (enqueue) -> Redis queue -> worker(s) -> result store
                                   |-- retry with backoff (bounded)
                                   |-- dead-letter queue after max attempts
```

## Layout

```
api/            FastAPI service: enqueue jobs, query status
worker/         queue consumer: processing, retries, backoff, DLQ, idempotency
common/         shared queue client and job model
docker-compose.yml   API + Redis + workers
loadtest/       enqueue bursts to watch the queue drain and fail
docs/           PROJECT.md
```

## Run it

```
docker compose up -d --scale worker=3
# enqueue a job
curl -X POST localhost:8000/jobs -H 'content-type: application/json' -d '{"payload":{"n":5},"idempotency_key":"abc"}'
curl localhost:8000/jobs/abc
```

## License

MIT. See LICENSE.
