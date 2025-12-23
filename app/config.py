from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""

    google_api_key: str = ""

    mongodb_uri: str = ""

    mongodb_db: str = ""

    mongodb_collection: str = ""

    mongodb_index: str = ""

    firebase_service_account_file: str = ""

    indexing_pwd: str = "----"

    model_config = SettingsConfigDict(env_file=".env")
