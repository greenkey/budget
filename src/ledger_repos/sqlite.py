import enum
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Callable, Generator, Iterable

from src import migrations, models

Connection = sqlite3.Connection


@contextmanager
def db_context(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Get the default database
    """
    db_path = db_path or os.environ.get("DB_PATH", ":memory:")
    conn = sqlite3.connect(db_path)
    migrations.migrate(conn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def db(fun: Callable) -> Callable:
    """
    Decorator to use the default database
    """

    def wrapper(*args, **kwargs):
        with db_context() as db:
            return fun(db, *args, **kwargs)

    return wrapper


def query(sql: str, db: sqlite3.Connection) -> Generator[dict[str, Any], None, None]:
    """
    Execute a query and yield dictionaries with the results
    """
    cursor = db.execute(sql)
    columns = [column[0] for column in cursor.description]
    for row in cursor:
        yield dict(zip(columns, row))


class DuplicateStrategy(enum.Enum):
    RAISE = "raise"
    REPLACE = "replace"
    SKIP = "skip"


class LedgerItemRepo:
    def __init__(self, db: Connection):
        self.db = db

    def insert(
        self,
        ledger_items: Iterable[models.LedgerItem],
        duplicate_strategy: DuplicateStrategy = DuplicateStrategy.RAISE,
    ):
        field_names = models.LedgerItem.get_field_names()
        fields = ", ".join(field_names)
        placeholders = ", ".join(f":{field}" for field in field_names)

        duplicate_strategy_str = {
            DuplicateStrategy.RAISE: "OR FAIL",
            DuplicateStrategy.REPLACE: "OR REPLACE",
            DuplicateStrategy.SKIP: "OR IGNORE",
        }[duplicate_strategy]

        # if we are skipping duplicates, it means we are in import phase, we want to sync them
        if duplicate_strategy == DuplicateStrategy.SKIP:
            ledger_items = list(ledger_items)
            for ledger_item in ledger_items:
                ledger_item.to_sync = True

        self.db.executemany(
            f"""
            INSERT {duplicate_strategy_str} INTO ledger_items ({fields}) VALUES ({placeholders})
            """,
            [models.asdict(ledger_item) for ledger_item in ledger_items],
        )

    def get_months(self) -> Iterable[str]:
        query = "SELECT DISTINCT strftime('%Y-%m', tx_date) FROM ledger_items ORDER BY tx_date"
        for row in self.db.execute(query):
            yield row[0]

    def get_month_data(
        self, month: str, only_to_sync: bool = False
    ) -> Iterable[models.LedgerItem]:
        query = "SELECT * FROM ledger_items WHERE strftime('%Y-%m', tx_date) = :month"
        # create cursor for query
        cursor = self.db.execute(query, {"month": month})
        # get columns from curosor
        columns = [column[0] for column in cursor.description]
        # run query to get dictionaries from sqlite
        for row in cursor.fetchall():
            # create dict
            row = dict(zip(columns, row))
            # convert dictionaries to LedgerItem objects
            if only_to_sync and not row["to_sync"]:
                continue
            yield models.LedgerItem(**row)

    def get_updated_data_by_month(self) -> Iterable[tuple[str, Iterable[models.LedgerItem]]]:
        # get all the months that have to_sync set to True
        query = "SELECT DISTINCT strftime('%Y-%m', tx_date) FROM ledger_items WHERE to_sync = 1"
        for row in self.db.execute(query):
            month = row[0]
            yield month, self.get_month_data(month, only_to_sync=True)

    def mark_month_as_synced(self, month: str):
        self.db.execute(
            "UPDATE ledger_items SET to_sync = FALSE WHERE strftime('%Y-%m', tx_date) = :month",
            {"month": month},
        )

    def replace_month_data(self, month: str, ledger_items: Iterable[models.LedgerItem]):
        # delete all rows for the month
        self.db.execute(
            "DELETE FROM ledger_items WHERE strftime('%Y-%m', tx_date) = :month",
            {"month": month},
        )
        # insert new rows
        self.insert(ledger_items, duplicate_strategy=DuplicateStrategy.REPLACE)

    def update(self, ledger_item: models.LedgerItem):
        field_names = models.LedgerItem.get_field_names()
        field_names.remove("tx_id")
        set_string = ", ".join(f"{field} = :{field}" for field in field_names)

        # ensure to_sync is set to True
        ledger_item.to_sync = True

        self.db.execute(
            f"""
            UPDATE ledger_items SET {set_string} WHERE tx_id = :tx_id
            """,
            models.asdict(ledger_item),
        )
