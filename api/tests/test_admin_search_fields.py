"""Tests for admin search fields API."""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.search_field import SearchField
from app.models.user import User
from app.core.security import get_password_hash, create_access_token


# Setup in-memory SQLite database for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="function")
def setup_database():
    """Setup test database with tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def admin_user(setup_database):
    """Create an admin user and return auth token."""
    db = TestingSessionLocal()

    # Create admin user
    admin = User(
        email="admin@test.com",
        hashed_password=get_password_hash("testpass123"),
        is_admin=True,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    # Create access token
    token = create_access_token({"sub": admin.email})

    db.close()
    return token


@pytest.fixture
def sample_search_field(setup_database):
    """Create a sample search field."""
    db = TestingSessionLocal()

    field = SearchField(
        key="test_field",
        label="Test Field",
        data_type="string",
        storage="extra",
        enabled=True,
        filterable=True,
        sortable=False,
        source_aliases=["Test Field", "test_field"],
    )
    db.add(field)
    db.commit()
    db.refresh(field)

    field_id = field.id
    db.close()
    return field_id


def test_list_search_fields_success(admin_user, sample_search_field):
    """Test GET /api/v1/admin/search/fields returns 200 with proper serialization."""
    response = client.get(
        "/api/v1/admin/search/fields",
        headers={"Authorization": f"Bearer {admin_user}"}
    )

    assert response.status_code == 200
    data = response.json()

    # Should return a list
    assert isinstance(data, list)
    assert len(data) > 0

    # Check first field structure
    field = data[0]
    assert "id" in field
    assert "key" in field
    assert "label" in field
    assert "data_type" in field
    assert "storage" in field
    assert "created_at" in field
    assert "updated_at" in field

    # Verify datetime fields are properly serialized (ISO format string)
    assert isinstance(field["created_at"], str)
    assert isinstance(field["updated_at"], str)
    # Should be parseable as ISO datetime
    datetime.fromisoformat(field["created_at"].replace("Z", "+00:00"))


def test_get_search_field_by_id(admin_user, sample_search_field):
    """Test GET /api/v1/admin/search/fields/{id} returns correct field."""
    response = client.get(
        f"/api/v1/admin/search/fields/{sample_search_field}",
        headers={"Authorization": f"Bearer {admin_user}"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == sample_search_field
    assert data["key"] == "test_field"
    assert data["label"] == "Test Field"
    assert isinstance(data["created_at"], str)
    assert isinstance(data["updated_at"], str)


def test_create_search_field(admin_user, setup_database):
    """Test POST /api/v1/admin/search/fields creates new field."""
    response = client.post(
        "/api/v1/admin/search/fields",
        headers={"Authorization": f"Bearer {admin_user}"},
        json={
            "key": "new_field",
            "label": "New Field",
            "data_type": "integer",
            "storage": "extra",
            "enabled": True,
            "filterable": True,
            "sortable": True,
            "source_aliases": ["New Field", "new_field"],
        }
    )

    assert response.status_code == 201
    data = response.json()

    assert data["key"] == "new_field"
    assert data["label"] == "New Field"
    assert data["data_type"] == "integer"
    assert data["storage"] == "extra"


def test_create_field_invalid_key(admin_user, setup_database):
    """Test creating field with invalid key format fails."""
    response = client.post(
        "/api/v1/admin/search/fields",
        headers={"Authorization": f"Bearer {admin_user}"},
        json={
            "key": "Invalid Key",  # Contains spaces and uppercase
            "label": "Invalid Field",
            "data_type": "string",
            "storage": "extra",
        }
    )

    assert response.status_code == 422  # Validation error


def test_list_fields_without_auth_fails(setup_database):
    """Test accessing admin endpoint without auth returns 401."""
    response = client.get("/api/v1/admin/search/fields")
    assert response.status_code in [401, 403]
