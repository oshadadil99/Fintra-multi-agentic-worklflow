"""Graph nodes: the orchestrator hub, the RAG-agent factory, and the fallback.

Hub-and-spoke: the orchestrator only classifies; the selected spoke produces
the final answer and the graph terminates. Spokes never call each other.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from fintra.agents.registry import AGENTS, FALLBACK_ROUTE, ROUTES, AgentSpec
from fintra.graph.state import GraphState
from fintra.llm import agent_llm, orchestrator_llm
from fintra.prompts import FALLBACK_MESSAGE, RAG_SYSTEM, ROUTER_SYSTEM
from fintra.retrieval.vectorstore import get_retriever


class RouteDecision(BaseModel):
    route: str = Field(description=f"One of: {', '.join(ROUTES)}")


def _format_history(history: list[dict]) -> str:
    if not history:
        return "(no previous messages)"
    return "\n".join(f"{m['role']}: {m['content']}" for m in history)


def orchestrator(state: GraphState) -> GraphState:
    prompt = [
        SystemMessage(content=ROUTER_SYSTEM),
        HumanMessage(
            content=(
                f"Conversation history:\n{_format_history(state.get('history', []))}\n\n"
                f"Customer's latest message:\n{state['query']}\n\n"
                "Respond with the route."
            )
        ),
    ]
    decision = orchestrator_llm().with_structured_output(RouteDecision).invoke(prompt)
    route = decision.route.strip().lower()
    # anything unexpected degrades safely to the fallback guardrail
    return {"route": route if route in AGENTS else FALLBACK_ROUTE}


def make_rag_node(spec: AgentSpec):
    def rag_node(state: GraphState) -> GraphState:
        docs = get_retriever(spec.namespace).invoke(state["query"])
        context = "\n\n---\n\n".join(d.page_content for d in docs) or "(no documents found)"
        prompt = [
            SystemMessage(content=RAG_SYSTEM.format(persona=spec.persona, context=context)),
            HumanMessage(
                content=(
                    f"Conversation history:\n{_format_history(state.get('history', []))}\n\n"
                    f"Customer's message:\n{state['query']}"
                )
            ),
        ]
        answer = agent_llm().invoke(prompt)
        sources = sorted({str(d.metadata.get("source", "unknown")) for d in docs})
        return {"answer": answer.content, "sources": sources}

    rag_node.__name__ = spec.name
    return rag_node


def fallback(state: GraphState) -> GraphState:
    # deliberate: no LLM call - deterministic, free, and injection-proof
    return {"answer": FALLBACK_MESSAGE, "sources": []}
