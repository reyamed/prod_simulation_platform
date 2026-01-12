from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogType(str, Enum):
    WEB_SERVER = "web_server"
    DATABASE = "database"
    APPLICATION = "application"
    SECURITY = "security"

class LogEntry(BaseModel):
    timestamp: datetime
    level: LogLevel
    log_type: LogType
    message: str
    source: str
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2024-01-15T10:30:00Z",
                "level": "INFO",
                "log_type": "web_server",
                "message": "Request processed successfully",
                "source": "nginx",
                "metadata": {
                    "ip": "192.168.1.100",
                    "status_code": 200
                }
            }
        }

class LogQuery(BaseModel):
    log_type: Optional[LogType] = None
    level: Optional[LogLevel] = None
    source: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    query_string: Optional[str] = None
    size: int = Field(default=100, ge=1, le=1000)
    from_: int = Field(default=0, ge=0, alias="from")

class LogResponse(BaseModel):
    total: int
    logs: list[Dict[str, Any]]
    took: int

