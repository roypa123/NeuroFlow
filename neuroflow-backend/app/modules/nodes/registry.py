"""The node registry. Populated only by `scripts/build_node_catalog.py`
(which imports `app/nodes/`) -- never by the running API process. See
docs/13-node-catalog-and-sdk.md #13.7 and the module docstring in
docs/03-system-architecture.md #3.9 boundary this exists to respect.
"""
from __future__ import annotations

from app.modules.nodes.base import BaseNode
from app.modules.nodes.descriptors import NodeTypeDescriptor


class DuplicateNodeKeyError(ValueError):
    pass


class InvalidNodeDescriptorError(ValueError):
    pass


class NodeRegistry:
    def __init__(self) -> None:
        self._nodes: dict[tuple[str, int], type[BaseNode]] = {}

    def register(self, cls: type[BaseNode]) -> None:
        descriptor = cls.descriptor
        if not descriptor.key:
            raise InvalidNodeDescriptorError(f"{cls.__name__} has an empty key")
        if not descriptor.name:
            raise InvalidNodeDescriptorError(f"{descriptor.key} has an empty name")
        for prop in descriptor.properties:
            if (
                prop.load_options_method is not None
                and prop.type not in ("options", "multiOptions")
            ):
                raise InvalidNodeDescriptorError(
                    f"{descriptor.key}.{prop.name}: load_options_method is only "
                    "valid on options/multiOptions properties"
                )
        registry_key = (descriptor.key, descriptor.version)
        if registry_key in self._nodes:
            raise DuplicateNodeKeyError(
                f"Duplicate node registration: {descriptor.key} v{descriptor.version}"
            )
        self._nodes[registry_key] = cls

    def get(self, key: str, version: int | None = None) -> type[BaseNode]:
        if version is not None:
            return self._nodes[(key, version)]
        candidates = [k for k in self._nodes if k[0] == key]
        if not candidates:
            raise KeyError(key)
        latest = max(candidates, key=lambda k: k[1])
        return self._nodes[latest]

    def all_descriptors(self) -> list[NodeTypeDescriptor]:
        return [cls.descriptor for cls in self._nodes.values()]
