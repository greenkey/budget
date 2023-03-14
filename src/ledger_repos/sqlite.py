import csv
import enum
import logging
import sqlite3
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Generator, Iterable

import config
from src import migrations, models

logger = logging.getLogger(__name__)


Connection = sqlite3.Connection


@contextmanager
def db_context(
    db_path: str | Path | None = None,
) -> Generator[sqlite3.Connection, None, None]:
    """
    Get the default database
    """
    db_path = db_path or config.DB_PATH
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
            kwargs["db"] = db
            return fun(*args, **kwargs)

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

    def filter(self, **kwargs) -> Iterable[models.LedgerItem]:
        """
        Get all the items that match the given filters
        """
        filters = ["1=1"]
        query_params = {}
        for key, value in kwargs.items():
            field__operator = key.split("__")
            if len(field__operator) == 1:
                field = key
                operator = "eq"
            else:
                field, operator = field__operator
            query_params[field] = value
            if operator == "eq":
                filters.append(f"{field} = :{field}")
            elif operator == "gte":
                filters.append(f"{field} >= :{field}")
        query = "SELECT * FROM ledger_items WHERE " + " AND ".join(filters)

        cursor = self.db.execute(query, query_params)

        columns = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            # create dict
            row = dict(zip(columns, row))
            # convert dictionaries to LedgerItem objects
            yield models.LedgerItem(**row)

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
        ledger_items = list(ledger_items)
        if duplicate_strategy == DuplicateStrategy.SKIP:
            for ledger_item in ledger_items:
                ledger_item.to_sync = True

        logger.debug(f"Inserting {len(ledger_items)} items into the database")

        result = self.db.executemany(
            f"""
            INSERT {duplicate_strategy_str} INTO ledger_items ({fields}) VALUES ({placeholders})
            """,
            [models.asdict(ledger_item) for ledger_item in ledger_items],
        )
        logger.debug(f"Inserted {result.rowcount} rows")

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

    def dump(self, table_name: str) -> StringIO:
        """Return a StringIO with the contents of the given table in CSV format"""
        cursor = self.db.execute(f"SELECT * FROM {table_name}")
        columns = [column[0] for column in cursor.description]
        csv_file = StringIO()
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        for row in cursor:
            writer.writerow(dict(zip(columns, row)))
        csv_file.seek(0)
        return csv_file
