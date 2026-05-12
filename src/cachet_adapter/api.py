import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine

from cachet_adapter.route import adapt, component_mapping, health
from cachet_adapter.settings import AdapterSettings
from cachet_adapter.utils.cachetapi import CachetApi

log = logging.getLogger(__name__)


@asynccontextmanager
async def configure_dependencies(the_app: FastAPI):
    log.debug('Configuring API')
    settings = AdapterSettings()

    the_app.state.cachet_api = CachetApi(base_url=settings.cachet_api_url, token=settings.cachet_token)

    sqlite_url = f'sqlite:///{settings.sqlite_file}'

    connect_args = {'check_same_thread': False}
    engine = create_engine(sqlite_url, connect_args=connect_args)
    SQLModel.metadata.create_all(engine)

    the_app.state.db_engine = engine
    log.debug('API configured')
    yield


app = FastAPI(
    title='HeiGIT Status Adapter',
    summary='Prometheus to Cachet adaption service',
    description='A mere wrapper that takes Prometheus Alertmanager post requests and translates them to Cachet incidents.',
    version='0.0.1',
    contact={
        'name': 'HeiGIT',
        'url': 'https://heigit.org',
        'email': 'info@heigit.org',
    },
    lifespan=configure_dependencies,
    docs_url='/docs',
    redoc_url='/redoc',
)

app.include_router(health.router)
app.include_router(adapt.router)
app.include_router(component_mapping.router)


def main():
    settings = AdapterSettings()
    logging.basicConfig(level=settings.log_level.upper())
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=settings.port,
        root_path=settings.root_path,
        log_level=settings.log_level.lower(),
    )


if __name__ == '__main__':
    main()
