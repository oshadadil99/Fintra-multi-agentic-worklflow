"""The agent registry - Fintra's extension point.

Each AgentSpec fully describes one domain specialist: its route name, the
Pinecone namespace it retrieves from, a routing description the orchestrator
uses to classify queries, and its persona. Adding a new banking domain is
one entry here plus one folder under data/ - no graph changes required.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentSpec:
    name: str
    namespace: str
    routing_description: str
    persona: str


AGENTS: dict[str, AgentSpec] = {
    "general": AgentSpec(
        name="general_agent",
        namespace="general-faq",
        routing_description=(
            "General information about Morgan Treasuries: company background, "
            "ownership, board of directors, branch locations, SWIFT codes, "
            "opening hours, contact details, and the overall list of products "
            "and services offered."
        ),
        persona=(
            "You are the general-information specialist for Morgan Treasuries, "
            "answering questions about the company, its leadership, branches, "
            "and its products and services."
        ),
    ),
    "loan": AgentSpec(
        name="loan_agent",
        namespace="loan-details",
        routing_description=(
            "Loans AND leasing: vehicle leasing (cars, vans, SUVs, three "
            "wheelers, two wheelers), Easy Leasing, vehicle/auto loans, gold "
            "loans (Ran Shakthi), mobile and laptop loans, repayment terms, "
            "leasing rates, and loan eligibility."
        ),
        persona=(
            "You are the loans and leasing specialist for Morgan Treasuries, "
            "answering questions about vehicle leasing, vehicle loans, gold "
            "loans, and their features, terms, and eligibility."
        ),
    ),
    "saving": AgentSpec(
        name="saving_agent",
        namespace="saving-details",
        routing_description=(
            "Savings and deposits: fixed deposits (Vishwasa FD), FD rates and "
            "terms, savings accounts (Vishishta, Shreyshta senior citizens, "
            "Flexy Fix money market, Pravishta children's), interest rates, "
            "and minimum opening balances."
        ),
        persona=(
            "You are the savings and deposits specialist for Morgan "
            "Treasuries, answering questions about fixed deposits, savings "
            "accounts, interest rates, and account benefits."
        ),
    ),
}

FALLBACK_ROUTE = "fallback"
ROUTES = (*AGENTS.keys(), FALLBACK_ROUTE)
