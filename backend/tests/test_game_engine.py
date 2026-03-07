import pytest
from unittest.mock import patch
from app.models import Player, Ticket, TicketStatus
from app.auth import get_password_hash

# Mock out external interactions in main.py namespace safely
@pytest.fixture(autouse=True)
def patch_orchestrator(monkeypatch):
    # Mocking validators
    monkeypatch.setattr("app.main.validate_stage_1", lambda: True)
    monkeypatch.setattr("app.main.validate_stage_2", lambda: True)
    # Mocking triggers
    monkeypatch.setattr("app.main.trigger_scenario_2_replicas", lambda: None)
    monkeypatch.setattr("app.main.trigger_scenario_3_data_view", lambda: None)
    
def get_auth_headers(client, db_session, email="game@example.com", password="password"):
    player = Player(
        username="gameuser",
        email=email,
        hashed_password=get_password_hash(password),
        current_stage=1
    )
    db_session.add(player)
    db_session.commit()
    
    response = client.post(
        "/token",
        data={"username": email, "password": password}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_start_game(client, db_session):
    headers = get_auth_headers(client, db_session)
    response = client.post("/game/start", headers=headers)
    assert response.status_code == 200
    assert "player_id" in response.json()
    
    # Check that a ticket was created
    response_tickets = client.get("/tickets", headers=headers)
    assert response_tickets.status_code == 200
    tickets = response_tickets.json()
    assert len(tickets) == 1
    assert tickets[0]["status"] == "open"
    assert tickets[0]["subject"] == "Billing logs are missing!"

def test_skip_game_stage(client, db_session):
    headers = get_auth_headers(client, db_session, "skip@example.com")
    
    # Start game to get Stage 1 Ticket
    client.post("/game/start", headers=headers)
    
    # Get active ticket
    tickets = client.get("/tickets", headers=headers).json()
    ticket_id = tickets[0]["id"]
    
    # Skip
    response = client.post("/game/skip", json={"ticket_id": ticket_id}, headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] == True
    
    # Verify ticket is now IN_PROGRESS, not RESOLVED
    tickets = client.get("/tickets", headers=headers).json()
    assert len(tickets) == 2 # Auto generated ticket 2
    
    skipped_ticket = next(t for t in tickets if t["id"] == ticket_id)
    assert skipped_ticket["status"] == "in_progress"
    
    new_ticket = next(t for t in tickets if t["id"] != ticket_id)
    assert new_ticket["status"] == "open"
    assert "Cluster Health" in new_ticket["subject"]

def test_validate_game_stage(client, db_session):
    headers = get_auth_headers(client, db_session, "validate@example.com")
    
    client.post("/game/start", headers=headers)
    tickets = client.get("/tickets", headers=headers).json()
    ticket_id = tickets[0]["id"]
    
    # Because validate_stage_1 is mocked to Return True
    response = client.post("/game/validate", json={"ticket_id": ticket_id}, headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] == True
    
    # Ticket should be explicitly RESOLVED
    tickets = client.get("/tickets", headers=headers).json()
    validate_ticket = next(t for t in tickets if t["id"] == ticket_id)
    assert validate_ticket["status"] == "resolved"
