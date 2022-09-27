import asyncio
import subprocess
from typing import AsyncGenerator, Callable, Generator, Type
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

from app.api.auth import get_active_account
from app.core.config import settings
from app.core.db import async_session, get_session
from app.core.models import Account, Role
from app.main import app as fastapi_app
from app.services.pulp import api as pulp_service_api
from app.services.pulp import content_manager as content_manager_module

from .utils import gen_account_attrs

current_user = Account(**gen_account_attrs())


@pytest.fixture(scope="session")
def event_loop(request) -> Generator:
    """This is magic and needs to be here or everything blows up."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True, scope="session")
def init_db():
    """Create and later destroy the test database."""
    settings.POSTGRES_DB = "test_db"
    db_str = f"docker exec -i {settings.POSTGRES_SERVER} psql -U {settings.POSTGRES_USER} -c "
    db_cmd = db_str.split()
    subprocess.check_call(db_cmd + [f"create database {settings.POSTGRES_DB}"])
    yield
    subprocess.check_call(db_cmd + [f"drop database {settings.POSTGRES_DB} with (FORCE)"])


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Each session will wipe and reinitialize the db. This ensures tests are isolated."""
    # Overriding the default engine here to set echo=False. Dropping and creating the schema every
    # test is very noisy otherwise.
    engine = create_async_engine(settings.db_uri(), echo=False, future=True)
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.drop_all)
        await connection.run_sync(SQLModel.metadata.create_all)
        async with async_session(bind=connection) as session:
            yield session
            await session.flush()
            await session.rollback()


@pytest.fixture()
def override_get_session(db_session: AsyncSession) -> Callable:
    async def _override_get_session():
        yield db_session

    return _override_get_session


@pytest.fixture()
def override_get_active_account() -> Callable:
    """This allows us to mock out the authentication step and return whatever account we please."""

    async def _get_active_account_override():
        return current_user

    return _get_active_account_override


@pytest.fixture()
def app(
    override_get_session: Callable, override_get_active_account: Callable
) -> Generator[FastAPI, None, None]:
    """Replace the app's session with ours, and mock out the authentication step."""
    fastapi_app.dependency_overrides[get_session] = override_get_session
    fastapi_app.dependency_overrides[get_active_account] = override_get_active_account
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


def _with_account(role: Role) -> Account:
    global current_user
    current_user = Account(**gen_account_attrs(role))
    return current_user


@pytest.fixture
def account_admin() -> Account:
    return _with_account(Role.Account_Admin)


@pytest.fixture
def repo_admin() -> Account:
    return _with_account(Role.Repo_Admin)


@pytest.fixture
def package_admin() -> Account:
    return _with_account(Role.Package_Admin)


@pytest.fixture
def publisher() -> Account:
    return _with_account(Role.Publisher)


@pytest.fixture(params=(Role.Account_Admin, Role.Repo_Admin, Role.Package_Admin, Role.Publisher))
def account(request) -> Account:
    """
    This fixture will execute every test that requires it 4 times, once for an account with each
    role.
    """
    return _with_account(request.param)


@pytest.fixture(autouse=True)
def mocked_pulp(monkeypatch):
    def nope(*args, **kwargs):
        raise Exception("You were accidentally about to call out to Pulp. Fix your test setup.")

    monkeypatch.setattr(pulp_service_api.PulpApi, "get", nope)
    monkeypatch.setattr(pulp_service_api.PulpApi, "post", nope)
    monkeypatch.setattr(pulp_service_api.PulpApi, "patch", nope)
    monkeypatch.setattr(pulp_service_api.PulpApi, "delete", nope)


def get_async_mock() -> AsyncMock:
    mock = AsyncMock()
    mock.return_value = None
    return mock


def list_async_mock() -> AsyncMock:
    """Mock that emulates a list endpoint."""
    mock = AsyncMock()
    mock.return_value = {"results": [], "count": 0, "limit": 100, "offset": 0}
    return mock


@pytest.fixture
def distribution_api(monkeypatch) -> Type[pulp_service_api.DistributionApi]:
    for method in ("create", "update", "read", "destroy", "list"):
        monkeypatch.setattr(pulp_service_api.DistributionApi, method, get_async_mock())
    return pulp_service_api.DistributionApi


@pytest.fixture
def repository_api(monkeypatch) -> Type[pulp_service_api.RepositoryApi]:
    for method in ("create", "update", "read", "destroy", "list", "update_content", "publish"):
        monkeypatch.setattr(pulp_service_api.RepositoryApi, method, get_async_mock())
    return pulp_service_api.RepositoryApi


@pytest.fixture
def release_api(monkeypatch) -> Type[pulp_service_api.ReleaseApi]:
    monkeypatch.setattr(pulp_service_api.ReleaseApi, "list", list_async_mock())
    for method in ("create", "update", "read", "destroy", "add_components", "add_architectures"):
        monkeypatch.setattr(pulp_service_api.ReleaseApi, method, get_async_mock())
    return pulp_service_api.ReleaseApi


@pytest.fixture
def orphan_api(monkeypatch) -> Type[pulp_service_api.OrphanApi]:
    for method in ("create", "update", "read", "destroy", "list", "cleanup"):
        monkeypatch.setattr(pulp_service_api.OrphanApi, method, get_async_mock())
    return pulp_service_api.OrphanApi


@pytest.fixture
def package_api(monkeypatch) -> Type[pulp_service_api.PackageApi]:
    for method in (
        "create",
        "update",
        "read",
        "destroy",
        "list",
        "repository_packages",
        "get_package_name",
    ):
        monkeypatch.setattr(pulp_service_api.PackageApi, method, get_async_mock())
    return pulp_service_api.PackageApi


@pytest.fixture
def task_api(monkeypatch) -> Type[pulp_service_api.TaskApi]:
    for method in ("create", "update", "read", "destroy", "list", "cancel"):
        monkeypatch.setattr(pulp_service_api.TaskApi, method, get_async_mock())
    return pulp_service_api.TaskApi


@pytest.fixture
def signing_service_api(monkeypatch) -> Type[pulp_service_api.SigningService]:
    for method in ("create", "update", "read", "destroy", "list", "list_relevant"):
        monkeypatch.setattr(pulp_service_api.SigningService, method, get_async_mock())
    return pulp_service_api.SigningService


@pytest.fixture
def content_manager(monkeypatch) -> Type[content_manager_module.ContentManager]:
    for method in (
        "_get_release_ids",
        "_get_component_ids_in_release",
        "_find_or_create_prc",
        "_find_prc",
        "_update_pulp",
    ):
        monkeypatch.setattr(content_manager_module.ContentManager, method, get_async_mock())
    return content_manager_module.ContentManager
