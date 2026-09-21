from sqlalchemy.orm import DeclarativeBase
from contextvars import ContextVar

tenant_context: ContextVar[str | None] = ContextVar("tenant_context", default=None)
tenant_bypass: ContextVar[bool] = ContextVar("tenant_bypass", default=False)


class Base(DeclarativeBase):
    """Tüm ORM modellerinin ortak tabanı."""
