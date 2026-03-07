from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from .models import ScenarioDifficulty, TicketStatus

# Player schemas
class PlayerBase(BaseModel):
    username: str
    email: str

class PlayerCreate(PlayerBase):
    password: str

class Player(PlayerBase):
    id: int
    current_stage: int
    score: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Scenario schemas
class ScenarioBase(BaseModel):
    title: str
    description: str
    difficulty: ScenarioDifficulty
    stage_order: int
    validation_type: str

class ScenarioCreate(ScenarioBase):
    pass

class Scenario(ScenarioBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)

# Ticket schemas
class TicketBase(BaseModel):
    sender_name: str
    subject: str
    body: str
    hints: Optional[str] = "[]"

class TicketCreate(TicketBase):
    scenario_id: int
    player_id: int

class Ticket(TicketBase):
    id: int
    scenario_id: int
    player_id: int
    status: TicketStatus
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class TicketValidationRequest(BaseModel):
    ticket_id: int

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
