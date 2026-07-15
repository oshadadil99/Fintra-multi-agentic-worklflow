"""The single entrypoint every interface (CLI, FastAPI, WhatsApp) calls.

One conversation turn: load memory -> run the graph -> persist the turn.
"""

from fintra.config import get_settings
from fintra.graph.builder import build_graph
from fintra.memory import cache
from fintra.memory.history import append_turn, load_history


def answer_query(session_id: str, message: str) -> dict:
    history = load_history(session_id)
    result = build_graph().invoke(
        {"session_id": session_id, "query": message, "history": history}
    )
    append_turn(session_id, message, result["answer"])

    # write-through: keep the cache identical to what a fresh Supabase read
    # of the last N messages would return
    window = get_settings().memory_window
    updated = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": result["answer"]},
    ]
    cache.set_history(session_id, updated[-window:])

    return {
        "session_id": session_id,
        "route": result["route"],
        "answer": result["answer"],
        "sources": result.get("sources", []),
    }
