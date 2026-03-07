import pytest
from app.models import Player
from app.auth import get_password_hash

def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Elastic Simulator Engine"}

def test_register_user(client):
    payload = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }
    response = client.post("/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "hashed_password" not in data
    assert "id" in data

def test_register_user_duplicate_email(client, db_session):
    # Base user
    player = Player(
        username="firstuser",
        email="duplicate@example.com",
        hashed_password=get_password_hash("pass")
    )
    db_session.add(player)
    db_session.commit()

    payload = {
        "username": "differentusername",
        "email": "duplicate@example.com",
        "password": "newpassword"
    }
    response = client.post("/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_login_for_access_token(client, db_session):
    # Base user
    player = Player(
        username="loginuser",
        email="login@example.com",
        hashed_password=get_password_hash("password123")
    )
    db_session.add(player)
    db_session.commit()

    # Form URL encoded payload for OAuth2
    response = client.post(
        "/token", 
        data={
            "username": "login@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_password(client, db_session):
    player = Player(
        username="loginuser",
        email="login@example.com",
        hashed_password=get_password_hash("password123")
    )
    db_session.add(player)
    db_session.commit()

    response = client.post(
        "/token", 
        data={
            "username": "login@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"
