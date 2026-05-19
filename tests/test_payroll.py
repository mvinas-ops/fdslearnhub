import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.database import get_db
from app.deps import get_current_user  # adjust if path is different


# -----------------------
# MOCK DB DEPENDENCY
# -----------------------
@pytest.fixture
def mock_db():
    db = AsyncMock()

    # default fake result
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        MagicMock(_mapping={
            "hhid": 1,
            "period_id": 2026,
            "month_id": 1,
            "person_id": 1001,
            "services": "Test Service",
            "region": "NCR"
        })
    ]

    mock_result.scalar_one.return_value = 1

    db.execute.return_value = mock_result
    return db


# -----------------------
# MOCK AUTH USER
# -----------------------
@pytest.fixture
def mock_user():
    return {
        "user_id": 1,
        "username": "test_user",
        "role": "Full Account"
    }


# -----------------------
# OVERRIDE DEPENDENCIES
# -----------------------
@pytest.fixture(autouse=True)
def override_all(mock_db, mock_user):

    async def _override_db():
        yield mock_db

    async def _override_user():
        return mock_user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user

    yield

    app.dependency_overrides.clear()


# -----------------------
# TEST CLIENT (FIXED)
# -----------------------
@pytest.fixture
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as ac:
        yield ac

# -----------------------
# TEST: /grants pagination
# -----------------------
@pytest.mark.asyncio
async def test_list_hh_grants(client):
    response = await client.post(
        "/api/payroll/grants",
        params={
            "year": 2026,
            "month": 1,
            "hh_id": "1213",
            "page": 1,
            "limit": 10
        }
    )

    assert response.status_code == 200
    body = response.json()

    assert "meta" in body
    assert "data" in body


# -----------------------
# TEST: /recovery pagination
# -----------------------
@pytest.mark.asyncio
async def test_list_recovery_overpayment(client):
    response = await client.post(
        "/api/payroll/recovery",
        params={
            "year": 2026,
            "month": 1,
            "hh_id": "1213",
            "page": 1,
            "limit": 10
        }
    )

    assert response.status_code == 200
    body = response.json()

    assert "meta" in body
    assert "data" in body

