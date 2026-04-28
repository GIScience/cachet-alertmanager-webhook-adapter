from pathlib import Path

from pydantic import HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class AdapterSettings(BaseSettings):
    log_level: str = 'INFO'

    port: int = 8002
    root_path: str = '/'

    cachet_api_url: HttpUrl
    cachet_token: str

    sqlite_file: Path = 'cachet_adapter.sqlite'

    model_config = SettingsConfigDict(env_file='.env')
