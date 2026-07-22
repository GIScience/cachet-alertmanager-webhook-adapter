import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlmodel import SQLModel, create_engine

from cachet_adapter.route import adapt, component_mapping, health, schedule
from cachet_adapter.settings import AdapterSettings
from cachet_adapter.utils.cachet_api import CachetApi
from cachet_adapter.utils.exception import validation_exception_handler

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
    title='Cachet-compatible Alertmanager Webhook Adapter',
    summary='Prometheus to Cachet Adaptation Service',
    description='A webhook adapter that translates [Prometheus Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/) alerts into [Cachet](https://cachethq.io/) status page incidents, and updates components.',
    version='0.0.1',
    lifespan=configure_dependencies,
    docs_url='/docs',
    redoc_url='/redoc',
)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.include_router(health.router)
app.include_router(adapt.router)
app.include_router(schedule.router)
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
