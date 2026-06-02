import pytest


@pytest.fixture(autouse=True)
def _enable_db_access(db):
    yield
