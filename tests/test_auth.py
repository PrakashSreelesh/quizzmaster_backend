"""
Test Auth Endpoints — register, login, /me, error cases.
"""
import pytest


class TestRegister:
    def test_register_instructor(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "newinstructor@test.com",
            "username": "newinstructor",
            "password": "password123",
            "role": "instructor",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newinstructor@test.com"
        assert data["username"] == "newinstructor"
        assert data["role"] == "instructor"
        assert "hashed_password" not in data

    def test_register_student(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "newstudent@test.com",
            "username": "newstudent",
            "password": "password123",
            "role": "student",
        })
        assert response.status_code == 201
        assert response.json()["role"] == "student"

    def test_register_duplicate_email(self, client, instructor_user):
        response = client.post("/api/v1/auth/register", json={
            "email": "instructor@test.com",
            "username": "differentuser",
            "password": "password123",
            "role": "instructor",
        })
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_duplicate_username(self, client, instructor_user):
        response = client.post("/api/v1/auth/register", json={
            "email": "different@test.com",
            "username": "instructor1",
            "password": "password123",
            "role": "instructor",
        })
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]

    def test_register_invalid_role(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "bad@test.com",
            "username": "badrole",
            "password": "password123",
            "role": "admin",
        })
        assert response.status_code == 422

    def test_register_short_password(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "short@test.com",
            "username": "shortpass",
            "password": "ab",
            "role": "student",
        })
        assert response.status_code == 422

    def test_register_short_username(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "short@test.com",
            "username": "ab",
            "password": "password123",
            "role": "student",
        })
        assert response.status_code == 422

    def test_register_invalid_email(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "notanemail",
            "username": "validuser",
            "password": "password123",
            "role": "student",
        })
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client, instructor_user):
        response = client.post("/api/v1/auth/login", data={
            "username": "instructor1",
            "password": "password123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, instructor_user):
        response = client.post("/api/v1/auth/login", data={
            "username": "instructor1",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post("/api/v1/auth/login", data={
            "username": "nouser",
            "password": "password123",
        })
        assert response.status_code == 401


class TestGetMe:
    def test_get_me_authenticated(self, client, instructor_headers, instructor_user):
        response = client.get("/api/v1/auth/me", headers=instructor_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "instructor@test.com"
        assert data["role"] == "instructor"

    def test_get_me_unauthenticated(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
