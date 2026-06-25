"""Отправка xAPI-стейтментов в LRS (Learning Record Store)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import requests

from breaker.core.schema import (
    EventType,
    RitualResult,
    XapiActor,
    XapiStatement,
)


@dataclass
class LrsConfig:
    url: str = "http://localhost:8080/xAPI"
    key: Optional[str] = None
    secret: Optional[str] = None
    mode: str = "mock"

    @classmethod
    def from_env(cls) -> "LrsConfig":
        return cls(
            url=os.getenv("LRS_URL", "http://localhost:8080/xAPI"),
            key=os.getenv("LRS_KEY"),
            secret=os.getenv("LRS_SECRET"),
            mode=os.getenv("LRS_MODE", "mock"),
        )

    @property
    def is_mock(self) -> bool:
        return self.mode.lower() == "mock"


def build_statement(
    result: RitualResult,
    actor: Optional[XapiActor] = None,
    course_id: Optional[str] = None,
    event_type: EventType = EventType.TASK_STARTED,
) -> XapiStatement:
    if actor is None:
        actor = XapiActor(
            mbox=f"mailto:{os.getenv('LEARNER_ID', 'learner_unknown')}@local",
            name=os.getenv("LEARNER_NAME", "Learner"),
        )
    return XapiStatement.from_ritual_result(
        result=result,
        actor=actor,
        course_id=course_id or os.getenv("COURSE_ID"),
        event_type=event_type,
    )


def _send_mock(statement: XapiStatement) -> bool:
    print("\n[MOCK] xAPI statement (not sent to LRS):")
    print(statement.to_json(indent=2))
    return True


def _send_real(statement: XapiStatement, config: LrsConfig) -> bool:
    url = f"{config.url.rstrip('/')}/statements"
    headers = {"Content-Type": "application/json", "X-Experience-API-Version": "1.0.3"}
    auth = (config.key, config.secret) if config.key and config.secret else None

    try:
        response = requests.post(
            url,
            data=statement.to_json(),
            headers=headers,
            auth=auth,
            timeout=10,
        )
        response.raise_for_status()
        print(f"xAPI statement sent to {url}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to send xAPI statement: {e}")
        return False


def send_statement(
    result: RitualResult,
    config: Optional[LrsConfig] = None,
    actor: Optional[XapiActor] = None,
    course_id: Optional[str] = None,
    event_type: EventType = EventType.TASK_STARTED,
) -> bool:
    """Send xAPI statement to LRS (or stdout in mock mode)."""
    if config is None:
        config = LrsConfig.from_env()

    statement = build_statement(result, actor, course_id, event_type)

    if config.is_mock:
        return _send_mock(statement)
    return _send_real(statement, config)


def send_statements_batch(
    results: list[RitualResult],
    config: Optional[LrsConfig] = None,
    **kwargs,
) -> dict:
    """Send multiple statements. Returns stats."""
    if config is None:
        config = LrsConfig.from_env()

    sent = 0
    failed = 0
    for result in results:
        if send_statement(result, config, **kwargs):
            sent += 1
        else:
            failed += 1

    return {"sent": sent, "failed": failed, "total": len(results)}
