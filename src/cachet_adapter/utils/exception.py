import json
import logging

from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from cachet_adapter.route.adapt import ADAPT_ROUTE

log = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    body = exc.body
    if ADAPT_ROUTE in exc.endpoint_path:
        try:
            body = json.dumps(body, indent=4)
        except Exception as e:
            log.debug('Failed to json-dump erroneous request body', exc_info=e)
    log.debug(
        f"""
Request processing failed with message

{exc}

for body

{body}
"""
    )
    return await request_validation_exception_handler(request, exc)
