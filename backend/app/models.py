from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from .database import Base

class ScenarioDifficulty(enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    difficulty = Column(Enum(ScenarioDifficulty))
    stage_order = Column(Integer)  # 1, 2, 3...
    
    # Internal validation logic key
    validation_type = Column(String)  # e.g., "check_mapping", "check_unassigned_shards"
    hints = Column(Text, default="[]")
    
    # Relationships
    tickets = relationship("Ticket", back_populates="scenario")

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    current_stage = Column(Integer, default=1)
    score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class TicketStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    
    sender_name = Column(String)  # The simulated user complaining
    subject = Column(String)
    body = Column(Text)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    hints = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scenario = relationship("Scenario", back_populates="tickets")
    player = relationship("Player")
