"""
Configuration management using Pydantic Settings.

This module provides centralized configuration management for the application.
Environment variables are automatically loaded from .env files and the environment.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from pydantic import field_validator, computed_field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Settings
    api_title: str = "Log Management Platform API"
    api_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # Elasticsearch Settings
    elasticsearch_host: str = "http://localhost:9200"
    elasticsearch_request_timeout: int = 30
    elasticsearch_index_prefix: str = "logs"
    
    # Logstash Settings
    logstash_host: str = "logstash"
    logstash_port: int = 5044
    
    # Database Settings
    database_url: Optional[str] = None
    
    # CORS Settings (comma-separated strings in env, converted to lists)
    cors_allow_origins: str = "*"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "*"
    cors_allow_headers: str = "*"
    
    @staticmethod
    def _parse_list_or_string(v: str) -> List[str]:
        """Parse comma-separated string or return ['*'] if '*'."""
        if v == "*":
            return ["*"]
        return [item.strip() for item in v.split(",") if item.strip()]
    
    @computed_field
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return self._parse_list_or_string(self.cors_allow_origins)
    
    @computed_field
    @property
    def cors_methods_list(self) -> List[str]:
        """Get CORS methods as a list."""
        return self._parse_list_or_string(self.cors_allow_methods)
    
    @computed_field
    @property
    def cors_headers_list(self) -> List[str]:
        """Get CORS headers as a list."""
        return self._parse_list_or_string(self.cors_allow_headers)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra environment variables
    )


# Create a singleton instance
settings = Settings()

