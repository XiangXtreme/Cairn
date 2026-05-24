from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from cairn.dispatcher.config import TaskType, WorkerType


DispatchSettingsMode = Literal["file", "ui"]
McpTransportType = Literal["stdio", "http"]
ProviderKind = Literal["claudecode", "codex", "pi"]
FactMetadataKind = Literal["fact", "evidence", "failure", "note", "hint"]
IntentPolicyStatus = Literal["active", "paused", "stale"]


class Settings(BaseModel):
    intent_timeout: int = Field(ge=5)
    reason_timeout: int = Field(ge=5)


class DispatchRuntimeSettings(BaseModel):
    interval: int = Field(gt=0)
    max_workers: int = Field(gt=0)
    max_running_projects: int = Field(gt=0)
    max_project_workers: int = Field(gt=0)
    healthcheck_timeout: int = Field(gt=0)
    prompt_group: str = Field(min_length=1)


class DispatchReasonTaskSettings(BaseModel):
    timeout: int = Field(gt=0)
    max_intents: int = Field(gt=0)
    allow_unavailable_dispatch: bool = False
    unavailable_fact_limit: int = Field(ge=1, default=2)


class DispatchBootstrapTaskSettings(BaseModel):
    timeout: int = Field(gt=0)
    conclude_timeout: int = Field(gt=0)


class DispatchExploreTaskSettings(BaseModel):
    timeout: int = Field(gt=0)
    conclude_timeout: int = Field(gt=0)


class DispatchObserveTaskSettings(BaseModel):
    enabled: bool = False
    timeout: int = Field(gt=0, default=300)
    min_interval_seconds: int = Field(ge=0, default=60)
    recent_run_limit: int = Field(ge=1, default=10)
    max_updates: int = Field(ge=1, default=4)


class DispatchTaskSettings(BaseModel):
    bootstrap: DispatchBootstrapTaskSettings
    reason: DispatchReasonTaskSettings
    explore: DispatchExploreTaskSettings
    observe: DispatchObserveTaskSettings = Field(default_factory=DispatchObserveTaskSettings)


class DispatchWorkerSettings(BaseModel):
    source_name: str = ""
    name: str
    enabled: bool = True
    type: WorkerType
    task_types: list[TaskType]
    max_running: int = Field(gt=0)
    priority: int = Field(ge=0)
    provider_id: str = ""
    provider_supported: bool = False
    model: str = ""
    base_url: str = ""
    auth_token: str = ""
    has_auth_token: bool = False
    provider_api: str = ""
    context_window: int | None = Field(default=None, gt=0)
    extra_env: dict[str, str] = Field(default_factory=dict)
    mcp_server_ids: list[str] = Field(default_factory=list)
    skill_ids: list[str] = Field(default_factory=list)
    mcp_supported: bool = False
    skill_supported: bool = False

    @field_validator("name", "provider_id", "model", "base_url", "auth_token", "provider_api")
    @classmethod
    def normalize_worker_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("task_types")
    @classmethod
    def validate_task_types_non_empty(cls, value: list[TaskType]) -> list[TaskType]:
        if not value:
            raise ValueError("task_types must not be empty")
        if len(set(value)) != len(value):
            raise ValueError("task_types must be unique")
        return value

    @field_validator("mcp_server_ids", "skill_ids")
    @classmethod
    def validate_binding_ids(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("binding ids must be unique")
        return cleaned

    @field_validator("extra_env")
    @classmethod
    def normalize_extra_env(cls, value: dict[str, str]) -> dict[str, str]:
        return {
            str(key).strip(): str(item).strip()
            for key, item in value.items()
            if str(key).strip()
        }


class DispatchModeInfo(BaseModel):
    mode: DispatchSettingsMode = "ui"
    runtime_profile: str = ""
    source_path: str
    compiled_path: str
    hot_reload_enabled: bool = True
    compiled_updated_at: str | None = None
    last_validation_error: str = ""
    observer_enabled: bool = False
    observer_online: bool = False
    observer_url: str = ""
    observer_runtime_root: str = ""


class ProviderSettings(BaseModel):
    id: str
    name: str
    enabled: bool = True
    kind: ProviderKind = "codex"
    model: str = ""
    base_url: str = ""
    auth_token: str = ""
    has_auth_token: bool = False
    provider_api: str = ""
    context_window: int | None = Field(default=None, gt=0)
    extra_env: dict[str, str] = Field(default_factory=dict)

    @field_validator("id", "name", "model", "base_url", "auth_token", "provider_api")
    @classmethod
    def normalize_provider_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("extra_env")
    @classmethod
    def normalize_provider_env(cls, value: dict[str, str]) -> dict[str, str]:
        return {
            str(key).strip(): str(item).strip()
            for key, item in value.items()
            if str(key).strip()
        }


class McpServerSettings(BaseModel):
    id: str
    name: str
    enabled: bool = True
    transport: McpTransportType
    command: str = ""
    url: str = ""
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)

    @field_validator("id", "name", "command", "url")
    @classmethod
    def normalize_mcp_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("args")
    @classmethod
    def normalize_mcp_args(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    @field_validator("env")
    @classmethod
    def normalize_mcp_env(cls, value: dict[str, str]) -> dict[str, str]:
        return {
            str(key).strip(): str(item).strip()
            for key, item in value.items()
            if str(key).strip()
        }


class SkillSettings(BaseModel):
    id: str
    name: str
    enabled: bool = True
    path: str = ""
    description: str = ""
    enabled_claude: bool = False
    enabled_codex: bool = False

    @field_validator("id", "name", "path", "description")
    @classmethod
    def normalize_skill_text(cls, value: str) -> str:
        return value.strip()


class DiscoveredSkill(BaseModel):
    id: str
    name: str
    path: str
    description: str = ""
    source: str = ""
    already_registered: bool = False

    @field_validator("id", "name", "path", "description", "source")
    @classmethod
    def normalize_discovered_skill_text(cls, value: str) -> str:
        return value.strip()


class SkillZipImportRequest(BaseModel):
    mode: DispatchSettingsMode = "ui"
    filename: str
    content_base64: str

    @field_validator("filename", "content_base64")
    @classmethod
    def normalize_zip_import_text(cls, value: str) -> str:
        return value.strip()


class SkillZipImportResponse(BaseModel):
    imported_dir: str
    discovered: list[DiscoveredSkill] = Field(default_factory=list)


class WorkerBindingSettings(BaseModel):
    worker_name: str
    mcp_server_ids: list[str] = Field(default_factory=list)
    skill_ids: list[str] = Field(default_factory=list)

    @field_validator("worker_name")
    @classmethod
    def normalize_worker_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("mcp_server_ids", "skill_ids")
    @classmethod
    def normalize_ids(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("binding ids must be unique")
        return cleaned


class DispatchSettings(BaseModel):
    mode: DispatchSettingsMode = "ui"
    path: str
    writable: bool
    runtime: DispatchRuntimeSettings
    tasks: DispatchTaskSettings
    workers: list[DispatchWorkerSettings]
    mode_info: DispatchModeInfo
    providers: list[ProviderSettings] = Field(default_factory=list)
    mcp_servers: list[McpServerSettings] = Field(default_factory=list)
    skills: list[SkillSettings] = Field(default_factory=list)
    worker_bindings: list[WorkerBindingSettings] = Field(default_factory=list)
    restart_required: bool = False


class UpdateDispatchSettingsRequest(BaseModel):
    mode: DispatchSettingsMode = "ui"
    runtime: DispatchRuntimeSettings
    tasks: DispatchTaskSettings
    workers: list[DispatchWorkerSettings]
    providers: list[ProviderSettings] = Field(default_factory=list)
    mcp_servers: list[McpServerSettings] = Field(default_factory=list)
    skills: list[SkillSettings] = Field(default_factory=list)
    worker_bindings: list[WorkerBindingSettings] = Field(default_factory=list)


class WorkerHealthcheckRequest(BaseModel):
    mode: DispatchSettingsMode = "ui"
    runtime: DispatchRuntimeSettings | None = None
    worker: DispatchWorkerSettings
    providers: list[ProviderSettings] = Field(default_factory=list)
    mcp_servers: list[McpServerSettings] = Field(default_factory=list)
    skills: list[SkillSettings] = Field(default_factory=list)
    worker_bindings: list[WorkerBindingSettings] = Field(default_factory=list)


class WorkerHealthcheckResponse(BaseModel):
    ok: bool
    worker_name: str
    worker_type: WorkerType
    returncode: int
    duration_ms: int
    http_status: str | None = None
    response_preview: str = ""
    stderr_preview: str = ""
    command: str = ""


class Fact(BaseModel):
    id: str
    description: str


class Intent(BaseModel):
    id: str
    from_: list[str] = Field(alias="from")
    to: str | None = None
    description: str
    creator: str
    worker: str | None = None
    last_heartbeat_at: str | None = None
    created_at: str
    concluded_at: str | None = None

    model_config = {"populate_by_name": True}


class Hint(BaseModel):
    id: str
    content: str
    creator: str
    created_at: str


class ProjectReason(BaseModel):
    worker: str
    trigger: str
    started_at: str
    last_heartbeat_at: str


class ProjectMeta(BaseModel):
    id: str
    title: str
    status: Literal["active", "stopped", "completed"]
    created_at: str
    reason: ProjectReason | None = None


class ProjectSummary(ProjectMeta):
    fact_count: int
    intent_count: int
    working_intent_count: int
    unclaimed_intent_count: int
    hint_count: int


class ProjectDetail(BaseModel):
    project: ProjectMeta
    facts: list[Fact]
    intents: list[Intent]
    hints: list[Hint]


class FactMetadata(BaseModel):
    fact_id: str
    kind: FactMetadataKind = "fact"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    source: str = ""
    updated_at: str


class IntentMetadata(BaseModel):
    intent_id: str
    priority: int = 0
    policy_status: IntentPolicyStatus = "active"
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    updated_at: str


class ProjectSummaryMetadata(BaseModel):
    content: str = ""
    source: str = ""
    updated_at: str | None = None


class ObserverCheckpoint(BaseModel):
    last_digest: str = ""
    last_observed_at: str | None = None


class ProjectMetadata(BaseModel):
    project_id: str
    summary: ProjectSummaryMetadata = Field(default_factory=ProjectSummaryMetadata)
    facts: dict[str, FactMetadata] = Field(default_factory=dict)
    intents: dict[str, IntentMetadata] = Field(default_factory=dict)
    observer: ObserverCheckpoint = Field(default_factory=ObserverCheckpoint)


class UpdateFactMetadataRequest(BaseModel):
    kind: FactMetadataKind = "fact"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    source: str = ""

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        cleaned: list[str] = []
        for item in value:
            text = str(item).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            cleaned.append(text)
        return cleaned

    @field_validator("summary", "source")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()


class UpdateIntentMetadataRequest(BaseModel):
    priority: int = 0
    policy_status: IntentPolicyStatus = "active"
    tags: list[str] = Field(default_factory=list)
    summary: str = ""

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        cleaned: list[str] = []
        for item in value:
            text = str(item).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            cleaned.append(text)
        return cleaned

    @field_validator("summary")
    @classmethod
    def normalize_summary(cls, value: str) -> str:
        return value.strip()


class UpdateProjectSummaryRequest(BaseModel):
    content: str
    source: str = ""

    @field_validator("content", "source")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()


class UpdateObserverCheckpointRequest(BaseModel):
    last_digest: str

    @field_validator("last_digest")
    @classmethod
    def normalize_digest(cls, value: str) -> str:
        return value.strip()


class CreateHintInline(BaseModel):
    content: str
    creator: str

    @field_validator("content", "creator")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be empty")
        return text


class CreateProjectRequest(BaseModel):
    title: str
    origin: str
    goal: str
    hints: list[CreateHintInline] | None = None

    @field_validator("title", "origin", "goal")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be empty")
        return text


class CreateHintRequest(BaseModel):
    content: str
    creator: str

    @field_validator("content", "creator")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be empty")
        return text


class CreateIntentRequest(BaseModel):
    from_: list[str] = Field(alias="from", min_length=1)
    description: str
    creator: str
    worker: str | None = None

    model_config = {"populate_by_name": True}

    @field_validator("description", "creator", "worker")
    @classmethod
    def validate_non_empty_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("must not be empty")
        return text

    @field_validator("from_")
    @classmethod
    def validate_fact_ids(cls, value: list[str]) -> list[str]:
        cleaned = []
        for item in value:
            text = item.strip()
            if not text:
                raise ValueError("fact ids must not be empty")
            cleaned.append(text)
        return cleaned


class HeartbeatRequest(BaseModel):
    worker: str

    @field_validator("worker")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be empty")
        return text


class ReasonClaimRequest(BaseModel):
    worker: str
    trigger: str

    @field_validator("worker", "trigger")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be empty")
        return text


class ConcludeRequest(BaseModel):
    worker: str
    description: str

    @field_validator("worker", "description")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be empty")
        return text


class CompleteRequest(BaseModel):
    from_: list[str] = Field(alias="from", min_length=1)
    description: str
    worker: str

    model_config = {"populate_by_name": True}

    @field_validator("description", "worker")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be empty")
        return text

    @field_validator("from_")
    @classmethod
    def validate_fact_ids(cls, value: list[str]) -> list[str]:
        cleaned = []
        for item in value:
            text = item.strip()
            if not text:
                raise ValueError("fact ids must not be empty")
            cleaned.append(text)
        return cleaned


class ConcludeResponse(BaseModel):
    fact: Fact
    intent: Intent


class UpdateProjectStatusRequest(BaseModel):
    status: Literal["active", "stopped"]


class UpdateProjectTitleRequest(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be empty")
        return text


class ReopenRequest(BaseModel):
    description: str
    creator: str

    @field_validator("description", "creator")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("must not be empty")
        return text


class ReopenResponse(BaseModel):
    project: ProjectMeta
    fact: Fact
    intent: Intent


class CloneProjectRequest(BaseModel):
    title: str | None = None

    @field_validator("title")
    @classmethod
    def validate_optional_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("must not be empty")
        return text
