from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

@dataclass(slots=True)
class IdempotencyReplay:
    hit: bool
    response_code: int
    response_body: dict[str, Any]

class IdempotencyConflictError(ValueError):
    pass

class IdempotencyService:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def compute_request_hash(payload: dict[str, Any]) -> str:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def acquire(self, *, scope: str, actor_id: str, idempotency_key: str) -> None:
        value = f"{scope}:{actor_id}:{idempotency_key}"
        self.session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:value, 0))"), {"value": value})

    def check(self, *, scope: str, actor_id: str, idempotency_key: str, request_hash: str) -> IdempotencyReplay:
        row = self.session.execute(
            text("SELECT request_hash, response_code, response_body FROM idempotency_record WHERE scope=:scope AND actor_id=:actor_id AND idempotency_key=:key LIMIT 1"),
            {"scope": scope, "actor_id": actor_id, "key": idempotency_key},
        ).mappings().first()
        if row is None:
            return IdempotencyReplay(False, 0, {})
        if row["request_hash"] != request_hash:
            raise IdempotencyConflictError("Idempotency key already used by another payload")
        return IdempotencyReplay(True, int(row["response_code"]), dict(row["response_body"] or {}))

    def persist(self, *, scope: str, actor_id: str, idempotency_key: str, request_hash: str, response_code: int, response_body: dict[str, Any], ttl_hours: int = 24) -> None:
        now = datetime.now(timezone.utc)
        self.session.execute(
            text("""
                INSERT INTO idempotency_record
                    (scope, actor_id, idempotency_key, request_hash, response_code, response_body, created_at, expires_at)
                VALUES (:scope, :actor_id, :key, :request_hash, :response_code, CAST(:response_body AS jsonb), :created_at, :expires_at)
                ON CONFLICT (scope, actor_id, idempotency_key) DO NOTHING
            """),
            {"scope": scope, "actor_id": actor_id, "key": idempotency_key, "request_hash": request_hash, "response_code": response_code, "response_body": json.dumps(response_body, default=str), "created_at": now, "expires_at": now + timedelta(hours=ttl_hours)},
        )
