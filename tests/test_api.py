import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test_instagram_feed.db"
engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Instagram Feed Ingestion API"
    assert data["version"] == "1.0.0"


def test_status():
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["accounts"] == 0
    assert data["total_media"] == 0


def test_list_accounts_empty():
    response = client.get("/accounts/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_media_empty():
    response = client.get("/feed/media")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["media"] == []


def test_get_media_not_found():
    response = client.get("/feed/media/nonexistent")
    assert response.status_code == 404


def test_get_account_not_found():
    response = client.get("/accounts/nonexistent")
    assert response.status_code == 404


def test_delete_account_not_found():
    response = client.delete("/accounts/nonexistent")
    assert response.status_code == 404


def test_trigger_ingestion_no_account():
    response = client.post("/feed/ingest/nonexistent")
    assert response.status_code == 404


def test_trigger_ingestion_all_no_accounts():
    response = client.post("/feed/ingest")
    assert response.status_code == 404


def test_get_login_url():
    response = client.get("/auth/login")
    assert response.status_code == 200
    data = response.json()
    assert "auth_url" in data
    assert "api.instagram.com" in data["auth_url"]
