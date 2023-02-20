import sqlite3


def create_ledger_items_table(db: sqlite3.Connection) -> None:
    db.execute(
        """
        CREATE TABLE ledger_items (
            tx_id TEXT UNIQUE PRIMARY KEY,
            tx_date DATE,
            tx_datetime DATETIME,
            amount TEXT,
            currency TEXT,
            description TEXT,
            account TEXT,
            ledger_item_type TEXT,
            counterparty TEXT,
            category TEXT,
            labels TEXT
        )"""
    )


migrations = {
    1: create_ledger_items_table,
}


def migrate(db: sqlite3.Connection) -> None:
    """
    Migrate the database to the latest version
    """
    # get the current version
    current_version = db.execute("PRAGMA user_version").fetchone()[0]
    # get the latest version
    latest_version = max(migrations.keys())
    # apply all the migrations
    for version in range(current_version, latest_version):
        migrations[version + 1](db)
        db.execute(f"PRAGMA user_version = {version + 1}")
