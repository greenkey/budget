import os
import sqlite3
from contextlib import contextmanager
from typing import Generator, Iterable, Optional

from src import migrations, models

# create a context manager to get the default database


@contextmanager
def db_context() -> Generator[sqlite3.Connection, None, None]:
    """
    Get the default database
    """
    db_path = os.environ.get("DB_PATH", ":memory:")
    conn = sqlite3.connect(db_path)
    migrations.migrate(conn)
    yield conn
    conn.close()


# create a decorator to use the default database
def uses_db(func):
    def wrapper(*args, **kwargs):
        if kwargs.get("db"):
            func(*args, **kwargs)
        else:
            with db_context() as db:
                kwargs["db"] = db
                func(*args, **kwargs)

    return wrapper


@uses_db
def store_ledger_items(
    ledger_items: Iterable[models.LedgerItem], db: sqlite3.Connection
) -> None:
    """
    Store the ledger items in the database
    """
    # bulk insert the ledger items
    db.executemany(
        """
        INSERT INTO ledger_items (
            tx_date,     tx_datetime,    amount,         currency,   description,    account,    ledger_item_type
        ) VALUES (
            :tx_date,    :tx_datetime,   :amount,        :currency,  :description,   :account,   :ledger_item_type
        )
    """,
        map(models.asdict, ledger_items),
    )
