import os
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker, with_loader_criteria

from .base import Base, tenant_bypass, tenant_context


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
    # Postgres ulaşılamaz/yanıt vermez (ör. yanlış host, güvenlik duvarı
    # paketleri sessizce düşürüyor) durumunda psycopg varsayılan olarak
    # işletim sisteminin TCP zaman aşımına kadar (dakikalarca, bazen hiç)
    # bekleyebilir. Bu da API isteklerinin (ör. /login) tarayıcıda hiçbir
    # hata vermeden sonsuza dek "yükleniyor" gibi görünmesine yol açar.
    # "connect_timeout" ile bağlantı kurma denemesini makul bir sürede
    # (10 sn) anlamlı bir hataya çeviriyoruz.
    connect_args={"connect_timeout": 10},
    # Havuzdaki tüm bağlantılar meşgulse yeni bir istek en fazla 10 saniye
    # bekler, sonra TimeoutError fırlatır; sonsuza dek askıda kalmaz.
    pool_timeout=10,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Session, "do_orm_execute")
def enforce_tenant_scope(execute_state):
    """All SELECTs that resolve tenant-aware models are filtered by current tenant.

    This is a logical isolation layer for multi-tenant operation, enforced in
    addition to PostgreSQL RLS so a tenant cannot access another tenant's data
    even when ORM queries are built manually.
    """
    if not execute_state.is_select or execute_state.is_column_load or execute_state.is_relationship_load:
        return

    tenant_id = tenant_context.get()
    if tenant_bypass.get() or not tenant_id:
        return

    from database import models

    scoped = [
        cls for cls in vars(models).values()
        if isinstance(cls, type) and hasattr(cls, "tenant_id")
    ]
    if not scoped:
        return

    statement = execute_state.statement
    for cls in scoped:
        statement = statement.options(
            with_loader_criteria(
                cls,
                lambda row, cls=cls: row.tenant_id == tenant_id,
                include_aliases=True,
            )
        )
    execute_state.statement = statement


@event.listens_for(Session, "after_begin")
def set_database_tenant(session, transaction, connection):
    """Sets the current tenant into PostgreSQL session settings so RLS can apply.

    When a tenant-specific JWT is present, the database session stores that value
    in app.tenant_id; when a super-admin bypass is active, RLS is not enforced.
    """
    tenant_id = tenant_context.get()
    if tenant_id:
        connection.exec_driver_sql(
            "SELECT set_config('app.tenant_id', %s, true)",
            (tenant_id,),
        )
    else:
        connection.exec_driver_sql(
            "SELECT set_config('app.tenant_id', '', true)"
        )


@event.listens_for(Session, "before_commit")
def validate_tenant_on_write(session):
    """Rejects writes to tenant-scoped tables unless a tenant is active."""
    tenant_id = tenant_context.get()
    if tenant_bypass.get() or tenant_id:
        return

    from database import models

    for instance in list(session.new) + list(session.dirty):
        if not hasattr(instance, "tenant_id"):
            continue
        raise PermissionError(
            "Tenant context is required before write operations on tenant-scoped tables."
        )


def get_session() -> Generator[Session, None, None]:
    """Returns a database session with automatic cleanup."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
