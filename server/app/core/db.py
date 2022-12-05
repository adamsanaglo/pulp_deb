from typing import Any, AsyncGenerator, Mapping, Optional, Sequence, TypeVar, Union, overload

from sqlalchemy import util
from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import engine as _engine
from sqlalchemy.ext.asyncio.engine import AsyncConnection, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.util.concurrency import greenlet_spawn
from sqlmodel import Session, SQLModel
from sqlmodel.engine.result import Result, ScalarResult
from sqlmodel.sql.base import Executable
from sqlmodel.sql.expression import Select, SelectOfScalar

from app.core.config import settings

_TSelectParam = TypeVar("_TSelectParam")


class AsyncSession(_AsyncSession):
    """
    SQLModel provides a Session wrapper over the regular sqlalchemy session that:
    1) unwraps the legacy rows-are-returned-as-objects-wrapped-in-tuples behavior if you call "exec"
    2) passes through Pydantic type hints of the returned objects.

    SQLModel has an equivalent wrapper for AsyncSession (sqlmodel.ext.asyncio.session.AsyncSession),
    but it's busted and throws type errors if you try to use it normally like you would Session.
    There's an upstream PR to fix it, but it's not merged yet. Until it's merged and fixed let's
    just copy-and-paste it in ourselves.
    https://github.com/tiangolo/sqlmodel/pull/58
    """

    sync_session: Session

    def __init__(
        self,
        bind: Optional[Union[AsyncConnection, AsyncEngine]] = None,
        binds: Optional[Mapping[object, Union[AsyncConnection, AsyncEngine]]] = None,
        **kw: Any,
    ):
        # All the same code of the original AsyncSession
        kw["future"] = True
        if bind:
            self.bind = bind
            bind = _engine._get_sync_engine_or_connection(bind)  # type: ignore

        if binds:
            self.binds = binds
            binds = {
                key: _engine._get_sync_engine_or_connection(b)  # type: ignore
                for key, b in binds.items()
            }

        self.sync_session = self._proxied = self._assign_proxied(  # type: ignore
            Session(bind=bind, binds=binds, **kw)  # type: ignore
        )

    @overload
    async def exec(
        self,
        statement: Select[_TSelectParam],
        *,
        params: Optional[Union[Mapping[str, Any], Sequence[Mapping[str, Any]]]] = None,
        execution_options: Mapping[str, Any] = util.EMPTY_DICT,
        bind_arguments: Optional[Mapping[str, Any]] = None,
        _parent_execute_state: Optional[Any] = None,
        _add_event: Optional[Any] = None,
        **kw: Any,
    ) -> Result[_TSelectParam]:
        ...

    @overload
    async def exec(
        self,
        statement: SelectOfScalar[_TSelectParam],
        *,
        params: Optional[Union[Mapping[str, Any], Sequence[Mapping[str, Any]]]] = None,
        execution_options: Mapping[str, Any] = util.EMPTY_DICT,
        bind_arguments: Optional[Mapping[str, Any]] = None,
        _parent_execute_state: Optional[Any] = None,
        _add_event: Optional[Any] = None,
        **kw: Any,
    ) -> ScalarResult[_TSelectParam]:
        ...

    async def exec(  # type: ignore
        self,
        statement: Union[
            Select[_TSelectParam],
            SelectOfScalar[_TSelectParam],
            Executable[_TSelectParam],
        ],
        params: Optional[Union[Mapping[str, Any], Sequence[Mapping[str, Any]]]] = None,
        execution_options: Mapping[Any, Any] = util.EMPTY_DICT,
        bind_arguments: Optional[Mapping[str, Any]] = None,
        **kw: Any,
    ) -> ScalarResult[_TSelectParam]:
        # TODO: the documentation says execution_options accepts a dict, but only
        # util.immutabledict has the union() method. Is this a bug in SQLAlchemy?
        execution_options = execution_options.union({"prebuffer_rows": True})  # type: ignore

        return await greenlet_spawn(
            self.sync_session.exec,
            statement,
            params=params,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
            **kw,
        )

    async def __aenter__(self) -> "AsyncSession":
        # PyCharm does not understand TypeVar here :/
        return await super().__aenter__()


engine = create_async_engine(settings.db_uri(), pool_pre_ping=True, **settings.db_engine_args())
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Function to initialize the database."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a db session."""
    async with async_session() as session:
        yield session
