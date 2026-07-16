import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer

from app.core.security import get_password_hash
from app.domain import AdminUser
from app.infra.db import session as session_module
from app.infra.db.session import get_session


@pytest.fixture(scope="session")
def db_engine():
    container = None
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        container = PostgresContainer("postgres:16")
        container.start()
        database_url = container.get_connection_url()
    database_url = database_url.replace("postgresql+psycopg2://", "postgresql+psycopg://")
    os.environ["DATABASE_URL"] = database_url

    config = Config("alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url, pool_pre_ping=True)
    session_module.engine.dispose()
    session_module.engine = engine
    session_module.SessionLocal.configure(bind=engine)
    yield engine

    if container is not None:
        command.downgrade(config, "base")
    engine.dispose()
    if container is not None:
        container.stop()


@pytest.fixture
def db(db_engine) -> Session:
    connection = db_engine.connect()
    transaction = connection.begin()
    testing_session = sessionmaker(bind=connection, autoflush=False, expire_on_commit=False)
    session = testing_session()
    from sqlalchemy import select
    if session.scalar(select(AdminUser).where(AdminUser.username == "admin")) is None:
        session.add(AdminUser(username="admin", password_hash=get_password_hash("admin123"), role="admin"))
    if session.scalar(select(AdminUser).where(AdminUser.username == "coach")) is None:
        session.add(AdminUser(username="coach", password_hash=get_password_hash("coach123"), role="coach"))
    session.flush()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session) -> TestClient:
    from app.main import app

    def override_get_session():
        yield db

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    return login_headers(client, "admin", "admin123")


@pytest.fixture
def coach_headers(client: TestClient) -> dict[str, str]:
    return login_headers(client, "coach", "coach123")
