"""Assemble the hub-and-spoke graph from the agent registry."""

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from fintra.agents.registry import AGENTS, FALLBACK_ROUTE
from fintra.graph.nodes import fallback, make_rag_node, orchestrator
from fintra.graph.state import GraphState


@lru_cache
def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("orchestrator", orchestrator)
    for route, spec in AGENTS.items():
        graph.add_node(route, make_rag_node(spec))
    graph.add_node(FALLBACK_ROUTE, fallback)

    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges(
        "orchestrator",
        lambda state: state["route"],
        {route: route for route in (*AGENTS, FALLBACK_ROUTE)},
    )
    for route in (*AGENTS, FALLBACK_ROUTE):
        graph.add_edge(route, END)

    return graph.compile()
