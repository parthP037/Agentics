"""
Intent routing and the department-specific support agents.
"""

import os
import re
from anthropic import Anthropic

from state import CustomerSupportState
from rag.retriever import retrieve_context_by_intent
from memory.sqlite_memory import (
    get_conversation_history,
    get_customer_name,
    save_interaction,
    format_history_for_prompt,
)

client = Anthropic()


def classify_intent(state: CustomerSupportState) -> CustomerSupportState:
    """
    Work out which support lane should handle the customer's message.

    The classifier returns one of the five intents the graph knows how to route:
    Sales, Technical, Billing, Account, or Memory.
    """
    print("\n[NODE] Intent Classification")

    query = state["query"]
    history = format_history_for_prompt(state.get("conversation_history", []))

    prompt = f"""You are an intent classifier for a customer support system at ABC Technologies.

Classify the following customer query into EXACTLY ONE of these categories:
- Sales      : product information, subscription plans, pricing, upgrades, trials
- Technical  : application errors, crashes, installation, login problems, configuration
- Billing    : invoices, payment issues, refund requests, subscription charges
- Account    : password reset, profile updates, account activation or deactivation
- Memory     : asking about previous interactions, past issues, conversation history

Previous conversation history:
{history}

Customer query: "{query}"

Respond with ONLY the category name (Sales, Technical, Billing, Account, or Memory). Nothing else."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=20,
        messages=[{"role": "user", "content": prompt}]
    )

    intent_raw = response.content[0].text.strip()
    for valid in ["Sales", "Technical", "Billing", "Account", "Memory"]:
        if valid.lower() in intent_raw.lower():
            intent = valid
            break
    else:
        intent = "Sales"

    print(f"  → Intent classified as: {intent}")

    name_match = re.search(r"my name is (\w+)", query, re.IGNORECASE)
    customer_name = name_match.group(1) if name_match else state.get("customer_name") or get_customer_name(state["customer_id"])

    return {
        **state,
        "intent": intent,
        "department": intent if intent != "Memory" else None,
        "customer_name": customer_name,
    }



def route_query(state: CustomerSupportState) -> str:
    """
    Send the query to the agent that matches the classified intent.

    Returns the name of the next node to execute.
    """
    intent = state.get("intent", "Sales")
    routing_map = {
        "Sales":     "sales_agent",
        "Technical": "technical_agent",
        "Billing":   "billing_agent",
        "Account":   "account_agent",
        "Memory":    "memory_agent",
    }
    next_node = routing_map.get(intent, "sales_agent")
    print(f"\n[ROUTER] Routing '{intent}' → {next_node}")
    return next_node



def _build_agent_prompt(department: str, query: str, rag_context: str,
                        history: str, customer_name: str) -> str:
    """Build the shared prompt used by the department agents."""
    name_str = f"The customer's name is {customer_name}. " if customer_name else ""
    return f"""You are a helpful {department} support agent at ABC Technologies.
{name_str}Use the knowledge base context below to answer the customer's query accurately and professionally.
If the context does not cover the query fully, use your best knowledge but stay truthful.

KNOWLEDGE BASE CONTEXT:
{rag_context}

CONVERSATION HISTORY:
{history}

Customer query: "{query}"

Provide a clear, concise, and helpful response. Be empathetic and professional."""


def sales_agent(state: CustomerSupportState) -> CustomerSupportState:
    """Handle pricing, plans, trials, upgrades, and general product questions."""
    print("\n[NODE] Sales Agent")

    query = state["query"]
    history = format_history_for_prompt(state.get("conversation_history", []))
    rag_context = retrieve_context_by_intent(query, "Sales")

    prompt = _build_agent_prompt("Sales", query, rag_context, history, state.get("customer_name"))

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    draft = response.content[0].text.strip()
    print(f"  → Draft response generated ({len(draft)} chars)")

    return {**state, "rag_context": rag_context, "draft_response": draft, "requires_approval": False}


def technical_agent(state: CustomerSupportState) -> CustomerSupportState:
    """Handle product errors, crashes, setup issues, and login problems."""
    print("\n[NODE] Technical Support Agent")

    query = state["query"]
    history = format_history_for_prompt(state.get("conversation_history", []))
    rag_context = retrieve_context_by_intent(query, "Technical")

    prompt = _build_agent_prompt("Technical Support", query, rag_context, history, state.get("customer_name"))

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    draft = response.content[0].text.strip()
    print(f"  → Draft response generated ({len(draft)} chars)")

    return {**state, "rag_context": rag_context, "draft_response": draft, "requires_approval": False}


def billing_agent(state: CustomerSupportState) -> CustomerSupportState:
    """
    Handle invoices, payment issues, subscription charges, and refunds.

    Refunds, cancellations, account closures, and compensation requests are
    flagged for a supervisor before the customer gets a final answer.
    """
    print("\n[NODE] Billing Agent")

    query = state["query"]
    history = format_history_for_prompt(state.get("conversation_history", []))
    rag_context = retrieve_context_by_intent(query, "Billing")

    high_risk_patterns = [
        (r'\brefund\b', "Refund request"),
        (r'\bcancel\b.*subscription|subscription.*\bcancel\b', "Subscription cancellation"),
        (r'\bclose\b.*account|account.*\bclose\b', "Account closure request"),
        (r'\bcompensation\b|\bcompensate\b', "Compensation request"),
    ]
    requires_approval = False
    escalation_reason = None
    for pattern, reason in high_risk_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            requires_approval = True
            escalation_reason = reason
            break

    if requires_approval:
        print(f"  ⚠ HIGH-RISK detected: {escalation_reason} — flagging for human approval")
        draft = (
            f"Thank you for reaching out about your {escalation_reason.lower()}. "
            f"I have logged your request and it is currently being reviewed by our billing supervisor. "
            f"You will receive a confirmation within 24 hours. "
            f"Your request reference number will be provided once approved."
        )
    else:
        prompt = _build_agent_prompt("Billing", query, rag_context, history, state.get("customer_name"))
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        draft = response.content[0].text.strip()

    print(f"  → Draft response generated. Requires approval: {requires_approval}")

    return {
        **state,
        "rag_context": rag_context,
        "draft_response": draft,
        "requires_approval": requires_approval,
        "approval_status": "pending" if requires_approval else None,
        "escalation_reason": escalation_reason,
    }


def account_agent(state: CustomerSupportState) -> CustomerSupportState:
    """
    Handle password resets, profile changes, and account access questions.

    Account closure requests are held for supervisor approval because they are
    permanent and should not be handled automatically.
    """
    print("\n[NODE] Account Agent")

    query = state["query"]
    history = format_history_for_prompt(state.get("conversation_history", []))
    rag_context = retrieve_context_by_intent(query, "Account")

    requires_approval = bool(re.search(r'\bclose\b.*account|account.*\bclose\b|delete.*account', query, re.IGNORECASE))
    escalation_reason = "Account closure request" if requires_approval else None

    if requires_approval:
        print(f"  ⚠ HIGH-RISK detected: {escalation_reason}")
        draft = (
            "Your account closure request has been received and flagged for supervisor review. "
            "Please note that account closure is permanent. A supervisor will contact you within 24 hours "
            "to confirm your identity and complete the process."
        )
    else:
        prompt = _build_agent_prompt("Account Support", query, rag_context, history, state.get("customer_name"))
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        draft = response.content[0].text.strip()

    print(f"  → Draft response generated. Requires approval: {requires_approval}")

    return {
        **state,
        "rag_context": rag_context,
        "draft_response": draft,
        "requires_approval": requires_approval,
        "approval_status": "pending" if requires_approval else None,
        "escalation_reason": escalation_reason,
    }


def memory_agent(state: CustomerSupportState) -> CustomerSupportState:
    """
    Answer questions about the customer's previous support conversations.

    This uses the conversation history already loaded from SQLite and does not
    route to a department-specific knowledge base.
    """
    print("\n[NODE] Memory Agent")

    customer_id = state["customer_id"]
    query = state["query"]
    history = state.get("conversation_history", [])
    history_str = format_history_for_prompt(history)

    if not history:
        draft = (
            "I don't have any previous conversation history for your account. "
            "This may be your first time contacting us, or your history may have been cleared. "
            "How can I assist you today?"
        )
    else:
        prompt = f"""You are a customer support assistant at ABC Technologies.
The customer is asking about their previous support interactions.

Customer's full conversation history:
{history_str}

Customer query: "{query}"

Summarise what the customer's previous issues were based on the history above.
Be specific and helpful."""

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        draft = response.content[0].text.strip()

    print(f"  → Memory recall response generated ({len(draft)} chars)")

    return {**state, "draft_response": draft, "requires_approval": False, "rag_context": None}
