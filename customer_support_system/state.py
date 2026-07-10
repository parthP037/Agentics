"""
Shared state for the customer support graph.

Every node receives and returns this shape, so keeping the fields explicit makes
the workflow easier to follow and safer to extend.
"""

from typing import TypedDict, Optional, List, Literal


class CustomerSupportState(TypedDict):
    """
    Data carried through one customer support run.

    Fields:
        customer_id: Stable customer ID used for memory lookups.
        customer_name: Customer name when we know it.
        query: Raw support message from the customer.
        intent: Classified intent for routing.
        department: Department chosen from the intent.
        rag_context: Knowledge base text used by the agent.
        conversation_history: Recent SQLite-backed messages for this customer.
        requires_approval: Whether the request needs human review.
        approval_status: Current review status for high-risk requests.
        draft_response: First answer produced by the department agent.
        final_response: Customer-facing answer after supervisor review.
        messages: Reserved message list for LangChain/LangGraph integrations.
        escalation_reason: Why this request was sent for human approval.
    """
    customer_id: str
    customer_name: Optional[str]
    query: str
    intent: Optional[Literal["Sales", "Technical", "Billing", "Account", "Memory"]]
    department: Optional[str]
    rag_context: Optional[str]
    conversation_history: List[dict]
    requires_approval: bool
    approval_status: Optional[Literal["pending", "approved", "rejected"]]
    draft_response: Optional[str]
    final_response: Optional[str]
    messages: List[dict]
    escalation_reason: Optional[str]
