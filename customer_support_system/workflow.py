"""
workflow.py
LangGraph workflow for ABC Technologies Customer Support Automation System.

Graph structure (Task 1):
  load_memory → classify_intent → [route by dept] → dept_agent
                                                  ↘ memory_agent
                               ↓ (if high-risk)
                          human_approval
                               ↓
                          supervisor → save_memory → END
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from typing import TypedDict, Optional
from langgraph_lite import StateGraph, END

from memory.sqlite_memory import load_history, save_message
from agents.department_agents import (
    classify_intent, detect_high_risk, is_memory_query,
    sales_agent, technical_agent, billing_agent, account_agent,
    general_agent, memory_agent, supervisor_agent,
)
from agents.human_approval import requires_approval, request_human_approval


# ─────────────────────────────────────────────
# STATE SCHEMA  (Task 2)
# ─────────────────────────────────────────────

class SupportState(TypedDict):
    customer_id:     str
    customer_name:   str
    query:           str
    department:      Optional[str]
    memory_history:  list
    rag_context:     Optional[str]
    high_risk_type:  Optional[str]
    human_approved:  Optional[bool]
    approval_note:   Optional[str]
    response:        Optional[str]
    final_response:  Optional[str]


# ─────────────────────────────────────────────
# NODE FUNCTIONS
# ─────────────────────────────────────────────

def node_load_memory(state):
    customer_id = state["customer_id"]
    history = load_history(customer_id)
    print(f"\n[NODE] Loading memory for customer: {customer_id}")
    print(f"  → Found {len(history)} past messages.")
    return {**state, "memory_history": history}


def node_classify_intent(state):
    query = state["query"]
    print(f"\n[NODE] Intent Classification")

    if is_memory_query(query):
        dept = "Memory"
    else:
        dept = classify_intent(query)

    high_risk = detect_high_risk(query)
    print(f"  → Department  : {dept}")
    if high_risk:
        print(f"  → ⚠️  High-risk : {high_risk}")
    return {**state, "department": dept, "high_risk_type": high_risk}


def node_sales(state):
    print(f"\n[NODE] Sales Agent")
    return sales_agent(state)

def node_technical(state):
    print(f"\n[NODE] Technical Support Agent")
    return technical_agent(state)

def node_billing(state):
    print(f"\n[NODE] Billing Agent")
    return billing_agent(state)

def node_account(state):
    print(f"\n[NODE] Account Agent")
    return account_agent(state)

def node_general(state):
    print(f"\n[NODE] General Support Agent")
    return general_agent(state)

def node_memory(state):
    print(f"\n[NODE] Memory Recall Agent")
    return memory_agent(state)


_AUTO_MODE     = True
_AUTO_DECISION = "approve"

def node_human_approval(state):
    print(f"\n[NODE] Human Approval")
    return request_human_approval(state, auto_mode=_AUTO_MODE, auto_decision=_AUTO_DECISION)


def node_supervisor(state):
    print(f"\n[NODE] Supervisor Agent — validating response")
    result = supervisor_agent(state)
    if result.get("approval_note"):
        result["final_response"] = result["approval_note"] + "\n\n" + result.get("final_response", "")
    return result


def node_save_memory(state):
    print(f"\n[NODE] Saving to memory")
    save_message(state["customer_id"], "user",      state["query"],                      state.get("department"))
    save_message(state["customer_id"], "assistant", state.get("final_response", ""),     state.get("department"))
    return state


# ─────────────────────────────────────────────
# ROUTING LOGIC  (Task 4)
# ─────────────────────────────────────────────

def route_by_department(state):
    dept      = state.get("department", "General")
    high_risk = state.get("high_risk_type")

    if dept == "Memory":
        return "memory"

    # Billing-related high-risk requests always go to Billing agent
    if high_risk in ("Refund Request", "Subscription Cancellation"):
        return "billing"

    mapping = {"Sales": "sales", "Technical": "technical",
               "Billing": "billing", "Account": "account"}
    return mapping.get(dept, "general")


def route_after_dept(state):
    if state.get("high_risk_type") and requires_approval(state.get("high_risk_type")):
        return "human_approval"
    return "supervisor"


# ─────────────────────────────────────────────
# BUILD THE GRAPH  (Task 1)
# ─────────────────────────────────────────────

def build_graph(auto_approval_mode=True, auto_decision="approve"):
    global _AUTO_MODE, _AUTO_DECISION
    _AUTO_MODE     = auto_approval_mode
    _AUTO_DECISION = auto_decision

    graph = StateGraph(SupportState)

    graph.add_node("load_memory",     node_load_memory)
    graph.add_node("classify_intent", node_classify_intent)
    graph.add_node("sales",           node_sales)
    graph.add_node("technical",       node_technical)
    graph.add_node("billing",         node_billing)
    graph.add_node("account",         node_account)
    graph.add_node("general",         node_general)
    graph.add_node("memory",          node_memory)
    graph.add_node("human_approval",  node_human_approval)
    graph.add_node("supervisor",      node_supervisor)
    graph.add_node("save_memory",     node_save_memory)

    graph.set_entry_point("load_memory")
    graph.add_edge("load_memory", "classify_intent")

    graph.add_conditional_edges(
        "classify_intent", route_by_department,
        {"sales": "sales", "technical": "technical",
         "billing": "billing", "account": "account",
         "general": "general", "memory": "memory"}
    )

    for dept_node in ("sales", "technical", "billing", "account", "general"):
        graph.add_conditional_edges(
            dept_node, route_after_dept,
            {"human_approval": "human_approval", "supervisor": "supervisor"}
        )

    graph.add_edge("memory",         "supervisor")
    graph.add_edge("human_approval", "supervisor")
    graph.add_edge("supervisor",     "save_memory")
    graph.add_edge("save_memory",    END)

    return graph.compile()
