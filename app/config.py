from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Workcode Agent"
    admin_email: str = "omasuaku@gmail.com"
    items_per_user: int = 50

    model_config = SettingsConfigDict(env_file=".env")


