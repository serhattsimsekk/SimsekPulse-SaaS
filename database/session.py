import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, with_loader_criteria
from sqlalchemy import event
from .base import tenant_bypass, tenant_context

from .base import Base

def _database_url() -> str:
    value = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://simseklog:simseklog@localhost:5432/simseklog",
    )
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://") :]
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://") :]
    return value


DATABASE_URL = _database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Session, "do_orm_execute")
def enforce_tenant_scope(execute_state):
    if not execute_state.is_select or execute_state.is_column_load or execute_state.is_relationship_load:
        return
    tenant_id = tenant_context.get()
    if tenant_bypass.get():
        return
    if not tenant_id:
        return
    from database import models
    scoped = [cls for cls in vars(models).values() if isinstance(cls, type) and hasattr(cls, "tenant_id")]
    statement = execute_state.statement
    for cls in scoped:
        statement = statement.options(
            with_loader_criteria(cls, lambda row: row.tenant_id == tenant_id, include_aliases=True)
        )
    execute_state.statement = statement


@event.listens_for(Session, "after_begin")
def set_database_tenant(session, transaction, connection):
    tenant_id = tenant_context.get()
    if tenant_id:
        connection.exec_driver_sql(
            "SELECT set_config('app.tenant_id', %s, true)", (tenant_id,)
        )


def get_session() -> Generator[Session, None, None]:
    """İşlem sonunda otomatik kapanan SQLAlchemy oturumu sağlar."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
