"""
Entry point for the customer support workflow.

This module wires together the LangGraph nodes, loads customer memory, runs
the right support agent, and saves the final interaction back to SQLite.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from langgraph.graph import StateGraph, END

from state import CustomerSupportState
from memory.sqlite_memory import (
    get_conversation_history,
    save_interaction,
    get_customer_name,
)
from agents.department_agents import (
    classify_intent,
    route_query,
    sales_agent,
    technical_agent,
    billing_agent,
    account_agent,
    memory_agent,
)
from agents.supervisor import (
    supervisor_agent,
    human_approval_node,
    route_after_intent,
)



def load_memory_node(state: CustomerSupportState) -> CustomerSupportState:
    """
    Pull the customer's recent conversation history before the query is routed.

    If we already know the customer's name, keep it. Otherwise, use the latest
    name saved in memory for this customer ID.
    """
    print("\n[NODE] Loading memory for customer:", state["customer_id"])
    history = get_conversation_history(state["customer_id"])
    stored_name = get_customer_name(state["customer_id"])
    print(f"  → Found {len(history)} past messages.")
    return {
        **state,
        "conversation_history": history,
        "customer_name": state.get("customer_name") or stored_name,
    }


def save_memory_node(state: CustomerSupportState) -> CustomerSupportState:
    """
    Save this turn of the conversation.

    The user message is always stored, and the assistant response is saved when
    the workflow has produced one.
    """
    print("\n[NODE] Saving interaction to memory")
    customer_id = state["customer_id"]
    customer_name = state.get("customer_name")

    save_interaction(
        customer_id=customer_id,
        role="user",
        message=state["query"],
        intent=state.get("intent"),
        customer_name=customer_name,
    )
    final_resp = state.get("final_response") or state.get("draft_response", "")
    if final_resp:
        save_interaction(
            customer_id=customer_id,
            role="assistant",
            message=final_resp,
            intent=state.get("intent"),
            customer_name=customer_name,
        )
    print("  → Interaction saved.")
    return state




def build_workflow() -> StateGraph:
    """
    Build the LangGraph app used by the demo and by direct query runs.

    The graph loads memory first, routes the query by intent, optionally asks
    for approval, reviews the answer, and then writes the turn back to memory.
    """
    builder = StateGraph(CustomerSupportState)

    builder.add_node("load_memory",       load_memory_node)
    builder.add_node("classify_intent",   classify_intent)

    builder.add_node("sales_agent",       sales_agent)
    builder.add_node("technical_agent",   technical_agent)
    builder.add_node("billing_agent",     billing_agent)
    builder.add_node("account_agent",     account_agent)
    builder.add_node("memory_agent",      memory_agent)

    builder.add_node("human_approval",    human_approval_node)

    builder.add_node("supervisor_agent",  supervisor_agent)

    builder.add_node("save_memory",       save_memory_node)


    builder.set_entry_point("load_memory")
    builder.add_edge("load_memory", "classify_intent")

    
    builder.add_conditional_edges(
        "classify_intent",
        route_query,
        {
            "sales_agent":     "sales_agent",
            "technical_agent": "technical_agent",
            "billing_agent":   "billing_agent",
            "account_agent":   "account_agent",
            "memory_agent":    "memory_agent",
        }
    )

    for agent_node in ["sales_agent", "technical_agent", "billing_agent", "account_agent", "memory_agent"]:
        builder.add_conditional_edges(
            agent_node,
            route_after_intent,
            {
                "human_approval": "human_approval",
                "supervisor":     "supervisor_agent",
            }
        )

    builder.add_edge("human_approval", "supervisor_agent")

    builder.add_edge("supervisor_agent", "save_memory")
    builder.add_edge("save_memory", END)

    return builder.compile()


def run_query(customer_id: str, query: str, customer_name: str = None) -> dict:
    """
    Run one customer question through the support workflow.

    Args:
        customer_id: Stable ID used to look up prior conversations.
        query: The customer's message.
        customer_name: Optional name to attach to the conversation.

    Returns:
        The final workflow state, including the intent, department, and reply.
    """
    app = build_workflow()

    initial_state: CustomerSupportState = {
        "customer_id":           customer_id,
        "customer_name":         customer_name,
        "query":                 query,
        "intent":                None,
        "department":            None,
        "rag_context":           None,
        "conversation_history":  [],
        "requires_approval":     False,
        "approval_status":       None,
        "draft_response":        None,
        "final_response":        None,
        "messages":              [],
        "escalation_reason":     None,
    }

    result = app.invoke(initial_state)
    return result



if __name__ == "__main__":
    print("\n" + "="*70)
    print("  ABC Technologies — AI Customer Support Automation System")
    print("  Built with LangGraph | Task 10: Demonstration")
    print("="*70)

    from memory.sqlite_memory import clear_customer_history
    for cid in ["CUST_001", "CUST_002", "CUST_003", "CUST_004", "CUST_005"]:
        clear_customer_history(cid)

    demo_queries = [
        {
            "id":    "CUST_001",
            "name":  "Alice",
            "query": "What are the pricing plans available for your software?",
            "desc":  "Query 1 — Expected: Sales"
        },
        {
            "id":    "CUST_002",
            "name":  "Bob",
            "query": "I forgot my account password.",
            "desc":  "Query 2 — Expected: Account"
        },
        {
            "id":    "CUST_003",
            "name":  "Charlie",
            "query": "My application crashes whenever I upload a file.",
            "desc":  "Query 3 — Expected: Technical Support"
        },
        {
            "id":    "CUST_004",
            "name":  "David",
            "query": "I need a refund for my annual subscription.",
            "desc":  "Query 4 — Expected: Billing + Human Approval"
        },
        {
            "id":    "CUST_004",   
            "name":  "David",
            "query": "What was my previous support issue?",
            "desc":  "Query 5 — Expected: Memory recall (same customer as Q4)"
        },
    ]

    results = []
    for i, q in enumerate(demo_queries, 1):
        print(f"\n{'─'*70}")
        print(f"  {q['desc']}")
        print(f"  Customer: {q['name']} ({q['id']})")
        print(f"  Query   : {q['query']}")
        print(f"{'─'*70}")

        result = run_query(q["id"], q["query"], q["name"])

        print(f"\n  INTENT    : {result.get('intent')}")
        print(f"  DEPT      : {result.get('department')}")
        print(f"  APPROVAL  : {result.get('approval_status', 'N/A')}")
        print(f"\n  FINAL RESPONSE:\n")
        final = result.get("final_response") or result.get("draft_response", "No response generated.")
        for line in final.split("\n"):
            print(f"     {line}")

        results.append({
            "query_num": i,
            "customer": q["name"],
            "query": q["query"],
            "intent": result.get("intent"),
            "approval": result.get("approval_status", "N/A"),
            "response": final
        })

    print(f"\n{'='*70}")
    print("  Demonstration Complete — All 5 queries processed.")
    print("  SQLite memory stored in: memory.db")
    print("="*70)
