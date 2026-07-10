"""
agents/human_approval.py
Human-in-the-loop approval process for high-risk requests.
Simulates supervisor review with a console prompt.
"""

APPROVAL_REQUIRED_TYPES = {
    "Refund Request",
    "Subscription Cancellation",
    "Account Closure",
    "Compensation Request",
    "Escalation to Management",
}


def requires_approval(risk_type: str | None) -> bool:
    return risk_type in APPROVAL_REQUIRED_TYPES


def request_human_approval(state: dict, auto_mode: bool = False, auto_decision: str = "approve") -> dict:
    """
    Prompt a human supervisor for approval of a high-risk request.

    Parameters
    ----------
    state       : current workflow state
    auto_mode   : if True, skip interactive prompt (used for demonstration)
    auto_decision : 'approve' or 'reject' when auto_mode is True
    """
    risk_type = state.get("high_risk_type", "Unknown")
    customer_name = state.get("customer_name", "Unknown Customer")
    query = state.get("query", "")

    print("\n" + "="*60)
    print("  ⚠️   HUMAN SUPERVISOR APPROVAL REQUIRED")
    print("="*60)
    print(f"  Customer   : {customer_name}")
    print(f"  Request    : {risk_type}")
    print(f"  Query      : {query}")
    print("="*60)

    if auto_mode:
        decision = auto_decision.lower().strip()
        print(f"  [AUTO MODE] Decision: {decision.upper()}")
    else:
        decision = input("  Approve or reject this request? (approve/reject): ").lower().strip()

    print("="*60 + "\n")

    approved = decision == "approve"

    if approved:
        approval_note = (
            f"✅ Your {risk_type} has been approved by our supervisor. "
            "Our team will process this within 5–7 business days."
        )
    else:
        approval_note = (
            f"❌ Your {risk_type} has been reviewed and unfortunately could not be approved "
            "at this time. Please contact our support team for further assistance."
        )

    return {
        **state,
        "human_approved": approved,
        "approval_note": approval_note,
    }
