from datetime import UTC
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime


def to_utc(value: AwareDatetime) -> AwareDatetime:
    return value.astimezone(UTC)


type UtcDateTime = Annotated[AwareDatetime, AfterValidator(to_utc)]
