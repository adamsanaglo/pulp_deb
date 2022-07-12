import enum
import uuid
from datetime import datetime
from typing import List

from sqlalchemy import UniqueConstraint
from sqlmodel import Column
from sqlmodel import Enum as EnumCol
from sqlmodel import Field, Relationship, SQLModel


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


class Account(ModelBase, table=True):
    """Model representing accounts."""

    __table_args__ = (UniqueConstraint("name"),)
    name: str
    # oid is a UUID for an account that we get from Azure Active Directory. We'll use it as our PK.
    # https://docs.microsoft.com/en-us/azure/active-directory/develop/access-tokens#payload-claims
    id: uuid.UUID = Field(primary_key=True, index=True, nullable=False)  # no default_factory
    is_enabled: bool
    role: Role = Field(sa_column=Column(EnumCol(Role)))
    icm_service: str
    icm_team: str
    contact_email: str
    repos: List["RepoAccess"] = Relationship(back_populates="account")
    packages: List["OwnedPackage"] = Relationship(back_populates="account")


class OwnedPackage(ModelBase, table=True):
    """
    A given account should only be allowed to add/delete packages of a certain name if they are the
    owner of that package. This tracks the package ownerships.
    """

    account_id: uuid.UUID = Field(foreign_key="account.id")
    # account: Account, implicitly created by "back_populates" directive on Account table.
    repo_id: str
    package_name: str


class RepoAccess(ModelBase, table=True):
    """
    A given account might have Publish roles to three repos but not the rest. This tracks the
    Pulp Ids of repos that accounts have access to.
    """

    account_id: uuid.UUID = Field(foreign_key="account.id")
    # account: Account, implicitly created by "back_populates" directive on Account table.
    repo_id: str
    # This allows the account to CRUD all packages in the repo, see "Repo Operator" role in design.
    operator: bool = Field(default=False, nullable=False)
