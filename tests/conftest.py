import pytest

from src import sqlite


@pytest.fixture
def db(tmp_path):
    db_path = f"{tmp_path}/test.db"
    with sqlite.db_context(db_path) as db:
        yield db
