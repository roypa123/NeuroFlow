"""DAG construction and validation. See docs/12-execution-engine.md #12.2/#12.3."""
from __future__ import annotations

import pytest

from app.engine.dag import DAG, GraphValidationError
from app.engine.registry import build_runtime_registry
from app.modules.workflows.schemas import GraphEdge, GraphNode, Position, WorkflowGraph


def node(node_id: str, node_type: str, x: float = 0) -> GraphNode:
    return GraphNode(id=node_id, type=node_type, position=Position(x=x, y=0))


def edge(
    edge_id: str, source: str, target: str, source_handle: str | None = None
) -> GraphEdge:
    return GraphEdge(
        id=edge_id, source=source, target=target, source_handle=source_handle
    )


@pytest.fixture(scope="module")
def registry():  # type: ignore[no-untyped-def]
    return build_runtime_registry()


def test_builds_a_valid_linear_graph(registry) -> None:  # type: ignore[no-untyped-def]
    graph = WorkflowGraph(
        nodes=[node("t", "neuroflow.manualTrigger"), node("s", "neuroflow.set", 200)],
        edges=[edge("e1", "t", "s")],
    )
    dag = DAG.from_graph(graph, registry)
    assert dag.trigger_node_ids() == ["t"]
    assert dag.nodes_by_id["s"].incoming[0].source == "t"


def test_rejects_duplicate_node_ids(registry) -> None:  # type: ignore[no-untyped-def]
    graph = WorkflowGraph(
        nodes=[node("t", "neuroflow.manualTrigger"), node("t", "neuroflow.set")],
        edges=[],
    )
    with pytest.raises(GraphValidationError, match="Duplicate node ids"):
        DAG.from_graph(graph, registry)


def test_rejects_unknown_node_type(registry) -> None:  # type: ignore[no-untyped-def]
    graph = WorkflowGraph(nodes=[node("t", "neuroflow.doesNotExist")], edges=[])
    with pytest.raises(GraphValidationError, match="Unknown node type"):
        DAG.from_graph(graph, registry)


def test_rejects_edge_to_unknown_node(registry) -> None:  # type: ignore[no-untyped-def]
    graph = WorkflowGraph(
        nodes=[node("t", "neuroflow.manualTrigger")],
        edges=[edge("e1", "t", "ghost")],
    )
    with pytest.raises(GraphValidationError, match="unknown node"):
        DAG.from_graph(graph, registry)


def test_rejects_a_cycle(registry) -> None:  # type: ignore[no-untyped-def]
    graph = WorkflowGraph(
        nodes=[node("a", "neuroflow.noOp"), node("b", "neuroflow.noOp", 200)],
        edges=[edge("e1", "a", "b"), edge("e2", "b", "a")],
    )
    with pytest.raises(GraphValidationError, match="cycle"):
        DAG.from_graph(graph, registry)


def test_branch_node_outputs_are_addressable_by_handle(registry) -> None:  # type: ignore[no-untyped-def]
    graph = WorkflowGraph(
        nodes=[
            node("t", "neuroflow.manualTrigger"),
            node("i", "neuroflow.if", 200),
            node("a", "neuroflow.noOp", 400),
            node("b", "neuroflow.noOp", 400),
        ],
        edges=[
            edge("e1", "t", "i"),
            edge("e2", "i", "a", source_handle="true"),
            edge("e3", "i", "b", source_handle="false"),
        ],
    )
    dag = DAG.from_graph(graph, registry)
    handles = {e.source_handle for e in dag.nodes_by_id["i"].outgoing}
    assert handles == {"true", "false"}
