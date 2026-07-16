import os

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

def test_database_connection_uses_migrated_postgresql(db):
    expected_database = make_url(os.environ["TEST_DATABASE_URL"]).database if os.getenv("TEST_DATABASE_URL") else "test"
    assert db.scalar(text("SELECT current_database()")) == expected_database
    tables = set(inspect(db.bind).get_table_names())
    assert {"admin_user", "member", "card_product", "member_card", "card_transaction", "audit_log"} <= tables
