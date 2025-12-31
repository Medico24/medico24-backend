"""Tests for Redis caching implementation."""

from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

from app.core.redis_client import CacheManager


def test_cache_manager_get_json():
    """Test CacheManager get_json method."""
    mock_redis = MagicMock()
    cache_manager = CacheManager(redis_client=mock_redis)

    # Test cache miss
    mock_redis.get.return_value = None
    result = cache_manager.get_json("test_key")
    assert result is None
    mock_redis.get.assert_called_once_with("test_key")

    # Test cache hit
    mock_redis.reset_mock()
    mock_redis.get.return_value = '{"name": "Test", "value": 123}'
    result = cache_manager.get_json("test_key")
    assert result == {"name": "Test", "value": 123}
    mock_redis.get.assert_called_once_with("test_key")


def test_cache_manager_set_json():
    """Test CacheManager set_json method."""
    mock_redis = MagicMock()
    cache_manager = CacheManager(redis_client=mock_redis)

    test_data = {"name": "Test", "value": 123}

    # Test without TTL
    result = cache_manager.set_json("test_key", test_data)
    assert result is True
    mock_redis.set.assert_called_once()

    # Test with TTL
    mock_redis.reset_mock()
    result = cache_manager.set_json("test_key", test_data, ttl=300)
    assert result is True
    mock_redis.setex.assert_called_once()


def test_cache_manager_delete():
    """Test CacheManager delete method."""
    mock_redis = MagicMock()
    cache_manager = CacheManager(redis_client=mock_redis)

    result = cache_manager.delete("test_key")
    assert result is True
    mock_redis.delete.assert_called_once_with("test_key")


def test_cache_manager_delete_pattern():
    """Test CacheManager delete_pattern method."""
    mock_redis = MagicMock()
    cache_manager = CacheManager(redis_client=mock_redis)

    # Mock keys method to return some keys
    mock_redis.keys.return_value = [
        "pharmacy:list:0:20:true:null:null:null",
        "pharmacy:list:0:10:true:null:null:null",
        "pharmacy:list:20:20:true:null:null:null",
    ]
    mock_redis.delete.return_value = 3

    result = cache_manager.delete_pattern("pharmacy:list:*")

    mock_redis.keys.assert_called_once_with("pharmacy:list:*")
    # Should delete all matched keys
    assert result == 3


@pytest.mark.asyncio
async def test_user_caching(
    client: AsyncClient,
    auth_headers: dict,
    test_user: dict,
    db_session,
):
    """Test user profile caching."""
    # First request - should cache the user
    response1 = await client.get(
        "/api/v1/users/me",
        headers=auth_headers,
    )
    assert response1.status_code == 200
    user_data_1 = response1.json()

    # Second request - should return cached data
    response2 = await client.get(
        "/api/v1/users/me",
        headers=auth_headers,
    )
    assert response2.status_code == 200
    user_data_2 = response2.json()

    # Data should be identical
    assert user_data_1 == user_data_2
    assert user_data_1["id"] == str(test_user["id"])
    assert user_data_1["email"] == test_user["email"]


@pytest.mark.asyncio
async def test_user_cache_invalidation(
    client: AsyncClient,
    auth_headers: dict,
    test_user: dict,
    db_session,
):
    """Test user cache is invalidated on update."""
    # Get user (caches the data)
    response1 = await client.get(
        "/api/v1/users/me",
        headers=auth_headers,
    )
    assert response1.status_code == 200
    original_name = response1.json()["full_name"]

    # Update user (should invalidate cache)
    update_data = {"full_name": "Updated Name"}
    response2 = await client.patch(
        "/api/v1/users/me",
        headers=auth_headers,
        json=update_data,
    )
    assert response2.status_code == 200
    assert response2.json()["full_name"] == "Updated Name"

    # Get user again (should fetch fresh data, not cached)
    response3 = await client.get(
        "/api/v1/users/me",
        headers=auth_headers,
    )
    assert response3.status_code == 200
    assert response3.json()["full_name"] == "Updated Name"
    assert response3.json()["full_name"] != original_name


@pytest.mark.asyncio
async def test_pharmacy_list_caching(
    client: AsyncClient,
    sample_pharmacy_data: dict,
    db_session,
):
    """Test pharmacy list caching."""
    # Create a pharmacy first
    create_response = await client.post(
        "/api/v1/pharmacies",
        json=sample_pharmacy_data,
    )
    assert create_response.status_code == 201

    # First request - should cache the list
    response1 = await client.get("/api/v1/pharmacies?limit=10")
    assert response1.status_code == 200
    pharmacies_1 = response1.json()
    assert len(pharmacies_1) >= 1

    # Second request with same params - should return cached data
    response2 = await client.get("/api/v1/pharmacies?limit=10")
    assert response2.status_code == 200
    pharmacies_2 = response2.json()

    # Data should be identical
    assert pharmacies_1 == pharmacies_2


@pytest.mark.asyncio
async def test_pharmacy_detail_caching(
    client: AsyncClient,
    sample_pharmacy_data: dict,
    db_session,
):
    """Test individual pharmacy caching."""
    # Create a pharmacy
    create_response = await client.post(
        "/api/v1/pharmacies",
        json=sample_pharmacy_data,
    )
    assert create_response.status_code == 201
    pharmacy_id = create_response.json()["id"]

    # First request - should cache the pharmacy
    response1 = await client.get(f"/api/v1/pharmacies/{pharmacy_id}")
    assert response1.status_code == 200
    pharmacy_1 = response1.json()

    # Second request - should return cached data
    response2 = await client.get(f"/api/v1/pharmacies/{pharmacy_id}")
    assert response2.status_code == 200
    pharmacy_2 = response2.json()

    # Data should be identical
    assert pharmacy_1 == pharmacy_2
    assert pharmacy_1["id"] == pharmacy_id


@pytest.mark.asyncio
async def test_pharmacy_cache_invalidation_on_update(
    client: AsyncClient,
    sample_pharmacy_data: dict,
    db_session,
):
    """Test pharmacy caches are invalidated on update."""
    # Create a pharmacy
    create_response = await client.post(
        "/api/v1/pharmacies",
        json=sample_pharmacy_data,
    )
    assert create_response.status_code == 201
    pharmacy_id = create_response.json()["id"]

    # Get pharmacy detail (caches it)
    response1 = await client.get(f"/api/v1/pharmacies/{pharmacy_id}")
    assert response1.status_code == 200
    original_name = response1.json()["name"]

    # Get pharmacy list (caches the list)
    list_response1 = await client.get("/api/v1/pharmacies?limit=10")
    assert list_response1.status_code == 200

    # Update pharmacy (should invalidate both detail and list caches)
    update_data = {
        "name": "Updated Pharmacy Name",
        "description": "Updated description",
    }
    update_response = await client.patch(
        f"/api/v1/pharmacies/{pharmacy_id}",
        json=update_data,
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Pharmacy Name"

    # Get pharmacy detail again (should be fresh, not cached)
    response2 = await client.get(f"/api/v1/pharmacies/{pharmacy_id}")
    assert response2.status_code == 200
    assert response2.json()["name"] == "Updated Pharmacy Name"
    assert response2.json()["name"] != original_name

    # Get pharmacy list again (should be fresh, not cached)
    list_response2 = await client.get("/api/v1/pharmacies?limit=10")
    assert list_response2.status_code == 200
    # Find the updated pharmacy in the list
    updated_pharmacy = next(
        (p for p in list_response2.json() if p["id"] == pharmacy_id),
        None,
    )
    assert updated_pharmacy is not None
    assert updated_pharmacy["name"] == "Updated Pharmacy Name"


@pytest.mark.asyncio
async def test_pharmacy_cache_different_query_params(
    client: AsyncClient,
    sample_pharmacy_data: dict,
    db_session,
):
    """Test that different query params create different cache keys."""
    # Create a pharmacy
    create_response = await client.post(
        "/api/v1/pharmacies",
        json=sample_pharmacy_data,
    )
    assert create_response.status_code == 201

    # Request with limit=5
    response1 = await client.get("/api/v1/pharmacies?limit=5")
    assert response1.status_code == 200
    pharmacies_5 = response1.json()

    # Request with limit=10
    response2 = await client.get("/api/v1/pharmacies?limit=10")
    assert response2.status_code == 200
    pharmacies_10 = response2.json()

    # Both requests should succeed and potentially have different lengths
    assert len(pharmacies_5) <= 5
    assert len(pharmacies_10) <= 10


@pytest.fixture
def sample_pharmacy_data() -> dict:
    """Sample pharmacy data for testing."""
    return {
        "name": "CacheTest Pharmacy",
        "description": "Testing caching functionality",
        "phone": "+91-9876543210",
        "email": "cache@test.com",
        "supports_delivery": True,
        "supports_pickup": True,
        "location": {
            "address_line": "123 Cache Street",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "pincode": "400001",
            "latitude": 19.0760,
            "longitude": 72.8777,
        },
    }
