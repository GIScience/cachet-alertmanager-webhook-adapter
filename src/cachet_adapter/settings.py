from enum import StrEnum

from pydantic import FilePath, HttpUrl
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

    sqlite_file: FilePath = FilePath('cachet_adapter.sqlite')

    model_config = SettingsConfigDict(env_file='.env')
