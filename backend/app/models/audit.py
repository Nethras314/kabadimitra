"""Audit event domain type."""

from dataclasses import dataclass, field


@dataclass
class AuditEvent:
    action: str
    id: str = ""
    actor_user_id: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    before: dict | None = None
    after: dict | None = None
    created_at: str | None = None
    metadata: dict = field(default_factory=dict)
