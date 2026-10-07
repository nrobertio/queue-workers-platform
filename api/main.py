# API: accept a job, enqueue it, return immediately. Query status later.
# Idempotency: if the same key was already accepted, return the existing job id
# instead of enqueueing a duplicate.
import os
import sys

sys.path.append("/app")
from common.job import Job, QUEUE_KEY, STATUS_PREFIX, IDEMPOTENCY_PREFIX

import redis
from fastapi import FastAPI
from pydantic import BaseModel

r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, decode_responses=True)
app = FastAPI(title="queue-api")


class JobIn(BaseModel):
    payload: dict
    idempotency_key: str


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/jobs", status_code=202)
def enqueue(body: JobIn):
    # Idempotency: reserve the key atomically; if it already exists, return the prior id.
    existing = r.get(IDEMPOTENCY_PREFIX + body.idempotency_key)
    if existing:
        return {"id": existing, "status": "already_accepted"}

    job = Job(payload=body.payload, idempotency_key=body.idempotency_key)
    # setnx so two concurrent requests with the same key cannot both enqueue.
    if not r.set(IDEMPOTENCY_PREFIX + body.idempotency_key, job.id, nx=True):
        return {"id": r.get(IDEMPOTENCY_PREFIX + body.idempotency_key), "status": "already_accepted"}

    r.set(STATUS_PREFIX + body.idempotency_key, "queued")
    r.lpush(QUEUE_KEY, job.to_json())
    return {"id": job.id, "status": "queued"}


@app.get("/jobs/{idempotency_key}")
def status(idempotency_key: str):
    st = r.get(STATUS_PREFIX + idempotency_key)
    return {"idempotency_key": idempotency_key, "status": st or "unknown"}
