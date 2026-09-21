from __future__ import annotations

import json
import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


@lru_cache(maxsize=32)
def tenant_engine(tenant_id: str) -> Engine:
    """Returns an optional dedicated tenant engine, falling back to the shared DB."""
    mapping = json.loads(os.getenv("TENANT_DATABASE_URLS", "{}"))
    url = mapping.get(tenant_id) or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL veya TENANT_DATABASE_URLS yapılandırılmalıdır.")
    if url.startswith(("postgres://", "postgresql://")) and "+psycopg" not in url:
        url = url.replace("postgres://", "postgresql+psycopg://", 1).replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url, pool_pre_ping=True, future=True)
