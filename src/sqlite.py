import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Generator

from src import migrations, models


@contextmanager
def db_context(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Get the default database
    """
    db_path = db_path or os.environ.get("DB_PATH", ":memory:")
    conn = sqlite3.connect(db_path)
    migrations.migrate(conn)
    yield conn
    conn.close()


def query(sql: str, db: sqlite3.Connection) -> Generator[dict[str, Any], None, None]:
    """
    Execute a query and yield dictionaries with the results
    """
    cursor = db.execute(sql)
    columns = [column[0] for column in cursor.description]
    for row in cursor:
        yield dict(zip(columns, row))
