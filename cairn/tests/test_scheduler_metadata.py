from __future__ import annotations

from cairn.dispatcher.scheduler.loop import DispatcherLoop
from cairn.server.models import Intent, IntentMetadata, ProjectMetadata


def _intent(intent_id: str, created_at: str) -> Intent:
    return Intent(
        id=intent_id,
        **{"from": ["origin"]},
        to=None,
        description=f"intent {intent_id}",
        creator="tester",
        worker=None,
        last_heartbeat_at=None,
        created_at=created_at,
        concluded_at=None,
    )


def test_scheduler_selects_highest_priority_then_newest_intent() -> None:
    loop = object.__new__(DispatcherLoop)
    metadata = ProjectMetadata(
        project_id="proj_001",
        intents={
            "i001": IntentMetadata(intent_id="i001", priority=1, updated_at="2026-01-01T00:00:00Z"),
            "i002": IntentMetadata(intent_id="i002", priority=5, updated_at="2026-01-01T00:00:00Z"),
            "i003": IntentMetadata(intent_id="i003", priority=5, updated_at="2026-01-01T00:00:00Z"),
        },
    )

    selected = loop._select_explore_intent(
        [
            _intent("i001", "2026-01-01T00:00:01Z"),
            _intent("i002", "2026-01-01T00:00:02Z"),
            _intent("i003", "2026-01-01T00:00:03Z"),
        ],
        metadata,
    )

    assert selected.id == "i003"


def test_scheduler_does_not_dispatch_paused_or_stale_intents() -> None:
    loop = object.__new__(DispatcherLoop)
    metadata = ProjectMetadata(
        project_id="proj_001",
        intents={
            "i001": IntentMetadata(
                intent_id="i001",
                policy_status="paused",
                updated_at="2026-01-01T00:00:00Z",
            ),
            "i002": IntentMetadata(
                intent_id="i002",
                policy_status="stale",
                updated_at="2026-01-01T00:00:00Z",
            ),
        },
    )

    assert loop._intent_dispatchable(_intent("i001", "2026-01-01T00:00:01Z"), metadata) is False
    assert loop._intent_dispatchable(_intent("i002", "2026-01-01T00:00:02Z"), metadata) is False
    assert loop._intent_dispatchable(_intent("i003", "2026-01-01T00:00:03Z"), metadata) is True
