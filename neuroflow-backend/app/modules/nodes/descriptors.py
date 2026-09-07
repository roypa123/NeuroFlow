"""Node type descriptor model. Pure data -- no execution logic lives here,
which is what makes this module safe for the API server to import while
`app/nodes/` (the real node implementations) stays forbidden to it. See
docs/13-node-catalog-and-sdk.md #13.2 and the import-boundary note in
docs/03-system-architecture.md #3.9.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.schema import CamelModel

PropertyType = Literal[
    "string",
    "number",
    "boolean",
    "options",
    "multiOptions",
    "json",
    "code",
    "credential",
    "collection",
    "resourceLocator",
    "dateTime",
    "color",
    "notice",
    "hidden",
]

NodeGroup = Literal["trigger", "action", "flow", "ai", "data"]


class PortSpec(CamelModel):
    type: str = "main"
    label: str | None = None


class PropertyOption(CamelModel):
    label: str
    value: Any


class DisplayOptions(CamelModel):
    """Conditional field visibility, evaluated on the frontend against
    current parameter values. `show`/`hide` map a parameter name to the
    list of values for which this property is shown/hidden."""

    show: dict[str, list[Any]] | None = None
    hide: dict[str, list[Any]] | None = None


class CredentialRequirement(CamelModel):
    types: list[str]
    required: bool = False


class NodeProperty(CamelModel):
    name: str
    display_name: str
    type: PropertyType
    default: Any = None
    required: bool = False
    description: str | None = None
    placeholder: str | None = None
    options: list[PropertyOption] | None = None
    load_options_method: str | None = None
    display_options: DisplayOptions | None = None
    type_options: dict[str, Any] | None = None
    no_data_expression: bool = False


class NodeTypeDescriptor(CamelModel):
    """`key` is the identifier stored in every saved workflow graph. It can
    never change once shipped -- renaming a node changes `name`, never
    `key`. See docs/13-node-catalog-and-sdk.md #13.2/#13.4."""

    key: str
    version: int = 1
    name: str
    group: NodeGroup
    category: str
    description: str
    icon: str
    color: str
    aliases: list[str] = Field(default_factory=list)
    subtitle: str | None = None
    documentation_url: str | None = None

    inputs: list[PortSpec] = Field(default_factory=list)
    outputs: list[PortSpec] = Field(default_factory=list)
    credentials: list[CredentialRequirement] = Field(default_factory=list)
    properties: list[NodeProperty] = Field(default_factory=list)
    idempotent: bool = False
    supports_error_output: bool = True
    max_items: int | None = None


class PairedItem(BaseModel):
    item: int


class Item(BaseModel):
    json_: dict[str, Any] = Field(default_factory=dict, alias="json")
    paired_item: PairedItem | None = None

    model_config = {"populate_by_name": True}
