import os
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR.parent.parent
ROOT_ENV_FILE = WORKSPACE_DIR / ".env"
ENV_FILE_PATH = os.getenv("MEW_ENV_FILE", str(ROOT_ENV_FILE if ROOT_ENV_FILE.exists() else BASE_DIR / ".env"))

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[str(ROOT_ENV_FILE), str(BASE_DIR / ".env")],
        extra="ignore"
    )

    api_key: str = ""
    environment: str = "development"
    google_api_key: str = ""

def get_settings() -> Settings:
    env_path = Path(ENV_FILE_PATH)
    current_key = os.getenv("MEW_API_KEY", "")
    
    if not current_key and env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("MEW_API_KEY="):
                    current_key = line.strip().split("=", 1)[1]
                    break

    if not current_key:
        generated_key = f"mew_sk_{secrets.token_hex(16)}"
        with open(env_path, "a" if env_path.exists() else "w") as f:
            f.write(f"\nMEW_API_KEY={generated_key}\n")
        current_key = generated_key

    return Settings(api_key=current_key)
