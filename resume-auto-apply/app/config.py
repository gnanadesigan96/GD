from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    jooble_api_key: str = ""
    data_dir: str = "./data"

    @property
    def data_path(self) -> Path:
        p = Path(self.data_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def resumes_path(self) -> Path:
        p = self.data_path / "resumes"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def generated_path(self) -> Path:
        p = self.data_path / "generated"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.data_path / 'app.db'}"


settings = Settings()
