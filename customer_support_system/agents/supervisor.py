"""
Supervisor review and human approval steps for the support workflow.
"""

import os
from anthropic import Anthropic
from state import CustomerSupportState

client = Anthropic()



def human_approval_node(state: CustomerSupportState) -> CustomerSupportState:
    """
    Ask a human supervisor to approve or reject a sensitive request.

    In production, this step would pause the graph and wait on a real approval
    channel. For the demo, it uses the terminal so the flow stays easy to run.
    """
    print("\n" + "="*60)
    print("  ⚠  HUMAN APPROVAL REQUIRED")
    print("="*60)
    print(f"  Reason       : {state.get('escalation_reason', 'High-risk request')}")
    print(f"  Customer ID  : {state['customer_id']}")
    print(f"  Customer Name: {state.get('customer_name', 'Unknown')}")
    print(f"  Query        : {state['query']}")
    print(f"\n  Proposed response:\n  {state.get('draft_response', 'N/A')}")
    print("="*60)

    while True:
        decision = input("\n  [SUPERVISOR] Approve this request? (yes/no): ").strip().lower()
        if decision in ("yes", "y"):
            print("  ✓ Request APPROVED by supervisor.")
            return {**state, "approval_status": "approved"}
        elif decision in ("no", "n"):
            reason = input("  [SUPERVISOR] Reason for rejection (optional): ").strip()
            print("  ✗ Request REJECTED by supervisor.")
            rejected_response = (
                f"Thank you for contacting ABC Technologies. After review, your "
                f"{state.get('escalation_reason', 'request').lower()} could not be approved at this time. "
            )
            if reason:
                rejected_response += f"Reason: {reason}. "
            rejected_response += "Please contact us for further assistance."
            return {
                **state,
                "approval_status": "rejected",
                "draft_response": rejected_response,
            }
        else:
            print("  Please enter 'yes' or 'no'.")


def route_after_intent(state: CustomerSupportState) -> str:
    """
    Choose the next step after a department agent drafts its answer.

    High-risk requests move to the approval gate. Everything else goes straight
    to supervisor review.
    """
    if state.get("requires_approval") and state.get("approval_status") == "pending":
        print("\n[ROUTER] High-risk request → human_approval_node")
        return "human_approval"
    print("\n[ROUTER] Standard request → supervisor_agent")
    return "supervisor"




def supervisor_agent(state: CustomerSupportState) -> CustomerSupportState:
    """
    Review the department agent's draft before it reaches the customer.

    The supervisor pass keeps the answer accurate, clear, policy-aware, and
    appropriately empathetic.
    """
    print("\n[NODE] Supervisor Agent — reviewing draft response")

    draft = state.get("draft_response", "")
    query = state["query"]
    intent = state.get("intent", "General")
    rag_context = state.get("rag_context", "No context available")
    approval_status = state.get("approval_status", "not_required")

    if approval_status == "rejected":
        print("  → Request was rejected. Passing rejection response to customer.")
        return {**state, "final_response": draft}

    prompt = f"""You are a senior customer support supervisor at ABC Technologies.
Review the following draft response from a {intent} support agent and improve it if needed.

CUSTOMER QUERY: "{query}"

AGENT DRAFT RESPONSE:
{draft}

KNOWLEDGE BASE CONTEXT USED:
{rag_context[:800] if rag_context else 'None'}

Your job:
1. Verify the response is accurate and complete.
2. Ensure the tone is professional, empathetic, and helpful.
3. Check that the response aligns with company policies.
4. Add any missing important information.
5. Keep the response concise (max 200 words).

If the draft is already good, return it with minimal changes.
Return ONLY the final customer-facing response. No meta-commentary."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )

    final = response.content[0].text.strip()
    print(f"  → Final response validated ({len(final)} chars)")

    return {**state, "final_response": final}
