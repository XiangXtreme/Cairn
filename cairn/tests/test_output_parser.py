from __future__ import annotations

import pytest

from cairn.dispatcher.output_parser import extract_json_object


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
