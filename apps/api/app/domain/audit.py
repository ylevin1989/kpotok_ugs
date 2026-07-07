from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog


def record_audit(
    db: Session,
    *,
    actor_user_id: UUID,
    action: str,
    entity_type: str,
    entity_id: str,
    organization_id: UUID | None = None,
    metadata: dict[str, object] | None = None,
    ip: str | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata,
        ip=ip,
    )
    db.add(audit_log)
    return audit_log
