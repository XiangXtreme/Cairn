from __future__ import annotations

from typing import Any

from cairn.dispatcher.output_parser import extract_json_object


def parse_json_output(stdout: str) -> dict[str, Any]:
    return extract_json_object(stdout)


def parse_observe_output(stdout: str, max_updates: int) -> tuple[str, dict[str, Any] | None]:
    if stdout.strip() == "NO_CHANGE":
        return "noop", None
    payload = parse_json_output(stdout)
    return validate_observe_payload(payload, max_updates=max_updates)


def _unwrap_wrapped_payload(payload: dict[str, Any]) -> tuple[bool | None, dict[str, Any] | None]:
    accepted = payload.get("accepted")
    if accepted is False:
        return False, None
    if accepted is True:
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ValueError("data must be an object")
        return True, data
    return None, None


def _is_dict(value: Any) -> bool:
    return isinstance(value, dict)


def _looks_like_reason_data(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False
    keys = set(payload)
    if keys == {"complete"}:
        complete = payload["complete"]
        return isinstance(complete, dict) and "from" in complete and "description" in complete
    if keys == {"intents"}:
        return isinstance(payload["intents"], list)
    if keys == {"intent"}:
        intent = payload["intent"]
        return isinstance(intent, dict) and "from" in intent and "description" in intent
    return False


def _looks_like_bootstrap_execute_data(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict) or set(payload) != {"fact", "complete"}:
        return False
    return _is_dict(payload.get("fact")) and _is_dict(payload.get("complete"))


def _looks_like_bootstrap_conclude_data(payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False
    keys = set(payload)
    if keys not in ({"fact"}, {"fact", "complete"}):
        return False
    return _is_dict(payload.get("fact"))


def _looks_like_explore_data(payload: dict[str, Any]) -> bool:
    return isinstance(payload, dict) and set(payload) == {"description"}


def validate_reason_payload(
    payload: dict[str, Any], open_intents_empty: bool, max_intents: int,
) -> tuple[str, dict[str, Any] | list[dict[str, Any]] | None]:
    accepted, data = _unwrap_wrapped_payload(payload)
    if accepted is False:
        return "rejected", None
    if accepted is None:
        if payload == {}:
            data = {}
        else:
            if not _looks_like_reason_data(payload):
                raise ValueError("accepted must be true or false")
            data = payload
    if not isinstance(data, dict):
        raise ValueError("accepted must be true or false")
    complete = data.get("complete")
    intents = data.get("intents")
    # backward compat: accept singular "intent" key from LLMs
    if intents is None:
        singular = data.get("intent")
        if isinstance(singular, dict):
            intents = [singular]
    if complete is not None:
        if intents is not None:
            raise ValueError("complete and intents cannot coexist")
        if not isinstance(complete, dict) or "from" not in complete or "description" not in complete:
            raise ValueError("invalid complete payload")
        return "complete", complete
    if intents is not None:
        if not isinstance(intents, list):
            raise ValueError("intents must be an array")
        for i, intent in enumerate(intents):
            if not isinstance(intent, dict) or "from" not in intent or "description" not in intent:
                raise ValueError(f"invalid intent at index {i}")
        intents = intents[:max_intents]
        if not intents:
            return "noop", None
        return "intents", intents
    return "noop", None


def validate_bootstrap_execute_payload(payload: dict[str, Any]) -> tuple[str, dict[str, str] | None]:
    accepted, data = _unwrap_wrapped_payload(payload)
    if accepted is False:
        return "rejected", None
    if accepted is None:
        if not _looks_like_bootstrap_execute_data(payload):
            raise ValueError("accepted must be true or false")
        data = payload
    if not isinstance(data, dict):
        raise ValueError("accepted must be true or false")

    fact = data.get("fact")
    if not isinstance(fact, dict):
        raise ValueError("fact is required")
    fact_description = fact.get("description")
    if not isinstance(fact_description, str) or not fact_description.strip():
        raise ValueError("fact.description is required")

    result = {"fact_description": fact_description.strip()}
    complete = data.get("complete")
    if complete is None:
        raise ValueError("complete is required")
    if not isinstance(complete, dict):
        raise ValueError("complete must be an object")
    complete_description = complete.get("description")
    if not isinstance(complete_description, str) or not complete_description.strip():
        raise ValueError("complete.description is required")
    result["complete_description"] = complete_description.strip()
    return "complete", result


def validate_bootstrap_conclude_payload(payload: dict[str, Any]) -> tuple[str, str | None]:
    accepted, data = _unwrap_wrapped_payload(payload)
    if accepted is False:
        return "rejected", None
    if accepted is None:
        if not _looks_like_bootstrap_conclude_data(payload):
            raise ValueError("accepted must be true or false")
        data = payload
    if not isinstance(data, dict):
        raise ValueError("accepted must be true or false")
    extra_keys = set(data) - {"fact", "complete"}
    if extra_keys:
        raise ValueError("unexpected keys in conclude payload")
    fact = data.get("fact")
    if not isinstance(fact, dict):
        raise ValueError("fact is required")
    fact_description = fact.get("description")
    if not isinstance(fact_description, str) or not fact_description.strip():
        raise ValueError("fact.description is required")
    return "fact", fact_description.strip()


def validate_explore_payload(payload: dict[str, Any]) -> tuple[str, str | None]:
    accepted, data = _unwrap_wrapped_payload(payload)
    if accepted is False:
        return "rejected", None
    if accepted is None:
        if not _looks_like_explore_data(payload):
            raise ValueError("accepted must be true or false")
        data = payload
    if not isinstance(data, dict):
        raise ValueError("accepted must be true or false")
    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("description is required")
    return "fact", description.strip()


def validate_observe_payload(payload: dict[str, Any], max_updates: int) -> tuple[str, dict[str, Any] | None]:
    accepted, data = _unwrap_wrapped_payload(payload)
    if accepted is False:
        return "rejected", None
    if accepted is None:
        data = payload
    if not isinstance(data, dict):
        raise ValueError("accepted must be true or false")
    hint = _validate_observe_hint(data.get("hint"))
    project_summary = _validate_observe_project_summary(data.get("project_summary"))
    fact_metadata = _validate_observe_fact_metadata_list(data.get("fact_metadata"))
    intent_metadata = _validate_observe_intent_metadata_list(data.get("intent_metadata"))
    limited_fact_metadata, limited_intent_metadata = _limit_observe_updates(
        fact_metadata,
        intent_metadata,
        max_updates=max_updates,
    )
    result = {
        "hint": hint,
        "project_summary": project_summary,
        "fact_metadata": limited_fact_metadata,
        "intent_metadata": limited_intent_metadata,
    }
    if not hint and not project_summary and not limited_fact_metadata and not limited_intent_metadata:
        return "noop", None
    return "update", result


def _validate_observe_hint(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("hint must be an object")
    content = value.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("hint.content is required")
    return {"content": content.strip()}


def _validate_observe_project_summary(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("project_summary must be an object")
    content = value.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("project_summary.content is required")
    source = value.get("source", "observer")
    if not isinstance(source, str):
        raise ValueError("project_summary.source must be a string")
    return {"content": content.strip(), "source": source.strip() or "observer"}


def _validate_observe_fact_metadata_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("fact_metadata must be an array")
    return [_validate_observe_fact_metadata(item, index) for index, item in enumerate(value)]


def _validate_observe_intent_metadata_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("intent_metadata must be an array")
    return [_validate_observe_intent_metadata(item, index) for index, item in enumerate(value)]


def _validate_observe_fact_metadata(value: Any, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"fact_metadata[{index}] must be an object")
    fact_id = _required_text(value, "fact_id", f"fact_metadata[{index}]")
    kind = _optional_choice(
        value,
        "kind",
        f"fact_metadata[{index}]",
        {"fact", "evidence", "failure", "note", "hint"},
        default="fact",
    )
    confidence = value.get("confidence")
    if confidence is not None:
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError(f"fact_metadata[{index}].confidence must be a number")
        confidence = float(confidence)
        if confidence < 0 or confidence > 1:
            raise ValueError(f"fact_metadata[{index}].confidence must be between 0 and 1")
    return {
        "fact_id": fact_id,
        "kind": kind,
        "confidence": confidence,
        "tags": _normalize_tags(value.get("tags")),
        "summary": _optional_text(value, "summary"),
        "source": _optional_text(value, "source") or "observer",
    }


def _validate_observe_intent_metadata(value: Any, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"intent_metadata[{index}] must be an object")
    intent_id = _required_text(value, "intent_id", f"intent_metadata[{index}]")
    policy_status = _optional_choice(
        value,
        "policy_status",
        f"intent_metadata[{index}]",
        {"active", "paused", "stale"},
        default="active",
    )
    priority = value.get("priority", 0)
    if isinstance(priority, bool) or not isinstance(priority, int):
        raise ValueError(f"intent_metadata[{index}].priority must be an integer")
    return {
        "intent_id": intent_id,
        "priority": priority,
        "policy_status": policy_status,
        "tags": _normalize_tags(value.get("tags")),
        "summary": _optional_text(value, "summary"),
    }


def _required_text(value: dict[str, Any], key: str, prefix: str) -> str:
    raw = value.get(key)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{prefix}.{key} is required")
    return raw.strip()


def _optional_text(value: dict[str, Any], key: str) -> str:
    raw = value.get(key, "")
    if raw is None:
        return ""
    if not isinstance(raw, str):
        raise ValueError(f"{key} must be a string")
    return raw.strip()


def _optional_choice(
    value: dict[str, Any],
    key: str,
    prefix: str,
    allowed: set[str],
    *,
    default: str,
) -> str:
    raw = value.get(key, default)
    if not isinstance(raw, str) or raw not in allowed:
        raise ValueError(f"{prefix}.{key} must be one of: {', '.join(sorted(allowed))}")
    return raw


def _normalize_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("tags must be an array")
    seen: set[str] = set()
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _limit_observe_updates(
    fact_metadata: list[dict[str, Any]],
    intent_metadata: list[dict[str, Any]],
    *,
    max_updates: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    budget = max(0, max_updates)
    limited_fact_metadata = fact_metadata[:budget]
    remaining = max(0, budget - len(limited_fact_metadata))
    limited_intent_metadata = intent_metadata[:remaining]
    return limited_fact_metadata, limited_intent_metadata
