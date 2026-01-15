from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix='/health')


class Health(BaseModel):
    status: Literal['ok', 'error'] = 'ok'


@router.get(path='', status_code=200, summary='Hey, is this thing on?')
def is_ok() -> Health:
    return Health()
