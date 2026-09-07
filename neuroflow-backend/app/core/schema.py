"""Shared camelCase Pydantic base for every module's schemas.

See ADR-019 (docs/20-adrs.md) and docs/08-backend-architecture.md #8.7:
camelCase on the wire, snake_case in Python, decided once and applied
everywhere so the two conventions never mix within one payload.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )
