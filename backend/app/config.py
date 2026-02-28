from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql://simuser:simpassword@127.0.0.1:5433/elastic_simulator"
    es_host: str = "http://localhost:9200"
    es_user: str = "elastic"
    es_password: str = "changeme"
    es_verify_certs: bool = False
    logstash_host: str = "127.0.0.1"
    logstash_port: int = 5000
    
    jwt_secret_key: str = "very_secret_simulator_key_123"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440 # 24 hours

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
