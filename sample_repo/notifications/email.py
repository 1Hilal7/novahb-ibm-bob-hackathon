"""
Notifications email module.

This module already safely handles the case where user.email is None.
It was designed with fallback-first behavior from the start.
Ayşe is actively improving this fallback handling.
"""
from sample_repo.shared.user import User


def send_notification(user: User, subject: str, body: str) -> bool:
    """
    Send an email notification to the user.

    Safely handles the case where user.email is None —
    logs a warning and returns False instead of crashing.
    This means the module is safe even if User.email becomes nullable.
    """
    if user.email is None:
        print(f"[notifications] Skipping email for user {user.id}: no email address on file.")
        return False

    recipient = user.email.strip().lower()
    print(f"[notifications] Sending '{subject}' to {recipient}")
    # Simulate dispatch
    return True


def send_bulk_notifications(users: list[User], subject: str, body: str) -> dict:
    """
    Send notifications to a list of users.
    Collects per-user results; skips users without email gracefully.
    """
    results = {}
    for user in users:
        results[user.id] = send_notification(user, subject, body)
    return results


def send_account_alert(user: User, alert_type: str) -> bool:
    """
    Send a critical account alert.
    Falls back to a no-op if the user has no email address.
    """
    if not user.email:
        print(f"[notifications] Cannot send alert '{alert_type}' for user {user.id}: email missing.")
        return False

    print(f"[notifications] Account alert '{alert_type}' sent to {user.email}")
    return True
