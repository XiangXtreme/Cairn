from __future__ import annotations

import pytest

from cairn.dispatcher.output_parser import extract_json_object
from cairn.dispatcher.contracts import parse_observe_output


def test_extract_json_object_accepts_plain_json() -> None:
    payload = extract_json_object('{"description":"ok"}')

    assert payload == {"description": "ok"}


def test_extract_json_object_accepts_fenced_json() -> None:
    payload = extract_json_object('```json\n{"description":"ok"}\n```')

    assert payload == {"description": "ok"}


def test_extract_json_object_accepts_prose_wrapped_fenced_json() -> None:
    payload = extract_json_object(
        'I checked the page and found the answer.\n```json\n{"accepted":true,"data":{"description":"ok"}}\n```\nNext I would verify it.',
    )

    assert payload == {"accepted": True, "data": {"description": "ok"}}


def test_extract_json_object_accepts_prose_before_inline_json() -> None:
    payload = extract_json_object(
        'Interesting, the endpoint behaves inconsistently. {"fact":{"description":"race works"},"complete":{"description":"done"}} trailing notes.',
    )

    assert payload == {
        "fact": {"description": "race works"},
        "complete": {"description": "done"},
    }


def test_extract_json_object_ignores_braces_inside_strings() -> None:
    payload = extract_json_object(
        'analysis prefix {"description":"value with braces {still text} inside"} suffix',
    )

    assert payload == {"description": "value with braces {still text} inside"}


def test_extract_json_object_raises_for_missing_json() -> None:
    with pytest.raises(ValueError, match="no JSON object found in output"):
        extract_json_object("Let me think this through step by step.")


def test_parse_observe_output_accepts_no_change() -> None:
    kind, data = parse_observe_output("NO_CHANGE\n", max_updates=4)

    assert kind == "noop"
    assert data is None


def test_parse_observe_output_truncates_metadata_updates() -> None:
    kind, data = parse_observe_output(
        """
        {"accepted": true, "data": {
          "hint": {"content": "Course correct."},
          "project_summary": {"content": "Compact state.", "source": "observer"},
          "fact_metadata": [
            {"fact_id": "f001", "kind": "evidence", "confidence": 0.9, "tags": ["web"], "summary": "A", "source": "observer"},
            {"fact_id": "f002", "kind": "failure", "tags": ["sqli"], "summary": "B", "source": "observer"}
          ],
          "intent_metadata": [
            {"intent_id": "i001", "priority": 5, "policy_status": "active", "tags": ["next"], "summary": "C"}
          ]
        }}
        """,
        max_updates=2,
    )

    assert kind == "update"
    assert data is not None
    assert data["hint"] == {"content": "Course correct."}
    assert len(data["fact_metadata"]) == 2
    assert data["intent_metadata"] == []


def test_parse_observe_output_rejects_invalid_policy_status() -> None:
    with pytest.raises(ValueError, match="policy_status"):
        parse_observe_output(
            '{"intent_metadata":[{"intent_id":"i001","policy_status":"done"}]}',
            max_updates=4,
        )
