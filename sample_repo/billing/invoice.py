"""
Billing invoice module.

IMPORTANT: This module assumes User.email is ALWAYS present (non-null).
There is intentionally NO null-check on user.email.
This creates a real risk when User.email becomes nullable.
"""
from sample_repo.shared.user import User


def build_invoice(user: User, amount: float, invoice_id: str) -> dict:
    """Build an invoice payload for the given user."""
    return {
        "invoice_id": invoice_id,
        "user_id": user.id,
        "recipient_email": user.email,  # assumes email always exists
        "amount": amount,
        "currency": "USD",
    }


def send_invoice(user: User, amount: float, invoice_id: str) -> bool:
    """
    Send an invoice email to the user.

    WARNING: This function assumes user.email is always a valid string.
    If user.email becomes None this will raise an AttributeError or send
    a malformed email, causing silent data corruption in the invoice flow.
    """
    invoice = build_invoice(user, amount, invoice_id)

    # Directly use email — no null check, no fallback
    recipient = user.email.strip().lower()  # will raise AttributeError if email is None

    print(f"[billing] Sending invoice {invoice_id} to {recipient} — amount: ${amount}")
    # Simulate email dispatch (real implementation calls SMTP/SES here)
    return True


def retry_failed_invoice(user: User, invoice_id: str) -> bool:
    """
    Retry a previously failed invoice delivery.
    Batuhan is actively working on this function.
    Still assumes email is always available — no recovery path for missing email.
    """
    print(f"[billing] Retrying invoice {invoice_id} for user {user.id} at {user.email}")
    return send_invoice(user, 0.0, invoice_id)
