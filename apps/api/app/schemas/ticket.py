from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    organization_id: UUID = Field(description='Owning organization.')
    brand_id: UUID = Field(description='Owning brand.')
    product_id: UUID | None = Field(default=None, description='Optional product scope.')
    content_item_id: UUID = Field(description='Parent content item.')
    content_version_id: UUID | None = Field(default=None, description='Related content version, if any.')
    type: str = Field(description='Ticket type.')
    reason_codes: list[str] = Field(default_factory=list, description='Reason codes that justify the ticket.')
    comment: str | None = Field(default=None, description='Free-form reviewer comment.')
    status: str = Field(default='open', description='Ticket lifecycle status.')
    priority: str = Field(default='normal', description='Ticket priority.')
    assigned_agent_role: str = Field(default='content_creator', description='Assigned downstream agent or human role.')
    resolved_at: datetime | None = Field(default=None, description='Resolution timestamp.')


class TicketRead(BaseModel):
    id: UUID
    organization_id: UUID
    brand_id: UUID
    product_id: UUID | None
    content_item_id: UUID
    content_version_id: UUID | None
    type: str
    reason_codes: list[str]
    comment: str | None
    status: str
    priority: str
    assigned_agent_role: str
    created_by_id: UUID | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    items: list[TicketRead]


class ContentItemReviewActionRequest(BaseModel):
    reason_codes: list[str] = Field(default_factory=list, description='Reason codes for reject / request revision.')
    comment: str | None = Field(default=None, description='Optional reviewer comment.')
    priority: str = Field(default='normal', description='Ticket priority for the resulting ticket.')
    assigned_agent_role: str = Field(default='content_creator', description='Follow-up agent or human role.')
