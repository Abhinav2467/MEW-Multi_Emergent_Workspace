"""LangGraph cold email agent: search → draft/send."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from backend.agents.cold_email.nodes import (
    ColdEmailState,
    create_or_send,
    generate_body,
    search_recruiters,
)


def build_cold_email_graph():
    graph = StateGraph(ColdEmailState)
    graph.add_node("search_recruiters", search_recruiters)
    graph.add_node("generate_body", generate_body)
    graph.add_node("create_or_send", create_or_send)
    graph.add_edge(START, "search_recruiters")
    graph.add_edge("search_recruiters", "generate_body")
    graph.add_edge("generate_body", "create_or_send")
    graph.add_edge("create_or_send", END)
    return graph.compile()


_GRAPH = None


def get_cold_email_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_cold_email_graph()
    return _GRAPH


def run_cold_email_flow(state: dict[str, Any]) -> dict[str, Any]:
    """Run the LangGraph cold email pipeline synchronously."""
    graph = get_cold_email_graph()
    return graph.invoke(state)
