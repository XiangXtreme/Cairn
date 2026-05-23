from __future__ import annotations

from fastapi import APIRouter

from cairn.server.db import get_conn
from cairn.server.models import (
    FactMetadata,
    IntentMetadata,
    ObserverCheckpoint,
    ProjectMetadata,
    ProjectSummaryMetadata,
    UpdateFactMetadataRequest,
    UpdateIntentMetadataRequest,
    UpdateObserverCheckpointRequest,
    UpdateProjectSummaryRequest,
)
from cairn.server.services import (
    build_project_metadata,
    upsert_fact_metadata,
    upsert_intent_metadata,
    upsert_observer_checkpoint,
    upsert_project_summary,
)

router = APIRouter(tags=["metadata"])


@router.get("/projects/{project_id}/metadata", response_model=ProjectMetadata)
def get_project_metadata(project_id: str):
    with get_conn() as conn:
        return build_project_metadata(conn, project_id)


@router.patch(
    "/projects/{project_id}/facts/{fact_id}/metadata",
    response_model=FactMetadata,
)
def update_fact_metadata(project_id: str, fact_id: str, body: UpdateFactMetadataRequest):
    with get_conn() as conn:
        return upsert_fact_metadata(conn, project_id, fact_id, body)


@router.patch(
    "/projects/{project_id}/intents/{intent_id}/metadata",
    response_model=IntentMetadata,
)
def update_intent_metadata(project_id: str, intent_id: str, body: UpdateIntentMetadataRequest):
    with get_conn() as conn:
        return upsert_intent_metadata(conn, project_id, intent_id, body)


@router.put(
    "/projects/{project_id}/summary",
    response_model=ProjectSummaryMetadata,
)
def update_project_summary(project_id: str, body: UpdateProjectSummaryRequest):
    with get_conn() as conn:
        return upsert_project_summary(conn, project_id, body)


@router.put(
    "/projects/{project_id}/observer/checkpoint",
    response_model=ObserverCheckpoint,
)
def update_observer_checkpoint(project_id: str, body: UpdateObserverCheckpointRequest):
    with get_conn() as conn:
        return upsert_observer_checkpoint(conn, project_id, body)
