from fastapi import APIRouter

from cairn.server.dispatch_settings import discover_skills, read_dispatch_settings, write_dispatch_settings
from cairn.server.db import get_conn
from cairn.server.models import DiscoveredSkill, DispatchSettings, DispatchSettingsMode, Settings, UpdateDispatchSettingsRequest

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=Settings)
def get_settings():
    with get_conn() as conn:
        row = conn.execute("SELECT intent_timeout, reason_timeout FROM settings WHERE rowid = 1").fetchone()
        return Settings(intent_timeout=row["intent_timeout"], reason_timeout=row["reason_timeout"])


@router.put("/settings", response_model=Settings)
def update_settings(body: Settings):
    with get_conn() as conn:
        conn.execute(
            "UPDATE settings SET intent_timeout = ?, reason_timeout = ? WHERE rowid = 1",
            (body.intent_timeout, body.reason_timeout),
        )
        return body


@router.get("/settings/dispatch", response_model=DispatchSettings)
def get_dispatch_settings(mode: DispatchSettingsMode | None = None):
    return read_dispatch_settings(mode)


@router.put("/settings/dispatch", response_model=DispatchSettings)
def update_dispatch_settings(body: UpdateDispatchSettingsRequest):
    return write_dispatch_settings(body)


@router.get("/settings/dispatch/skills/discover", response_model=list[DiscoveredSkill])
def get_discovered_skills(mode: DispatchSettingsMode | None = None):
    return discover_skills(mode)
