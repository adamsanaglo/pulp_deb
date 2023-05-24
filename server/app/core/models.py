import enum
import hashlib
import logging
import uuid
from datetime import datetime
from typing import Any, List

from sqlalchemy import UniqueConstraint, event
from sqlmodel import Column
from sqlmodel import Enum as EnumCol
from sqlmodel import Field, Relationship, SQLModel

from app.services.model import signature

logger = logging.getLogger(__name__)


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


class Role(str, enum.Enum):
    Publisher = "Publisher"
    Account_Admin = "Account_Admin"
    Repo_Admin = "Repo_Admin"
    Package_Admin = "Package_Admin"
    Migration = "Migration"  # TODO: [MIGRATE] Remove this role

    def __str__(self) -> str:
        """Return value as the string representation."""
        return str(self.value)


class Account(ModelBase, table=True):
    """Model representing accounts."""

    __table_args__ = (UniqueConstraint("name"), UniqueConstraint("oid"))
    name: str
    # oid is a UUID for an account that we get from Azure Active Directory.
    # https://docs.microsoft.com/en-us/azure/active-directory/develop/access-tokens#payload-claims
    oid: uuid.UUID
    is_enabled: bool
    role: Role = Field(sa_column=Column(EnumCol(Role)))
    icm_service: str
    icm_team: str
    contact_email: str
    repos: List["RepoAccess"] = Relationship(
        back_populates="account",
        sa_relationship_kwargs={"cascade": "delete, delete-orphan"},
    )
    packages: List["OwnedPackage"] = Relationship(
        back_populates="account",
        sa_relationship_kwargs={"cascade": "delete, delete-orphan"},
    )
    signature: str

    def serialize(self) -> str:
        """Serializes a row."""
        fields_data = self.dict(exclude={"signature"})
        fields_data = dict(sorted(fields_data.items()))
        return str(fields_data)

    def hash(self) -> bytes:
        return hashlib.sha256(self.serialize().encode("utf-8")).digest()

    def sign(self) -> None:
        self.signature = signature.sign(self.hash())


@event.listens_for(Account, "before_update")  # type: ignore
@event.listens_for(Account, "before_insert")  # type: ignore
def before_insert_function(mapper: Any, connection: Any, target: Account) -> None:
    target.sign()


class OwnedPackage(ModelBase, table=True):
    """
    A given account should only be allowed to add/delete packages of a certain name if they are the
    owner of that package. This tracks the package ownerships.
    """

    __table_args__ = (UniqueConstraint("account_id", "repo_id", "package_name"),)

    account_id: uuid.UUID = Field(foreign_key="account.id")
    account: Account = Relationship(back_populates="packages")
    repo_id: str
    package_name: str


class RepoAccess(ModelBase, table=True):
    """
    A given account might have Publish roles to three repos but not the rest. This tracks the
    Pulp Ids of repos that accounts have access to.
    """

    __table_args__ = (UniqueConstraint("account_id", "repo_id"),)

    account_id: uuid.UUID = Field(foreign_key="account.id")
    account: Account = Relationship(back_populates="repos")
    repo_id: str
    # This allows the account to CRUD all packages in the repo, see "Repo Operator" role in design.
    operator: bool = Field(default=False, nullable=False)
