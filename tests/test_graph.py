"""Graph behaviour with every external dependency mocked - no network, no cost."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import fintra.graph.nodes as nodes
from fintra.graph.builder import build_graph
from fintra.graph.nodes import RouteDecision, fallback, orchestrator
from fintra.prompts import FALLBACK_MESSAGE


def _fake_router(route: str):
    llm = MagicMock()
    llm.with_structured_output.return_value.invoke.return_value = RouteDecision(route=route)
    return lambda: llm


@pytest.mark.parametrize("route", ["general", "loan", "saving", "fallback"])
def test_orchestrator_returns_known_routes(monkeypatch, route):
    monkeypatch.setattr(nodes, "orchestrator_llm", _fake_router(route))
    assert orchestrator({"query": "q", "history": []})["route"] == route


def test_orchestrator_degrades_unknown_route_to_fallback(monkeypatch):
    monkeypatch.setattr(nodes, "orchestrator_llm", _fake_router("weather_agent"))
    assert orchestrator({"query": "q", "history": []})["route"] == "fallback"


def test_fallback_is_deterministic_and_free():
    result = fallback({"query": "anything"})
    assert result["answer"] == FALLBACK_MESSAGE
    assert result["sources"] == []


def test_graph_runs_end_to_end_with_mocks(monkeypatch):
    monkeypatch.setattr(nodes, "orchestrator_llm", _fake_router("saving"))

    doc = SimpleNamespace(
        page_content="FD terms: 1 to 48 months.",
        metadata={"source": "saving-details/saving-details.md", "chunk": 0},
    )
    retriever = MagicMock()
    retriever.invoke.return_value = [doc]
    monkeypatch.setattr(nodes, "get_retriever", lambda ns: retriever)

    agent = MagicMock()
    agent.invoke.return_value = SimpleNamespace(content="Terms range from 1 to 48 months.")
    monkeypatch.setattr(nodes, "agent_llm", lambda: agent)

    result = build_graph().invoke(
        {"session_id": "t", "query": "FD terms?", "history": []}
    )
    assert result["route"] == "saving"
    assert result["answer"] == "Terms range from 1 to 48 months."
    assert result["sources"] == ["saving-details/saving-details.md"]


def test_history_reaches_the_agent_prompt(monkeypatch):
    """The coreference mechanism: prior turns must be in the LLM prompt."""
    monkeypatch.setattr(nodes, "orchestrator_llm", _fake_router("general"))
    retriever = MagicMock()
    retriever.invoke.return_value = []
    monkeypatch.setattr(nodes, "get_retriever", lambda ns: retriever)

    agent = MagicMock()
    agent.invoke.return_value = SimpleNamespace(content="Yes, at JKH.")
    monkeypatch.setattr(nodes, "agent_llm", lambda: agent)

    history = [
        {"role": "user", "content": "Who is the chairman?"},
        {"role": "assistant", "content": "Mr. Ajit Gunewardene."},
    ]
    build_graph().invoke(
        {"session_id": "t", "query": "did he work in John Keells?", "history": history}
    )
    sent = agent.invoke.call_args.args[0]
    human_text = sent[-1].content
    assert "Ajit Gunewardene" in human_text
    assert "did he work in John Keells?" in human_text
