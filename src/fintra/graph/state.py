"""Shared state flowing through the graph."""

from typing import TypedDict


class GraphState(TypedDict, total=False):
    session_id: str
    query: str
    history: list[dict]  # [{"role": "user"|"assistant", "content": str}, ...]
    route: str
    sources: list[str]
    answer: str
