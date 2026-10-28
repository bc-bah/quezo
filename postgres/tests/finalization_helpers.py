from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4
import hashlib
import json

import psycopg

from fastapi.testclient import TestClient

from identity_helpers import SigningPeer
from db_helpers import IsolatedDatabase
from quezo_api.database import Database
from test_attempts import headers


def legacy_opened(client: TestClient, database: IsolatedDatabase, peer: SigningPeer,
                  policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Seed the actual pre-D04 schema, not the current start API against an old schema."""
    from test_attempts import assigned

    assignment, _ = assigned(client, database, policy)
    attempt_id, key = uuid4(), uuid4()
    fingerprint = hashlib.sha256(json.dumps({
        "actor": assignment["learnerId"], "target": assignment["id"], "operation": "start",
        "key": str(key), "payload": {},
    }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("""
            WITH clock AS MATERIALIZED (SELECT clock_timestamp() AS now)
            INSERT INTO quezo.attempts (id, assignment_id, learner_id, version_id, attempt_number,
                title, instructions, policy, started_at, deadline, possible_points)
            SELECT %s, a.id, a.learner_id, v.id, 1, v.title, v.instructions, v.policy,
                clock.now, least((v.policy->>'availabilityEnd')::timestamptz,
                    clock.now + (v.policy->>'durationSeconds')::integer * interval '1 second'), v.possible_points
            FROM quezo.assignments a JOIN quezo.quiz_versions v ON v.id = a.version_id
            CROSS JOIN clock WHERE a.id = %s
        """, (attempt_id, assignment["id"]))
        connection.execute("""
            INSERT INTO quezo.attempt_questions (id, attempt_id, version_id, question_id,
                question_version_id, position, question, options, effective_points)
            SELECT gen_random_uuid(), %s, quiz_version_id, question_id, question_version_id, position,
                question, question->'options', effective_points FROM quezo.quiz_questions WHERE quiz_version_id = %s
        """, (attempt_id, assignment["versionId"]))
        connection.execute("""
            INSERT INTO quezo.attempt_start_commands (actor_id, assignment_id, operation, request_id, fingerprint, attempt_id)
            SELECT learner_id, id, 'start', %s, %s, %s FROM quezo.assignments WHERE id = %s
        """, (key, fingerprint, attempt_id, assignment["id"]))
        rows = connection.execute(
            "SELECT id, options FROM quezo.attempt_questions WHERE attempt_id = %s ORDER BY position", (attempt_id,),
        ).fetchall()
    return {"id": str(attempt_id), "assignmentId": assignment["id"], "startKey": str(key),
            "questions": [{"attemptQuestionId": str(row[0]), "options": row[1]} for row in rows]}


def submit(client: TestClient, attempt: dict[str, Any], peer: SigningPeer) -> Any:
    return client.post(f"/api/v1/attempts/{attempt['id']}/submission", json={}, headers=headers(peer))


@asynccontextmanager
async def prior_schema_lifespan(database: Database) -> AsyncIterator[None]:
    # Only prior-head migration tests use this: D03 cannot run on an old schema.
    yield
