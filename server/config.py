"""
config.py
---------
Centralised settings loaded from environment variables / a .env file.
Every other module imports `settings` from here instead of calling
os.environ directly, so there is exactly one place that knows how
configuration is wired up.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- LLM ---
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # --- Sandbox / agent behaviour ---
    workspace_dir: Path = Path("./workspace")
    max_agent_iterations: int = 12
    tool_timeout_seconds: int = 20

    # --- Server ---
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
