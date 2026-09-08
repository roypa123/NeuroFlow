"""Graph construction and validation for one execution. See
docs/12-execution-engine.md #12.2/#12.3.

Reuses the exact validation rules `WorkflowService._collect_graph_errors`
already enforces at save time (docs/09-domain-modules.md), but against the
*runtime* registry (real `app.nodes` classes) rather than the API-safe
descriptor catalog -- the two are built from the same source so they never
disagree, but only the runtime registry can actually execute a node.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.nodes.descriptors import NodeTypeDescriptor
from app.modules.nodes.registry import NodeRegistry
from app.modules.workflows.schemas import GraphEdge, GraphNode, WorkflowGraph


class GraphValidationError(RuntimeError):
    def __init__(self, message: str, *, errors: list[str]) -> None:
        super().__init__(message)
        self.errors = errors


@dataclass(slots=True)
class DagNode:
    node: GraphNode
    descriptor: NodeTypeDescriptor
    incoming: list[GraphEdge] = field(default_factory=list)
    outgoing: list[GraphEdge] = field(default_factory=list)


class DAG:
    def __init__(self, nodes_by_id: dict[str, DagNode]) -> None:
        self.nodes_by_id = nodes_by_id

    @classmethod
    def from_graph(cls, graph: WorkflowGraph, registry: NodeRegistry) -> DAG:
        errors: list[str] = []
        ids = [n.id for n in graph.nodes]
        if len(ids) != len(set(ids)):
            errors.append("Duplicate node ids in graph")
        id_set = set(ids)

        nodes_by_id: dict[str, DagNode] = {}
        for n in graph.nodes:
            try:
                node_cls = registry.get(n.type, n.type_version)
            except KeyError:
                errors.append(f"Unknown node type: {n.type}")
                continue
            nodes_by_id[n.id] = DagNode(node=n, descriptor=node_cls.descriptor)

        for e in graph.edges:
            if e.source not in id_set or e.target not in id_set:
                errors.append(f"Edge {e.id} references an unknown node")
                continue
            if e.source in nodes_by_id and e.target in nodes_by_id:
                nodes_by_id[e.source].outgoing.append(e)
                nodes_by_id[e.target].incoming.append(e)

        if errors:
            raise GraphValidationError(errors[0], errors=errors)

        dag = cls(nodes_by_id)
        dag._check_for_cycles()
        return dag

    def _check_for_cycles(self) -> None:
        white, gray, black = 0, 1, 2
        color = dict.fromkeys(self.nodes_by_id, white)

        def visit(node_id: str) -> None:
            color[node_id] = gray
            for edge in self.nodes_by_id[node_id].outgoing:
                if color[edge.target] == gray:
                    raise GraphValidationError(
                        "Graph contains a cycle", errors=["Graph contains a cycle"]
                    )
                if color[edge.target] == white:
                    visit(edge.target)
            color[node_id] = black

        for node_id in self.nodes_by_id:
            if color[node_id] == white:
                visit(node_id)

    def trigger_node_ids(self) -> list[str]:
        return [
            node_id
            for node_id, dn in self.nodes_by_id.items()
            if not dn.incoming and dn.descriptor.group == "trigger"
        ]
