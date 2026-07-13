"""The registry is the platform's contract - guard its invariants."""

from fintra.agents.registry import AGENTS, FALLBACK_ROUTE, ROUTES


def test_expected_routes_exist():
    assert set(AGENTS) == {"general", "loan", "saving"}
    assert FALLBACK_ROUTE in ROUTES


def test_namespaces_are_unique():
    namespaces = [spec.namespace for spec in AGENTS.values()]
    assert len(namespaces) == len(set(namespaces))


def test_every_spec_is_complete():
    for route, spec in AGENTS.items():
        assert spec.name, route
        assert spec.namespace, route
        assert len(spec.routing_description) > 40, f"{route}: routing description too thin"
        assert spec.persona, route


def test_loan_agent_covers_leasing():
    # locked scope decision: loan_agent answers loans AND leasing
    assert "leasing" in AGENTS["loan"].routing_description.lower()
