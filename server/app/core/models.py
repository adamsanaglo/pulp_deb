import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class ModelBase(SQLModel):
    """Base model with common fields."""

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    created_at: datetime = Field(default=datetime.utcnow(), nullable=False)
    last_edited: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class Publisher(ModelBase, table=True):
    """Model representing publishers."""

    __table_args__ = (UniqueConstraint("name"),)
    name: str
    is_enabled: bool
    is_account_admin: bool
    is_repo_admin: bool
    is_package_admin: bool
    icm_service: str
    icm_team: str
    contact_email: str
