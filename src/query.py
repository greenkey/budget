import sqlite3
from typing import Any, Generator

from src.operations import db_context, uses_db


def query(sql: str) -> Generator[dict[str, Any], None, None]:
    """
    Execute a query and yield the results
    """
    with db_context() as db:
        cursor = db.execute(sql)
        columns = [column[0] for column in cursor.description]
        for row in cursor:
            yield dict(zip(columns, row))
