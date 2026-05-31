from pathlib import Path
from pydantic_settings import BaseSettings

_env_file = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    synthesis_backend: str = "ollama"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:32b"
    serper_api_key: str = ""
    linkedin_accounts: str = ""
    pi_url: str = "http://localhost:8000"
    pi_api_secret: str = "changeme"
    my_name: str = ""

    model_config = {"env_file": str(_env_file)}

    def linkedin_account_list(self) -> list[tuple[str, str]]:
        pairs = []
        for entry in self.linkedin_accounts.split(","):
            entry = entry.strip()
            if ":" in entry:
                email, pw = entry.split(":", 1)
                pairs.append((email.strip(), pw.strip()))
        return pairs


settings = Settings()
