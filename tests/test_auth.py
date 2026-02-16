"""Tests for JWT authentication."""

import pytest
from fastapi.testclient import TestClient

from app.enums import UserRole
from app.services.auth import create_user, get_password_hash


def test_create_user(db):
    """Test creating a user."""
    user = create_user(db, "test@example.com", "testuser", "password123", UserRole.USER)
    assert user.email == "test@example.com"
    assert user.username == "testuser"
    assert user.role == UserRole.USER.value
    assert user.is_active is True


def test_login_success(client: TestClient, db):
    """Test successful login."""
    # Create a test user
    create_user(db, "login@example.com", "loginuser", "password123", UserRole.USER)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient, db):
    """Test login with wrong password."""
    create_user(db, "wrong@example.com", "wronguser", "password123", UserRole.USER)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client: TestClient):
    """Test login with nonexistent user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "password123"},
    )
    assert response.status_code == 401


def test_refresh_token(client: TestClient, db):
    """Test refreshing access token."""
    # Create user and login
    create_user(db, "refresh@example.com", "refreshuser", "password123", UserRole.USER)
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@example.com", "password": "password123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    # Refresh
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_access_protected_endpoint_with_jwt(client: TestClient, db):
    """Test accessing protected endpoint with JWT."""
    # Create admin user
    create_user(db, "admin@example.com", "admin", "password123", UserRole.ADMIN)

    # Login
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "password123"},
    )
    access_token = login_response.json()["access_token"]

    # Access admin endpoint
    response = client.get(
        "/api/v1/audit/logs",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200


def test_access_admin_endpoint_as_user(client: TestClient, db):
    """Test that regular users can't access admin endpoints."""
    # Create regular user
    create_user(db, "user@example.com", "regularuser", "password123", UserRole.USER)

    # Login
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    access_token = login_response.json()["access_token"]

    # Try to access admin endpoint
    response = client.get(
        "/api/v1/audit/logs",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 403  # Forbidden


def test_invalid_token(client: TestClient):
    """Test accessing protected endpoint with invalid token."""
    response = client.get(
        "/api/v1/audit/logs",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
