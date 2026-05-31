from pathlib import Path
from pydantic_settings import BaseSettings

_env_file = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "phi3.5:3.8b"
    pi_api_secret: str = "changeme"
    linkedin_auth_state_path: str = "linkedin_auth.json"
    gmail_address: str = ""
    gmail_app_password: str = ""
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_token_secret: str = ""
    my_name: str = ""

    model_config = {"env_file": str(_env_file)}


settings = Settings()
