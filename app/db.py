import os
import psycopg2
from contextlib import contextmanager
from typing import Iterator, Optional

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://unap:unap123@localhost:5432/unap_repo"
)

# Opcionales (bueno para producción/local)
DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
DB_APPLICATION_NAME = os.getenv("DB_APPLICATION_NAME", "unap-reco-api")


def get_conn(autocommit: bool = True) -> psycopg2.extensions.connection:
    """
    Crea una conexión nueva (psycopg2).
    - autocommit=True es cómodo para lecturas en API
    """
    conn = psycopg2.connect(
        DB_URL,
        connect_timeout=DB_CONNECT_TIMEOUT,
        application_name=DB_APPLICATION_NAME,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )
    conn.autocommit = autocommit
    return conn


@contextmanager
def db_cursor(autocommit: bool = True) -> Iterator[psycopg2.extensions.cursor]:
    """
    Uso:
      with db_cursor() as cur:
          cur.execute(...)
    """
    conn: Optional[psycopg2.extensions.connection] = None
    try:
        conn = get_conn(autocommit=autocommit)
        with conn.cursor() as cur:
            yield cur
    finally:
        if conn is not None:
            conn.close()