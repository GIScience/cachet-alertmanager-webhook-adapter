from enum import StrEnum
from pathlib import Path

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class OverrideMode(StrEnum):
    ALL = 'all'
    SUPPLIER = 'supplier'
    NONE = 'none'


class AdapterSettings(BaseSettings):
    log_level: str = 'INFO'

    port: int = 8002
    root_path: str = '/'

    cachet_api_url: HttpUrl
    cachet_token: str

    message_override: OverrideMode = OverrideMode.SUPPLIER

    sqlite_file: Path = Path(
        'cachet_adapter.sqlite'
    )  # Don't make this a Pydantic FilePath, because we want to create it if it doesn't exist

    model_config = SettingsConfigDict(env_file='.env')
